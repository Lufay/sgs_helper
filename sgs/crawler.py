from collections import deque
from collections.abc import Iterator
from itertools import tee
import sys
import inspect

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from common import root_path

class Text(str):
    def __new__(cls, text='', name='', *args, **kwargs):
        cls = dict(cls.local_subclasses).get(name, cls)
        return super().__new__(cls, text)
    
    def __init__(self, text='', name='', **kwargs):
        self.__name__ = name
        self.attrs = kwargs

    # @classproperty(1)
    @classmethod
    @property
    def local_subclasses(cls):
        for name, cc in inspect.getmembers(sys.modules[cls.__module__], inspect.isclass):
            if issubclass(cc, cls):
                yield name.lower(), cc
        yield 'Strong', B
        yield 'Emphasis', I


class I(Text):
    def __str__(self):
        s = super().__str__()
        return f'*{s}*' if s else ''

    
class Font(Text):
    def __str__(self) -> str:
        t = Tag(name=self.__name__, attrs=self.attrs)
        t.append(BeautifulSoup().new_string(super().__str__()))
        return str(t)


class B(Text):
    def __str__(self):
        s = super().__str__()
        return f'**{s}**' if s else ''


class Header(Text):
    # def __str__(self):
    #     s = super().__str__()
    #     return '# ' + s
    pass
    
class Caption(Text):
    pass

class Img:
    DEFAULT_SRC = '1x'
    def __init__(self, tag:Tag|dict, author=None):
        self.img_src_set = {self.DEFAULT_SRC: tag["src"]}
        for item in tag.get("srcset", '').split(','):
            src, t = item.strip().split()
            self.img_src_set[t] = src
        self.data_src = tag.get("data-src", '')
        self.alt = tag.get("alt")
        self.author = author

    @property
    def img_src(self):
        src = self.img_src_set[self.DEFAULT_SRC]
        if not src.startswith('http') and self.data_src.startswith('http'):
            return self.data_src
        return src

    def __str__(self) -> str:
        return f'![{self.alt}]({self.img_src})'

class GeneralBlock:
    BLACK_NAMES = {'style', 'script', 'sup'}
    WHITE_NAMES = {'div', 'p', 'span', 'hr', 'h2', 'h3', 'a', }
    BLACK_CLASSES = {'btn', 'desc-color', 'wiki-bot'}
    def __init__(self, name, contents, classes=()):
        if name in self.BLACK_NAMES or self.BLACK_CLASSES.intersection(classes):
            raise KeyError(name + str(classes))
        assert name in self.WHITE_NAMES, name
        self.__name__ = name
        self.contents = contents
        self.classes = classes

    def __iter__(self):
        if inspect.isgenerator(self.contents) or isinstance(self.contents, Iterator):
            a, b = tee(self.contents)
            self.contents = a
            return b
        return iter(self.contents)

    def __str__(self) -> str:
        return ''.join(str(c) for c in self)
    

class UList(GeneralBlock):
    WHITE_NAMES = {'ul', 'li'}
    def __init__(self, name, contents, leader='+ '):
        super().__init__(name, contents)
        self.leader = leader

    def __str__(self) -> str:
        if self.__name__ == 'ul':
            return '\n'.join(f'{self.leader}{c}  ' for c in self.contents)
        return super().__str__()


class Table(GeneralBlock):
    WHITE_NAMES = {'table', 'thead', 'tbody', 'tr', 'th', 'td'}
    def __init__(self, name, contents, **kwargs):
        classes = kwargs.pop('class', ())
        super().__init__(name, contents, classes)
        self.attrd = kwargs
        if name == 'table':
            self.headers = []
            self.records = []
            self.record = []
            self.rowspan_cache = deque()
            self.iter_children(contents)

    def iter_children(self, children):
        '''only table to run
        '''
        col_idx = 0
        for cont in children:
            match cont:
                case Table(__name__='thead') | Table(__name__='tbody') | Table(__name__='tr'):
                    if self.record:
                        self.records.append(self.record)
                        self.record = []
                        col_idx = 0
                    self.iter_children(cont)
                case Table(__name__='th'):
                    self.headers.append(cont)
                case Table(__name__='td'):
                    if self.rowspan_cache and (top := self.rowspan_cache[0]).idx == col_idx:
                        self.record.append(top)
                        if top.cache_cnt > 1:
                            top.cache_cnt -= 1
                            self.rowspan_cache.rotate(-1)
                        else:
                            self.rowspan_cache.popleft()
                        col_idx += 1
                    if cache_cnt := (int(cont.attrd.get('rowspan', 1)) - 1):
                        cont.cache_cnt = cache_cnt
                        cont.idx = col_idx
                        self.rowspan_cache.append(cont)
                    self.record.append(cont)
                    col_idx += 1
        if self.record:
            self.records.append(self.record)
            self.record = []


def crawl(name):
    f = root_path / f'page_cache/biligame/{name}.html'
    if f.is_file():
        bs = BeautifulSoup(f.read_text(), 'html.parser')
    else:
        resp = requests.get(f'https://wiki.biligame.com/sgs/{name}')
        resp.raise_for_status()
        bs = BeautifulSoup(resp.text, 'html.parser')
        f.write_text(bs.prettify())
    yield from recur_node(bs.find('div', id='mw-content-text').div.find('div', class_='col-direction'))


def recur_node(node:Tag):
    for block in node.children:
        match block:
            case NavigableString():
                yield block.strip()
            case Tag(name='br'):
                yield '\n'
            case Tag(name='i') | Tag(name='font') | Tag(name='small') | Tag(name='b') | Tag(name='caption'):
                yield Text(''.join(block.stripped_strings), block.name, **block.attrs)
            case Tag(name='img'):
                yield Img(block)
            case Tag(name='li') | Tag(name='ul'):
                yield UList(block.name, recur_node(block))
            case Tag(name='table') | Tag(name='thead') | Tag(name='tbody') | Tag(name='tr') | Tag(name='th') | Tag(name='td'):
                yield Table(block.name, recur_node(block), **block.attrs)
            case Tag(name='div') if '锚点' in block.get('class', ()):
                block_cont = ''.join(block.stripped_strings)
                if any(map(lambda x: x in block_cont, ('国战', '自走棋', '皮肤', '秀'))):
                    break
                yield Text(block_cont, 'pack')
            case _:
                try:
                    yield GeneralBlock(block.name, recur_node(block), block.get('class', ()))
                except KeyError as e:
                    print(f'skip block {e}')


def baike_crawl(name):
    f = root_path / f'page_cache/baidu_baike/{name}.html'
    if f.is_file():
        bs = BeautifulSoup(f.read_text(), 'html.parser')
    else:
        host = 'https://baike.baidu.com'
        resp = requests.get(f'{host}/item/{name}')
        resp.raise_for_status()
        bs = BeautifulSoup(resp.text, 'html.parser')
        ulist = bs.find('ul', class_='polysemantList-wrapper')
        cond = lambda c: '三国杀' in c and '武将牌' in c
        a = ulist.find('a', string=cond, title=cond)
        resp = requests.get(f'{host}{a["href"]}')
        resp.raise_for_status()
        bs = BeautifulSoup(resp.text, 'html.parser')
        f.write_text(bs.prettify())
    yield baike_basic_info(bs.find('div', class_='basic-info'))
    module = bs.find('div', class_='anchor-list')
    while module and (node := module.find_next_sibling('div', class_='para-title')):
        title = get_module_title(node)
        yield Header(title)
        module = node
        while True:
            module = module.find_next_sibling(('div', 'table'))
            if not module or 'anchor-list' in module.get('class', ()):
                break
            yield from recur_node(module)
    
def baike_basic_info(div: Tag):
    basic_info = {}
    for dl in div.find_all('dl'):
        cur:Tag = dl.dt
        while cur:
            nxt = cur.find_next_sibling('dd')
            key = ''.join(cur.string.strip().split())
            basic_info[key] = str(GeneralBlock('div', recur_node(nxt)))
            cur = nxt.find_next_sibling('dt')
    return basic_info

def get_module_title(module: Tag):
    header = module.find('h2', class_='title-text')
    if not header:
        return
    return ''.join(cs for c in header.children if isinstance(c, NavigableString) and (cs := c.strip()))
