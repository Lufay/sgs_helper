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


class Img:
    DEFAULT_SRC = '1x'
    def __init__(self, tag:Tag|dict, author=None):
        self.img_src_set = {'1x': tag["src"]}
        for item in tag.get("srcset", '').split(','):
            src, t = item.strip().split()
            self.img_src_set[t] = src
        self.alt = tag.get("alt")
        self.author = author

    def __str__(self) -> str:
        return f'![{self.alt}]({self.img_src_set[self.DEFAULT_SRC]})'

class GeneralBlock:
    BLACK_NAMES = {'style'}
    WHITE_NAMES = {'div', 'p', 'span', 'hr', 'h2', 'a', }
    BLACK_CLASSES = {'btn', 'desc-color', 'wiki-bot'}
    def __init__(self, name, contents, classes=()):
        if name in self.BLACK_NAMES or self.BLACK_CLASSES.intersection(classes):
            raise KeyError(name + str(classes))
        assert name in self.WHITE_NAMES, name
        self.__name__ = name
        self.contents = contents
        self.classes = classes

    def __iter__(self):
        return iter(self.contents)

    def __str__(self) -> str:
        raise NotImplementedError

class UList(GeneralBlock):
    WHITE_NAMES = {'ul', 'li'}
    def __init__(self, name, contents, leader='+ '):
        super().__init__(name, contents)
        self.leader = leader

    def __str__(self) -> str:
        if self.__name__ == 'ul':
            return '\n'.join(f'{self.leader}{c}  ' for c in self.contents)
        else:
            return ' '.join(str(c) for c in self.contents)


def crawl(name):
    f = root_path / f'page_cache/{name}.html'
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
            case Tag(name='i') | Tag(name='font') | Tag(name='small') | Tag(name='b'):
                yield Text(''.join(block.stripped_strings), block.name, **block.attrs)
            case Tag(name='img'):
                yield Img(block)
            case Tag(name='li') | Tag(name='ul'):
                yield UList(block.name, recur_node(block))
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