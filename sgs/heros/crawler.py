from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Iterator
from functools import cached_property
from itertools import tee
import sys
import inspect

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from common import root_path
from utils import classproperty

class Markdown:
    '''支持markdown 格式化的基类
    '''
    def md_format(self, **kwargs):
        return str(self)

class Text(str, Markdown):
    '''文本类型的基类
    在构造时, 会根据name决定返回的具体子类
    '''
    def __new__(cls, text='', name='', *args, **kwargs):
        cls = cls.local_subclasses.get(name, cls)
        return super().__new__(cls, text)
    
    def __init__(self, text='', name='', **kwargs):
        self.__name__ = name
        self.attrs = kwargs

    @classproperty(1)
    def local_subclasses(cls) -> dict:
        d = {
            'Strong': B,
            'Emphasis': I,
        }
        d.update((name.lower(), cc)
                 for name, cc in inspect.getmembers(sys.modules[cls.__module__], inspect.isclass)
                 if issubclass(cc, cls))
        return d


class I(Text):
    '''斜体文本
    '''
    def md_format(self, **kwargs):
        s = super().md_format(**kwargs)
        return f'*{s}*' if s else ''

    
class Font(Text):
    '''带格式的文本
    '''
    def md_format(self, **kwargs):
        t = Tag(name=self.__name__, attrs=self.attrs)
        t.append(BeautifulSoup().new_string(super().md_format(**kwargs)))
        return str(t)


class B(Text):
    '''粗体文本
    '''
    def md_format(self, **kwargs):
        s = super().md_format(**kwargs)
        return f'**{s}**' if s else ''


class Header(Text):
    '''标题文本
    '''
    def md_format(self, **kwargs):
        level = kwargs.pop('level', 1)
        return '#' * level + ' ' + super().md_format(**kwargs)
    
class Caption(Text):
    '''表格标题文本
    '''
    pass

class Img(Markdown):
    '''img 标签
    '''
    DEFAULT_SRC = '1x'
    def __init__(self, tag:Tag|dict, author=None):
        self.img_src_set = {self.DEFAULT_SRC: tag["src"]}
        if srcset := tag.get("srcset"):
            for item in srcset.split(','):
                src, t = item.split()
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
    '''通用块标签
    BLACK_NAMES: 忽略的标签名
    BLACK_CLASSES: 带有这里面class 的tag 会忽略
    WHITE_NAMES: 支持的标签名(不支持且未忽略会assert 报错)
    '''
    BLACK_NAMES = {'style', 'script', 'sup', 'rp', 'rt'}
    WHITE_NAMES = {'div', 'p', 'span', 'hr', 'h2', 'h3', 'a', 'ruby', 'rb'}
    BLACK_CLASSES = {'btn', 'desc-color', 'wiki-bot'}
    def __init__(self, name, contents, classes=()):
        if name in self.BLACK_NAMES or self.BLACK_CLASSES.intersection(classes):
            raise KeyError(name + str(classes))
        assert name in self.WHITE_NAMES, name
        self.__name__ = name
        self.contents = filter(None, contents)
        self.classes = classes

    def __iter__(self):
        '''可重用迭代contents
        不要直接使用contents 遍历, 因为迭代器或生成器, 无法重复使用
        '''
        if inspect.isgenerator(self.contents) or isinstance(self.contents, Iterator):
            a, b = tee(self.contents)
            self.contents = a
            return b
        return iter(self.contents)

    def __str__(self) -> str:
        return ''.join(str(c) for c in self)
    
    def __getstate__(self):
        '''pickle.dump 会序列化contents
        '''
        self.contents = list(self.contents)
        return vars(self)
    
    def md_format(self, **kwargs):
        '''使用line_break 将contents 串联起来
        若支持markdown, 则使用markdown 格式化; 否则则直接使用字符串化
        '''
        return kwargs.pop('line_break', '').join(
            c.md_format(**kwargs) if isinstance(c, Markdown) else str(c) for c in self)
    
    @classmethod
    def empty(cls, name):
        '''跳过name 检查, 生成一个空实例
        '''
        ins = cls.__new__(cls)
        ins.__name__ = name
        ins.contents = []
        ins.classes = ()
        return ins


class UList(GeneralBlock):
    '''无序列表块
    '''
    WHITE_NAMES = {'ul', 'li'}
    def __init__(self, name, contents, leader='+'):
        super().__init__(name, contents)
        self.leader = leader

    def __str__(self):
        if self.__name__ == 'ul':
            return str(list(self))
        return super.__str__()
    
    def md_format(self, **kwargs):
        if self.__name__ == 'ul':
            return '\n'.join((c.md_format(**kwargs) if isinstance(c, Markdown) else str(c)) + '  ' for c in self)
        elif self.__name__ == 'li':
            return f'{self.leader} {super().md_format(**kwargs)}'
        return super().md_format(**kwargs)

    @classmethod
    def copy_from_block(cls, name, block, leader='+'):
        '''将一个GeneralBlock 实例转换为为一个本实例
        '''
        assert isinstance(block, GeneralBlock)
        ins = cls.__new__(cls)
        ins.__name__ = name
        ins.contents = block.contents
        ins.leader = leader
        return ins
    
    @classmethod
    def list_collect(cls, blocks):
        '''将blocks 中连续的li 元素聚集成一个ul 元素, 其他元素则原样返回
        返回一个生成器
        '''
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
    '''table 块内的相关元素
    '''
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
        '''将单元格每一格th 和 td 的内容放入headers 和 records
        only table tag to run
        支持rowspan和colspan(缓存内容实例, 并放到span的每一个位置)
        not_consumed_cache 是为了解决tr 标签中没有内容的问题(前面的行中rowspan比较多)
        '''
        col_idx = 0
        not_consumed_cache = True
        for cont in children:
            match cont:
                case Table(__name__='thead') | Table(__name__='tbody') | Table(__name__='tr'):
                    if self.record:
                        self.records.append(self.record)
                        self.record = []
                        col_idx = 0
                    if self.iter_children(cont) and self.rowspan_cache:
                        for rc in self.rowspan_cache:
                            rc.cache_cnt -= 1
                        self.rowspan_cache = deque(rc for rc in self.rowspan_cache if rc.cache_cnt)
                case Table(__name__='th'):
                    if (colspan := int(cont.attrd.get('colspan', 1))) > 1:
                        self.headers.extend([cont]*colspan)
                    else:
                        self.headers.append(cont)
                case Table(__name__='td'):
                    not_consumed_cache = False
                    col_idx = self._add_rowspan_cols(col_idx)
                    if cache_cnt := (int(cont.attrd.get('rowspan', 1)) - 1):
                        cont.cache_cnt = cache_cnt
                        cont.idx = col_idx
                        self.rowspan_cache.append(cont)
                    colspan = int(cont.attrd.get('colspan', 1))
                    if colspan > 1:
                        self.record.extend([cont]*colspan)
                    else:
                        self.record.append(cont)
                    col_idx = self._add_rowspan_cols(col_idx + colspan)
        if self.record:
            self.records.append(self.record)
            self.record = []
        return not_consumed_cache

    def _add_rowspan_cols(self, col_idx):
        '''应用rowspan 缓存, 左侧队列头, 右侧队列尾
        '''
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
        '''生成一个空的实例
        当内容填充完毕后, 手动调用iter_children
        '''
        ins = super().empty(name)
        if name == 'table':
            ins.headers = []
            ins.records = []
            ins.record = []
            ins.rowspan_cache = deque()
        return ins

html_parser = 'html.parser'

def crawl(name, ver='sgs'):
    '''biligame 抓取器, 并做页面缓存
    通过recur_node 将关注的tag 转换为内部类型的生成器
    '''
    f = root_path / f'page_cache/biligame/{ver}/{name}.html'
    if f.is_file():
        bs = BeautifulSoup(f.read_text(), html_parser)
    else:
        resp = requests.get(f'https://wiki.biligame.com/{ver}/{name}')
        resp.raise_for_status()
        bs = BeautifulSoup(resp.text, html_parser)
        f.write_text(bs.prettify())
    yield from recur_node(bs.find('div', id='mw-content-text').div.find('div', class_='col-direction'))


def recur_node(node:Tag):
    '''递归将指定tag 下的所有内容转换为内部类型的生成器
    '''
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
    '''baidu baike 抓取器, 并做页面缓存(缓存的是三国杀武将页，而不是默认人物页)
    依次生成基本信息(dict)、锚点头(Header)、锚点体(table)
    '''
    f = root_path / f'page_cache/baidu_baike/{name}.html'
    if f.is_file():
        bs = BeautifulSoup(f.read_text(), html_parser)
    else:
        host = 'https://baike.baidu.com'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.67',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            # 'Cookie': ''
        }
        resp = requests.get(f'{host}/item/{name}', headers=headers)
        resp.raise_for_status()
        print(resp.encoding)
        bs = BeautifulSoup(resp.text, html_parser)
        ulist = bs.find('ul', class_='polysemantList-wrapper')
        cond = lambda c: c and '三国杀' in c and '武将牌' in c
        if ulist:
            a = ulist.find('a', string=cond, title=cond)
        else:
            a = bs.find('a', string=cond)
        if a:
            resp = requests.get(f'{host}{a["href"]}', headers=headers)
            resp.raise_for_status()
            bs = BeautifulSoup(resp.text, html_parser)
        f.write_text(bs.prettify())
    yield baike_basic_info(bs.find('div', class_=('basic-info', 'J-basic-info')))
    baike_anchor:BaikeAnchor = BaikeAnchor.detect_anchor(bs)
    while baike_anchor and (header := baike_anchor.get_title_block()):
        title = ''.join(cs for c in header.children
                        if isinstance(c, NavigableString) and (cs := c.strip()))
        yield Header(title)
        yield from baike_anchor.iter_siblings()
    
def baike_basic_info(div: Tag) -> dict:
    '''根据基本信息tag 返回dict
    '''
    return {
        # 这种方式不支持\xa0、\u3000、\u2800 这些空白符
        # dt.string.translate(str.maketrans(dict.fromkeys(string.whitespace))):
        ''.join(dt.string.split()):
        str(GeneralBlock('div', recur_node(dt.find_next_sibling('dd'))))
        for dl in div.find_all('dl')
        for dt in dl.find_all('dt')
    }


class BaikeAnchor(ABC):
    '''baidu baike 锚点基类
    '''
    def __init__(self, block: Tag, anchor_class:str):
        self.block = block
        self.anchor_class = anchor_class

    def __bool__(self):
        return bool(self.block)

    @abstractmethod
    def get_title_block(self): ...
    @property
    @abstractmethod
    def next_tag_name(self): ...
    @staticmethod
    @abstractmethod
    def process_next_block(block:Tag): ...

    def iter_siblings(self):
        '''遍历锚点体兄弟节点, 直到发现下一个锚点或者没兄弟为止
        '''
        block = self.block.find_next_sibling(self.next_tag_name)
        while block and self.anchor_class not in block.get('class', ()):
            yield from self.__class__.process_next_block(block)
            block = block.find_next_sibling(self.next_tag_name)
        self.block = block

    @classmethod
    def detect_anchor(cls, bs: Tag):
        '''根据锚点结构样式, 返回一个具体的子类实例
        '''
        for subcls in cls.__subclasses__():
            if ins := subcls.detect_anchor(bs):
                return ins


class FixedBaikeAnchor(BaikeAnchor):
    '''固定class的锚点类型
    '''
    FIXED_CLASS = 'anchor-list'
    process_next_block = recur_node
        
    @classmethod
    def detect_anchor(cls, bs: Tag):
        if module := bs.find('div', class_=cls.FIXED_CLASS):
            return cls(module, cls.FIXED_CLASS)
        
    def get_title_block(self):
        if node := self.block.find_next_sibling('div', class_='para-title'):
            self.block = node
            return node.find(('h2', 'h3'), class_='title-text')
        
    @cached_property
    def next_tag_name(self):
        return ('div', 'table')

        
class DynamicBaikeAnchor(BaikeAnchor):
    '''动态后缀class的锚点类型
    '''
    CLASS_PREFIX = 'paraTitle_'

    @classmethod
    def detect_anchor(cls, bs: Tag):
        if module := bs.find('div', class_=lambda c: c and c.startswith(cls.CLASS_PREFIX)):
            for name in module['class']:
                if name.startswith(cls.CLASS_PREFIX):
                    return cls(module, name)

    def get_title_block(self):
        return self.block.find(('h2', 'h3'))    # , {"name": str.isdigit}
    
    @cached_property
    def next_tag_name(self):
        return 'div'
    
    @staticmethod
    def process_next_block(block: Tag):
        if block.get('data-module-type', '') == 'table':
            yield from recur_node(block.find('table'))
