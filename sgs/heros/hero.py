from enum import Enum
from dataclasses import dataclass, field, fields
from functools import cached_property
import glob
import pickle
from typing import List, Optional

from .crawler import GeneralBlock, Img
from . import parser
from utils import classproperty
from common import conf

class Camp(Enum):
    '''势力阵营枚举
    '''
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
    '''按照配置给Hero 动态添加parser 的meta
    配置key为具体的parser 类名, value 为整数, 0为关闭, 非0为打开
    '''
    valid_parsers = (getattr(parser, parse_name) for parse_name, val in conf.items('HeroParser')
                     if int(val) and hasattr(parser, parse_name))
    return type(name, bases+tuple(valid_parsers), attrd)


@dataclass
class Hero(metaclass=hero_parsers):
    '''武将模型
    contents: md 文件的段落列表, 每一个段落转为一个GeneralBlock
    hp: 初始血量
    hp_max: 体力上限
    image: 插画
    is_monarch: 是否是主公
    '''
    pack: str
    name: str
    contents: List[GeneralBlock] = field(default_factory=list)
    hp: int = 0
    hp_max: int = 0
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
        '''使用parser 进行抓取解析
        '''
        if isinstance(self, parser.Parser):
            self.crawl_parse(self.name)
        return self
    
    def __getattribute__(self, name):
        mapper = {
            'hp': min, 'hp_max': max,
        }
        v = super().__getattribute__(name)
        if name in mapper and v == 0 and isinstance(self, parser.Parser):
            return mapper[name](self.hps)
        return v

    def __getattr__(self, name):
        '''当没有继承parser, 而又需要访问其抽象属性, 提供兜底返回
        '''
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
        if self.image:
            self.image.author = author

    def set_image(self, image):
        self.image = image

    def get_pack(self):
        return self.pack
    
    @cached_property
    def uni_name(self):
        return f'{self.name}@{self.pack}'
    
    def __getstate__(self):
        '''cached_property 是个mapping_proxy 无法dump 所以需要先移除
        '''
        d = self.__dict__
        if isinstance(self, parser.Parser):
            d = d.copy()
            if 'alias_mapper' in d:
                del d['alias_mapper']
            if 'hps' in d:
                del d['hps']
        return d

    def dump(self, file_path: str):
        if not file_path.endswith('.pickle'):
            file_path += self.uni_name + '.pickle'
        with open(file_path, 'wb') as wf:
            pickle.dump(self, wf)

    @staticmethod
    def load(file_path, name, pack=None):
        filename = ('',)
        if not file_path.endswith('.pickle'):
            filename = (f'{name}@{pack}.pickle',) if pack else \
                glob.iglob(name + '@*.pickle', root_dir=file_path)
        for fn in filename:
            with open(file_path + fn, 'rb') as rf:
                yield pickle.load(rf)