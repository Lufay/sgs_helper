from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import Field, dataclass, field, fields
from functools import cached_property

from .crawler import Img, GeneralBlock, Text, Table

@dataclass(init=False, eq=False, match_args=False)
class BiligameParser(ABC):
    biligame_key: str = field(default='', init=False, metadata={'md_key': ''})
    biligame_skill_ver: str = field(default='', init=False, metadata={'md_key': ''})

    @abstractmethod
    def set_title(self, title): ...
    @abstractmethod
    def set_image(self, image): ...
    @abstractmethod
    def set_image_author(self, author): ...

    @cached_property
    def alias_mapper(self):
        return {alias:fd for fd in fields(self) if (alias := fd.metadata.get('alias'))}
    
    def clear_alias_key(self):
        del self.key, self.hit_alias, self.anchor
    
    def alias_matcher(self, sline):
        if hasattr(self, 'hit_alias') and self.hit_alias == sline:
            return
        match getattr(self, 'key', None):
            case 'author':
                self.set_image_author(sline)
                self.clear_alias_key()
            case Field() as fd:
                if func := fd.metadata.get('val_trans'):
                    sline = func(sline)
                if hasattr(self, 'anchor') and self.anchor.level >= 0:
                    self.anchor.stack.append(sline)
                else:
                    setattr(self, fd.name, sline)
                    self.clear_alias_key()
            case _:
                for alias, fd in self.alias_mapper.items():
                    if alias in sline:
                        self.key = fd
                        self.hit_alias = sline
                        self.anchor = Anchor(fd.metadata.get('anchor_num', -1),
                                             getattr(self, fd.name),
                                             fd.metadata.get('sections'))
                        break

    def parse_header(self, headers):
        skip = True
        for line in headers:
            if not line:
                continue
            if isinstance(line, str) and (sline := line.strip()):
                if '武将称号' in sline:
                    skip = False
                    self.set_title(sline.removeprefix('武将称号：'))
                elif isinstance(line, Text) and line.__name__ == 'pack':
                    return False
                else:
                    self.alias_matcher(sline)
            elif isinstance(line, GeneralBlock):
                skip = self.parse_header(line) and skip
        return skip

    def parse_module(self, mod):
        for line in mod:
            if not line:
                continue
            if isinstance(line, str) and (sline := line.strip()):
                if isinstance(line, Text) and line.__name__ == 'pack':
                    if ('界' in self.pack) != ('界' in line):
                        return True
                elif sline == '历史版本':
                    self.search_ver = True
                    continue
                elif getattr(self, 'search_ver', None):
                    if sline == self.biligame_skill_ver:
                        self.anchor.running = True
                        self.search_ver = False
                    continue
                self.alias_matcher(sline)
            elif isinstance(line, Table) and line.__name__ == 'table':
                if hasattr(self, 'anchor') and self.anchor.level >= 0:
                    self.anchor.running = False
                self.parse_module(line.headers[0])
                for row in line.records:
                    self.parse_module(row[0])
                if self.search_ver:
                    del self.search_ver
                    self.anchor.running = True
                else:
                    self.anchor = Anchor()
                    self.clear_alias_key()
            elif isinstance(line, GeneralBlock):
                with getattr(self, 'anchor', Anchor.get_ins())(line.classes, self.clear_alias_key):
                    if self.parse_module(line):
                        return True
            elif isinstance(line, Img):
                if '形象' in line.alt:
                    self.set_image(line)
                    self.key = 'author'
                    self.hit_alias = '形象'
                    self.anchor = Anchor()
                else:
                    self.alias_matcher(line.alt.strip())


class Anchor:
    _ins = None
    
    def __new__(cls, *args, **kwargs):
        return cls.get_ins()
    
    @classmethod
    def get_ins(cls):
        if cls._ins is None:
            cls._ins = object.__new__(cls)
        return cls._ins
    
    def __init__(self, level=-1, stack=None, sections=None):
        self.level = level
        self.stack = stack
        self.sections = sections
        self.sec_idx = 0 if self.sections else -1
        self.running = True

    @contextmanager
    def __call__(self, classes, cf):
        if self.running:
            ori_stack = None
            if self.level >= 0:
                self.level += 1
                if 0 <= self.sec_idx < len(self.sections) and \
                        self.sections[self.sec_idx] in classes:
                    ori_stack = self.stack
                    self.stack = []
                    ori_stack.append(self.stack)
                    self.sec_idx += 1
            yield
            if self.level >= 0:
                self.level -= 1
                if ori_stack:
                    self.stack = ori_stack
                    self.sec_idx -= 1
                if self.level < 0:
                    cf()
        else:
            yield