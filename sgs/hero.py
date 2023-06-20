from contextlib import contextmanager
from enum import Enum, auto
from dataclasses import Field, dataclass, field, fields
from typing import List, Optional
from functools import cached_property

from .crawler import crawl, Img, GeneralBlock

class Camp(Enum):
    def __init__(self, value, zn_name):
        self._value_ = value
        self.zn_name = zn_name

    @classmethod
    def get_value(cls, zn_name):
        for ev in cls:
            if ev.zn_name == zn_name:
                return ev
        return cls.UNKNOWN
            
    UNKNOWN = (auto(), '未知')
    SHU = (auto(), '蜀')
    WEI = (auto(), '魏')
    WU = (auto(), '吴')
    QUN = (auto(), '群')
    JIN = (auto(), '晋')


@dataclass
class Hero:
    pack: str = field(metadata={'alias': '武将包'})
    name: str
    title: str = ''
    contents: List[str] = field(default_factory=list)
    hp: int = field(default=0, metadata={'alias': '勾玉', 'val_trans': int})
    hp_max: int = 0
    image: Optional[Img] = None
    gender: str = field(default='', metadata={'alias': '性别'})
    camp: Camp = field(default=Camp.UNKNOWN, metadata={'alias': '势力', 'val_trans': Camp.get_value})
    skills: List[str] = field(default_factory=list, metadata={'alias': '技能', 'anchor_num': 1, 'sections': ['技能标签']})
    lines: List[str] = field(default_factory=list, metadata={'alias': '台词', 'anchor_num': 1, 'sections': ['basic-info-row-label']})
    position: List[str] = field(default_factory=list, metadata={'alias': '定位', 'anchor_num': 1})
    is_monarch: bool = False
        
    def crawl_by_name(self):
        not_p_header = True
        for line in crawl(self.name):
            if line and isinstance(line, GeneralBlock):
                if not_p_header:
                    not_p_header = self.parse_header(line)
                else:
                    self.parse_module(line)

    @cached_property
    def alias_mapper(self):
        return {md.get('alias'):fd for fd in fields(self) if (md := fd.metadata)}
    
    def alias_matcher(self, sline):
        if hasattr(self, 'hit_alias') and self.hit_alias in sline:
            return
        match getattr(self, 'key', None):
            case 'author':
                self.image.author = sline
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
                        self.hit_alias = alias
                        self.anchor = Anchor(fd.metadata.get('anchor_num', -1),
                                             getattr(self, fd.name),
                                             fd.metadata.get('sections'))
                        break
    
    def clear_alias_key(self):
        del self.key, self.hit_alias
        if hasattr(self, 'anchor'):
            del self.anchor

    def parse_header(self, headers):
        skip = True
        for line in headers:
            if not line:
                continue
            if isinstance(line, str) and (sline := line.strip()):
                if '武将称号' in sline:
                    skip = False
                    self.title = sline.removeprefix('武将称号：')
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
                self.alias_matcher(sline)
            elif isinstance(line, GeneralBlock):
                with getattr(self, 'anchor', Anchor.nop())(line.classes, self.clear_alias_key):
                    self.parse_module(line)
            elif isinstance(line, Img):
                if '形象' in line.alt:
                    self.image = line
                    self.key = 'author'
                    self.hit_alias = '形象'
                else:
                    self.alias_matcher(line.alt.strip())


@dataclass
class Anchor:
    level: int
    stack: list
    sections: list
    sec_idx: int = -1

    def __post_init__(self):
        if self.sections:
            self.sec_idx = 0

    @contextmanager
    def __call__(self, classes, cf):
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
        if self.level > 0:
            self.level -= 1
            if ori_stack:
                self.stack = ori_stack
                self.sec_idx -= 1
        elif self.level == 0:
            cf()

    @classmethod
    def nop(cls):
        return cls(-1, None, None)