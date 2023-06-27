from enum import Enum
from dataclasses import dataclass, field, fields
import logging
from typing import List, Optional

from .crawler import crawl, Img, GeneralBlock, Text, UList
from .parser import BiligameParser
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
class Hero(BiligameParser):
    pack: str
    name: str
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
            try:
                for line in crawl(self.biligame_key if self.biligame_key else self.name):
                    if line and isinstance(line, GeneralBlock):
                        if not_p_header:
                            not_p_header = self.parse_header(line)
                        elif not self.parse_module(line):
                            break
            except Exception as e:
                logger = logging.getLogger('biligameCrawler')
                logger.error('crawl biligame failed %s', e, exc_info=True, stack_info=True)
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
    
    def set_image_author(self, author):
        self.image.author = author

    def set_title(self, title):
        self.title = title

    def set_image(self, image):
        self.image = image