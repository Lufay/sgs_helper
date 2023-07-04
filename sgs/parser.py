from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import Field, dataclass, field, fields
from functools import cached_property
import logging
import operator
from typing import List

from .crawler import UList, crawl, baike_crawl, Img, GeneralBlock, Text, Table, Header, Caption

class Parser(ABC):
    @abstractmethod
    def crawl_parse(self, name): ...

    @cached_property
    def alias_mapper(self):
        d = {}
        for fd in fields(self):
            if alias := fd.metadata.get('alias'):
                if isinstance(alias, tuple):
                    d.update({alias_item:fd for alias_item in alias})
                else:
                    d[alias] = fd
        return d

@dataclass(init=False, eq=False, match_args=False)
class BaiduBaikeParser(Parser):
    baike_title:str = field(default='', init=False, metadata={'alias': '称号'})
    game_mode: str = field(default='', init=False, metadata={'alias':('模式', '出现模式')})
    card_id: str = field(default='', init=False, metadata={'alias': '编号'})
    baike_skill_names: list = field(default_factory=list, init=False, metadata={'alias': ('技能名称', '名称')})
    baike_skill_descs: list = field(default_factory=list, init=False, metadata={'alias': ('技能描述', '描述', '技能信息')})
    baike_lines: list = field(default_factory=list, init=False)
    baike_skill_ver: str = field(default='', init=False, metadata={'md_key': ''})
    baike_line_ver: str = field(default='', init=False, metadata={'md_key': ''})
    module_name: str = field(default='', init=False, repr=False)
    sub_mod_name: str = field(default='', init=False, repr=False)
    sub_module: dict = field(default_factory=dict, init=False, repr=False)

    @property
    def baike_skill_str(self):
        skills = []
        for name, desc in zip(self.baike_skill_names, self.baike_skill_descs):
            b = Text(name, 'b')
            skills.append(UList('li', [b, ' ', desc]))
        return UList('ul', skills).md_format()
    
    @property
    def baike_line_str(self):
        return UList('ul', [UList('li', (line,)) for line in self.baike_lines]).md_format()

    @abstractmethod
    def set_image_author(self, author): ...

    table_parser = lambda method_name: (lambda *args: operator.methodcaller(method_name, *args))
    module_parsers = {
        '能力设定': (table_parser('parse_abilities'), 'baike_skill_ver'),
        '武将属性': (table_parser('parse_abilities'), 'baike_skill_ver'),
        '属性': (table_parser('parse_abilities'), 'baike_skill_ver'),
        '武将技能': (table_parser('parse_abilities'), 'baike_skill_ver'),
        '技能': (table_parser('parse_abilities'), 'baike_skill_ver'),

        '武将台词': (table_parser('parse_abilities'), 'baike_line_ver'),
        '角色台词': (table_parser('parse_abilities'), 'baike_line_ver'),
        '语音台词': (table_parser('parse_abilities'), 'baike_line_ver'),
        '台词': (table_parser('parse_abilities'), 'baike_line_ver'),

        '角色专属': (table_parser('parse_images'), 'baike_line_ver'),
        '皮肤': (table_parser('parse_images'), 'baike_line_ver'),
    }

    def crawl_parse(self, name):
        if self.baike_skill_ver != 'none' and not self.baike_skill_names:
            for node in baike_crawl(name):
                if node:
                    match node:
                        case dict():
                            self.parse_basic_info(node)
                        case Header(t):
                            self.new_sub_mod(t)
                            self.module_name = t
                        case _ if self.sub_mod_name in self.sub_module:
                            self.parse_module_item(node)
            self.new_sub_mod('')
            for mod_name, table in self.sub_module.items():
                if table.headers and (f_verkey := self.module_parsers.get(mod_name)):
                    len_header = len(table.headers)
                    f, self.ver_key = f_verkey
                    self.ver = getattr(self, self.ver_key)
                    if self.ver:
                        headers = [str(h) for h in table.headers[1:]]
                    else:
                        headers = [str(h) for h in table.headers]
                    for record in table.records:
                        assert len(record) == len_header
                        f(headers, record)(self)
                    del self.ver, self.ver_key
            # self.clear_modules()
        return super().crawl_parse(name)
    
    # def clear_modules(self):
    #     self.module_name = self.sub_mod_name = ''
    #     self.sub_module = {}
    
    def parse_basic_info(self, info:dict):
        if '武将称号' in info:
            info.setdefault('称号', info.pop('武将称号'))
        info.setdefault('势力', info.get('所属势力', '未知')[0])
        if '技能' in info:
            del info['技能']
        for alias, fd in self.alias_mapper.items():
            if alias in info:
                val = info[alias]
                if func := fd.metadata.get('val_trans'):
                    val = func(val)
                setattr(self, fd.name, val)

    def parse_module_item(self, item):
        match item:
            case Caption(t):
                self.new_sub_mod(t)
            case Table():
                self.sub_module[self.sub_mod_name].contents.append(item)

    def new_sub_mod(self, name):
        if self.sub_mod_name and (table := self.sub_module.get(self.sub_mod_name)):
            table.iter_children(table.contents)
        self.sub_mod_name = name
        if name in self.module_parsers.keys():
            self.sub_module[name] = Table.empty('table')

    def parse_abilities(self, headers:list, record: list):
        if not self.ver or self.ver in str(record[0]):
            cols = record[1:] if self.ver else record
            for i, col in enumerate(cols):
                col_name = headers[i]
                if col_name == '画师':
                    self.set_image_author(str(col))
                elif self.ver_key == 'baike_line_ver':
                    self.baike_lines = [str(d) for d in col if d]
                elif fd := self.alias_mapper.get(col_name):
                    val = str(col)
                    if func := fd.metadata.get('val_trans'):
                        val = func(val)
                    if issubclass(fd.type, list):
                        getattr(self, fd.name).append(val)
                    else:
                        setattr(self, fd.name, val)
    
    def parse_images(self, headers:list, record: list):
        print(f'image header len: {len(headers)} {headers}')
        print(f'\trecord len: {len(record)}')


@dataclass(init=False, eq=False, match_args=False)
class BiligameParser(Parser):
    bili_title: str = field(default='', init=False, metadata={'alias': '武将称号'})
    bili_skills: List[str] = field(default_factory=list, init=False, metadata={
        'alias': '技能', 'anchor_num': 1, 'sections': ['技能标签']})
    bili_lines: List[str] = field(default_factory=list, init=False, metadata={
        'alias': '台词', 'anchor_num': 1, 'sections': ['basic-info-row-label']})
    biligame_pack: str = field(default='', init=False, metadata={'alias': '武将包'})
    biligame_key: str = field(default='', init=False, metadata={'md_key': ''})
    biligame_skill_ver: str = field(default='', init=False, metadata={'md_key': ''})

    @abstractmethod
    def set_image(self, image): ...
    @abstractmethod
    def set_image_author(self, author): ...

    @property
    def bili_skill_str(self) -> str:
        return self.to_str(self.bili_skills)
    
    @property
    def bili_lines_str(self) -> str:
        return self.to_str(self.bili_lines)
    
    @staticmethod
    def to_str(lists):
        secs = []
        sec = []
        for item in lists:
            if isinstance(item, list):
                if sec:
                    secs.append(UList('li', sec))
                    sec = []
                sec.append(Text(''.join(item) + ' ', 'b'))
            else:
                sec.append(item)
        secs.append(UList('li', sec))
        return UList('ul', secs).md_format()

    def crawl_parse(self, name):
        if not self.biligame_pack and self.biligame_key != 'none':
            not_p_header = True
            try:
                for line in crawl(self.biligame_key if self.biligame_key else name):
                    if line and isinstance(line, GeneralBlock):
                        if not_p_header:
                            not_p_header = self.parse_header(line)
                        elif not self.parse_module(line):
                            break
            except Exception as e:
                logger = logging.getLogger('biligameCrawler')
                logger.error('crawl biligame failed %s', e, exc_info=True, stack_info=True)
        return super().crawl_parse(name)
    
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
                    self.bili_title = sline.removeprefix('武将称号：')
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