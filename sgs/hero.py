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
    hp: int = 0
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
        match getattr(self, 'key', None):
            case 'author':
                self.image.author = sline
                del self.key
            case 'hp':
                self.hp = int(sline)
            case Field() as fd:
                if func := fd.metadata.get('val_trans'):
                    sline = func(sline)
                if getattr(self, 'anchor_num', -1) >= 0:
                    self.sec_list.append(sline)
                else:
                    setattr(self, fd.name, sline)
                    del self.key
            case _:
                for alias, fd in self.alias_mapper.items():
                    if alias in sline:
                        self.key = fd
                        if (an := fd.metadata.get('anchor_num', -1)) >= 0:
                            self.anchor_num = an
                            self.sec_list = getattr(self, fd.name)
                            if 'sections' in fd.metadata:
                                self.sec_idx = 0
                        break

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
                ori_list = None
                if hasattr(self, 'anchor_num'):
                    self.anchor_num += 1
                    if hasattr(self, 'sec_idx') and \
                        self.sec_idx < len(sections := self.key.metadata.get('sections')) and \
                            sections[self.sec_idx] in line.classes:
                        ori_list = self.sec_list
                        self.sec_list = []
                        ori_list.append(self.sec_list)
                        self.sec_idx += 1
                self.parse_module(line)
                if hasattr(self, 'anchor_num'):
                    if self.anchor_num > 0:
                        self.anchor_num -= 1
                        if ori_list:
                            self.sec_list = ori_list
                            self.sec_idx -= 1
                    else:
                        del self.anchor_num, self.key
                        if hasattr(self, 'sec_idx'):
                            del self.sec_idx
            elif isinstance(line, Img):
                if '勾玉' in line.alt:
                    self.key = 'hp'
                elif '形象' in line.alt:
                    self.image = line
                    self.key = 'author'


@dataclass
class Anchor:
    level: int
    stack: list
    sec_idx: int = -1