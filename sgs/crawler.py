from collections import deque
from collections.abc import Iterator
from itertools import tee
import sys
import inspect

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from common import root_path

class Markdown:
    def md_format(self, **kwargs):
        return str(self)

class Text(str, Markdown):
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
    def md_format(self, **kwargs):
        s = super().md_format(**kwargs)
        return f'*{s}*' if s else ''

    
class Font(Text):
    def md_format(self, **kwargs):
        t = Tag(name=self.__name__, attrs=self.attrs)
        t.append(BeautifulSoup().new_string(super().md_format(**kwargs)))
        return str(t)


class B(Text):
    def md_format(self, **kwargs):
        s = super().md_format(**kwargs)
        return f'**{s}**' if s else ''


class Header(Text):
    def md_format(self, **kwargs):
        level = kwargs.pop('level', 1)
        return '#' * level + ' ' + super().md_format(**kwargs)
    
class Caption(Text):
    pass

class Img(Markdown):
    DEFAULT_SRC = '1x'
    def __init__(self, tag:Tag|dict, author=None):
        self.img_src_set = {self.DEFAULT_SRC: tag["src"]}
        for item in tag.get("srcset", '').split(','):
            src, t = item.strip().split()
            self.img_src_set[t] = src
        self.data_src = tag.get("data-src", '')
        self.alt = tag.get("alt")
        self.author = author

    def img_src(self, src_key=None):
        if src_key is None:
            src_key = self.DEFAULT_SRC
        src = self.img_src_set[src_key]
        if not src.startswith('http') and self.data_src.startswith('http'):
            return self.data_src
        return src

    def __str__(self) -> str:
        return self.img_src_set[self.DEFAULT_SRC]
    
    def md_format(self, **kwargs):
        src_key = kwargs.get('src_key')
        return f'![{self.alt}]({self.img_src(src_key)})'


class GeneralBlock(Markdown):
    BLACK_NAMES = {'style', 'script', 'sup'}
    WHITE_NAMES = {'div', 'p', 'span', 'hr', 'h2', 'h3', 'a', }
    BLACK_CLASSES = {'btn', 'desc-color', 'wiki-bot'}
    def __init__(self, name, contents, classes=()):
        if name in self.BLACK_NAMES or self.BLACK_CLASSES.intersection(classes):
            raise KeyError(name + str(classes))
        assert name in self.WHITE_NAMES, name
        self.__name__ = name
        self.contents = filter(None, contents)
        self.classes = classes

    def __iter__(self):
        if inspect.isgenerator(self.contents) or isinstance(self.contents, Iterator):
            a, b = tee(self.contents)
            self.contents = a
            return b
        return iter(self.contents)

    def __str__(self) -> str:
        return ''.join(str(c) for c in self)
    
    def __getstate__(self):
        self.contents = list(self.contents)
        return vars(self)
    
    def md_format(self, **kwargs):
        return kwargs.pop('line_break', '').join(
            c.md_format(**kwargs) if isinstance(c, Markdown) else str(c) for c in self)
    
    @classmethod
    def empty(cls, name):
        ins = cls.__new__(cls)
        ins.__name__ = name
        ins.contents = []
        ins.classes = ()
        return ins


class UList(GeneralBlock):
    WHITE_NAMES = {'ul', 'li'}
    def __init__(self, name, contents, leader='+'):
        super().__init__(name, contents)
        self.leader = leader

    def __str__(self):
        if self.__name__ == 'ul':
            return str(list(self.contents))
        return super.__str__()
    
    def md_format(self, **kwargs):
        if self.__name__ == 'ul':
            return '\n'.join((c.md_format(**kwargs) if isinstance(c, Markdown) else str(c)) + '  ' for c in self.contents)
        elif self.__name__ == 'li':
            return f'{self.leader} {super().md_format(**kwargs)}'
        return super().md_format(**kwargs)

    @classmethod
    def copy_from_block(cls, name, block, leader='+'):
        assert isinstance(block, GeneralBlock)
        ins = cls.__new__(cls)
        ins.__name__ = name
        ins.contents = block.contents
        ins.leader = leader
        return ins
    
    @classmethod
    def list_collect(cls, blocks):
        lis = []
        for block in blocks:
            if isinstance(block, cls) and block.__name__ == 'li':
                lis.append(block)
            else:
                if lis:
                    yield cls('ul', lis)
                    lis.clear()
                yield block
        if lis:
            yield cls('ul', lis)


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
                    col_idx = self._add_rowspan_cols(col_idx)
                    if cache_cnt := (int(cont.attrd.get('rowspan', 1)) - 1):
                        cont.cache_cnt = cache_cnt
                        cont.idx = col_idx
                        self.rowspan_cache.append(cont)
                    for i in range(int(cont.attrd.get('colspan', 1))):
                        self.record.append(cont)
                        col_idx += 1
                    col_idx = self._add_rowspan_cols(col_idx)
        if self.record:
            self.records.append(self.record)
            self.record = []

    def _add_rowspan_cols(self, col_idx):
        while self.rowspan_cache and (top := self.rowspan_cache[0]).idx == col_idx:
            self.record.append(top)
            if top.cache_cnt > 1:
                top.cache_cnt -= 1
                self.rowspan_cache.rotate(-1)
            else:
                self.rowspan_cache.popleft()
            col_idx += 1
        return col_idx

    @classmethod
    def empty(cls, name):
        ins = super().empty(name)
        if name == 'table':
            ins.headers = []
            ins.records = []
            ins.record = []
            ins.rowspan_cache = deque()
        return ins


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
        print(resp.encoding)
        bs = BeautifulSoup(resp.text, 'html.parser')
        ulist = bs.find('ul', class_='polysemantList-wrapper')
        cond = lambda c: c and '三国杀' in c and '武将牌' in c
        if ulist:
            a = ulist.find('a', string=cond, title=cond)
        else:
            a = bs.find('a', string=cond)
        resp = requests.get(f'{host}{a["href"]}')
        resp.raise_for_status()
        bs = BeautifulSoup(resp.text, 'html.parser')
        f.write_text(bs.prettify())
    yield baike_basic_info(bs.find('div', class_=('basic-info', 'J-basic-info')))
    anchor_classes = ('anchor-list', )
    module = bs.find('div', class_=anchor_classes)
    while module and (node := module.find_next_sibling('div', class_='para-title')):
        title = get_module_title(node)
        yield Header(title)
        module = node
        while True:
            module = module.find_next_sibling(('div', 'table'))
            if not module or any(anchor in module.get('class', ()) for anchor in anchor_classes):
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
    header = module.find(('h2', 'h3'), class_='title-text')
    if not header:
        return
    return ''.join(cs for c in header.children if isinstance(c, NavigableString) and (cs := c.strip()))
