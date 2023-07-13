from enum import Enum
from dataclasses import dataclass, field, fields
import pickle
from typing import List, Optional

from .crawler import GeneralBlock, Img
from . import parser
from utils import classproperty
from common import conf

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
            return cls(zn_name[0])
        except ValueError:
            return cls.UNKNOWN


def hero_parsers(name, bases, attrd):
    valid_parsers = (getattr(parser, parse_name) for parse_name, val in conf.items('HeroParser')
                     if int(val) and hasattr(parser, parse_name))
    return type(name, bases+tuple(valid_parsers), attrd)


@dataclass
class Hero(metaclass=hero_parsers):
    pack: str
    name: str
    contents: List[GeneralBlock] = field(default_factory=list)
    hp: int = field(default=0, metadata={'alias': '勾玉', 'val_trans': int})
    hp_max: int = field(default=0, metadata={'alias': '体力', 'val_trans': lambda s: int(s.partition('勾玉')[0])})
    image: Optional[Img] = None
    gender: str = field(default='', metadata={'alias': '性别'})
    camp: Camp = field(default=Camp.UNKNOWN, metadata={'alias': '势力', 'val_trans': Camp.get_value})
    position: List[str] = field(default_factory=list, metadata={'alias': ('定位', '武将定位'), 'anchor_num': 1})
    is_monarch: bool = False

    @classproperty(1)
    def md_fields(cls):
        '''md_key is the keyword in markdown file which field represents, default is field name
        '''
        return {fd.name: md_key if md_key else fd.name
                for fd in fields(cls)
                if (md_key := fd.metadata.get('md_key')) is not None}
        
    def crawl_by_name(self):
        if isinstance(self, parser.Parser):
            self.crawl_parse(self.name)
        return self
    
    def __getattr__(self, name):
        if hasattr(parser.Parser, name):
            return ''
        return super().__getattr__(name)
    
    # @property
    # def title(self):
    #     if isinstance(self, parser.Parser):
    #         return super().title
    #     return ''
    
    # @property
    # def skills(self):
    #     if isinstance(self, parser.Parser):
    #         yield from super().skills

    # @property
    # def lines(self):
    #     if isinstance(self, parser.Parser):
    #         yield from super().lines
    
    def set_image_author(self, author):
        self.image.author = author

    def set_image(self, image):
        self.image = image

    def get_pack(self):
        return self.pack

    def dump(self, file_path: str):
        if isinstance(self, parser.Parser):
            del self.alias_mapper
        if not file_path.endswith('.pickle'):
            file_path += self.name + '.pickle'
        with open(file_path, 'wb') as wf:
            pickle.dump(self, wf)

    @staticmethod
    def load(file_path):
        with open(file_path, 'rb') as rf:
            return pickle.load(rf)