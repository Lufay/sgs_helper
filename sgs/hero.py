from contextlib import contextmanager
from enum import Enum
from dataclasses import Field, dataclass, field, fields
from typing import List, Optional
from functools import cached_property

from .crawler import crawl, Img, GeneralBlock, Text, UList, Table
from utils import classproperty

class Camp(Enum):
    UNKNOWN = '未知'
    SHU = '蜀'
    WEI = '魏'
    WU = '吴'
    QUN = '群'
    JIN = '晋'

    @classmethod
    def get_value(cls, zn_name):
        try:
            return cls(zn_name)
        except ValueError:
            return cls.UNKNOWN


@dataclass
class Hero:
    pack: str
    name: str
    biligame_key: str = field(default='', metadata={'md_key': ''})
    biligame_skill_ver: str = field(default='', metadata={'md_key': ''})
    title: str = ''
    detail_pack: str = field(default='', metadata={'alias': '武将包'})
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

    @classproperty(1)
    def md_fields(cls):
        return {fd.name: md_key if md_key else fd.name
                for fd in fields(cls)
                if (md_key := fd.metadata.get('md_key')) is not None}
        
    def crawl_by_name(self):
        if not self.detail_pack and self.biligame_key != 'none':
            not_p_header = True
            for line in crawl(self.biligame_key if self.biligame_key else self.name):
                if line and isinstance(line, GeneralBlock):
                    if not_p_header:
                        not_p_header = self.parse_header(line)
                    elif not self.parse_module(line):
                        break
        return self
    
    @property
    def skill_str(self) -> str:
        return self.to_str(self.skills)
    
    @property
    def lines_str(self) -> str:
        return self.to_str(self.lines)

    @staticmethod
    def to_str(lists):
        secs = []
        sec = []
        for item in lists:
            if isinstance(item, list):
                if sec:
                    secs.append(UList('li', sec))
                    sec = []
                sec.append(Text(''.join(item), 'b'))
            else:
                sec.append(item)
        secs.append(UList('li', sec))
        return str(UList('ul', secs))

    @cached_property
    def alias_mapper(self):
        return {alias:fd for fd in fields(self) if (alias := fd.metadata.get('alias'))}
    
    def alias_matcher(self, sline):
        if hasattr(self, 'hit_alias') and self.hit_alias == sline:
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
                        self.hit_alias = sline
                        self.anchor = Anchor(fd.metadata.get('anchor_num', -1),
                                             getattr(self, fd.name),
                                             fd.metadata.get('sections'))
                        break
    
    def clear_alias_key(self):
        del self.key, self.hit_alias, self.anchor

    def parse_header(self, headers):
        skip = True
        for line in headers:
            if not line:
                continue
            if isinstance(line, str) and (sline := line.strip()):
                if '武将称号' in sline:
                    skip = False
                    self.title = sline.removeprefix('武将称号：')
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
                    self.image = line
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