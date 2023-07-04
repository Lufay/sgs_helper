from enum import Enum
from dataclasses import dataclass, field, fields
from typing import List, Optional

from .crawler import GeneralBlock, Img
from .parser import BiligameParser, BaiduBaikeParser
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
class Hero(BiligameParser, BaiduBaikeParser):
    pack: str
    name: str
    contents: List[GeneralBlock] = field(default_factory=list)
    hp: int = field(default=0, metadata={'alias': '勾玉', 'val_trans': int})
    hp_max: int = field(default=0, metadata={'alias': '体力', 'val_trans': lambda s: int(s.partition('勾玉')[0])})
    image: Optional[Img] = None
    gender: str = field(default='', metadata={'alias': '性别'})
    camp: Camp = field(default=Camp.UNKNOWN, metadata={'alias': '势力', 'val_trans': Camp.get_value})
    position: List[str] = field(default_factory=list, metadata={'alias': '定位', 'anchor_num': 1})
    is_monarch: bool = False

    @classproperty(1)
    def md_fields(cls):
        return {fd.name: md_key if md_key else fd.name
                for fd in fields(cls)
                if (md_key := fd.metadata.get('md_key')) is not None}
        
    def crawl_by_name(self):
        self.crawl_parse(self.name)
        return self
    
    def set_image_author(self, author):
        self.image.author = author

    def set_image(self, image):
        self.image = image