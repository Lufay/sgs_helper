from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import Field, dataclass, field, fields
from functools import cached_property
import logging
from typing import List, _GenericAlias, _SpecialGenericAlias

from utils import classproperty

from .crawler import B, UList, crawl, baike_crawl, Img, GeneralBlock, Text, Table, Header, Caption

def both_in_or_not(s, a, b):
    return (s in a) == (s in b)

class Parser(ABC):
    @abstractmethod
    def crawl_parse(self, name): ...
    @property
    @abstractmethod
    def skills(self): yield
    @property
    @abstractmethod
    def lines(self): yield
    @property
    @abstractmethod
    def title(self) -> str: return ''
    @abstractmethod
    def get_pack(self) -> str: ...

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
    
    def set_field(self, fd:Field, val):
        if func := fd.metadata.get('val_trans'):
            val = func(val)
        if isinstance(fd.type, (_GenericAlias, _SpecialGenericAlias)):
            t = fd.type.__origin__
        else:
            t = fd.type
        if issubclass(t, list):
            getattr(self, fd.name).append(val)
        else:
            setattr(self, fd.name, val)


@dataclass(init=False, eq=False, match_args=False)
class BaiduBaikeParser(Parser):
    baike_title:str = field(default='', init=False, metadata={'alias': '称号'})
    game_mode: str = field(default='', init=False, metadata={'alias':('模式', '出现模式', '所属模式', '适用模式')})
    card_id: str = field(default='', init=False, metadata={'alias': ('编号', '武将编号')})
    baike_skill_names: list = field(default_factory=list, init=False, metadata={'alias': ('技能名称', '名称')})
    baike_skill_descs: list = field(default_factory=list, init=False, metadata={'alias': ('技能描述', '描述', '技能信息')})
    baike_lines: list = field(default_factory=list, init=False)
    baike_attr_ver: str = field(default='', init=False, metadata={'md_key': ''})
    baike_skill_ver: str = field(default='', init=False, metadata={'md_key': ''})
    baike_line_ver: str = field(default='', init=False, metadata={'md_key': ''})
    baike_image_ver: str = field(default='', init=False, metadata={'md_key': ''})

    name = '百度百科'

    @property
    def skills(self):
        skills = []
        for name, desc in zip(self.baike_skill_names, self.baike_skill_descs):
            b = Text(name, 'b')
            skills.append(UList('li', [b, ' ', desc]))
        yield f'{BaiduBaikeParser.name}  \n' + UList('ul', skills).md_format()
        yield from super().skills
    
    @property
    def lines(self):
        yield f'{BaiduBaikeParser.name}  \n' + UList('ul', [UList('li', (line,)) for line in self.baike_lines]).md_format()
        yield from super().lines

    @property
    def title(self):
        return self.baike_title or super().title

    @abstractmethod
    def set_image_author(self, author): ...

    @classproperty(1)
    def module_parsers(cls):
        # table_parser = lambda method_name: (lambda *args: operator.methodcaller(method_name, *args))
        keys = {
            'attr': ('属性', '武将属性', '卡牌属性', '卡牌信息'),
            'skill': ('能力设定', '技能', '武将技能'),
            'line': ('台词', '武将台词', '角色台词', '语音台词'),
            'image': ('角色专属', '皮肤', '武将皮肤')
        }
        parser_mapper = {name:val for name, val in vars(BaiduBaikeParser).items() if name.startswith('parse_')}
        # table_parser(f'parse_{key_type}s' if f'parse_{key_type}s' in parser_names else 'parse_abilities')
        return {key: (parser_mapper.get(f'parse_{key_type}s', cls.parse_abilities), f'baike_{key_type}_ver')
                for key_type, key_tuple in keys.items()
                for key in key_tuple}

    def crawl_parse(self, name):
        if self.baike_skill_ver != 'none' and not self.baike_skill_names:
            self.sub_mod_name = ''
            self.sub_module = {}
            # fill sub_module
            for node in baike_crawl(name):
                if node:
                    match node:
                        case dict():
                            self.parse_basic_info(node)
                        case Header(t) | Caption(t):
                            self.new_sub_mod(t)
                        case Table() if self.sub_mod_name in self.sub_module:
                            self.sub_module[self.sub_mod_name].contents.append(node)
            self.new_sub_mod('')
            # consume sub_module
            for mod_name, table in self.sub_module.items():
                if f_verkey := self.module_parsers.get(mod_name):
                    headers = [str(h) for h in table.headers] if table.headers else ()
                    len_header = len(headers)
                    f, ver_key = f_verkey
                    ver = getattr(self, ver_key)
                    if ver:
                        try:
                            ver_col_idx = headers.index('扩展包')
                        except ValueError:
                            ver_col_idx = 0
                        vers = ver.split('|')
                        if headers:
                            headers = headers[ver_col_idx+len(vers):]
                    for record in table.records:
                        if len_header:
                            assert len(record) == len_header
                        if not ver or all(ver in (record_ver := str(record[ver_col_idx+i])) and \
                                       both_in_or_not('国战', ver, record_ver) for i, ver in enumerate(vers)):
                            cols = record[ver_col_idx+len(vers):] if ver else record
                            # f(headers, cols)(self)
                            f(self, headers, cols)
            del self.sub_mod_name, self.sub_module
        return super().crawl_parse(name)
    
    def parse_basic_info(self, info:dict):
        if '武将称号' in info:
            info.setdefault('称号', info.pop('武将称号'))
        info.setdefault('势力', info.get('所属势力', '未知')[0])
        if '技能' in info:
            del info['技能']
        for alias, fd in self.alias_mapper.items():
            if alias in info:
                self.set_field(fd, info[alias])

    def new_sub_mod(self, name):
        if self.sub_mod_name and (table := self.sub_module.get(self.sub_mod_name)):
            table.iter_children(table.contents)
        self.sub_mod_name = name
        if name in self.module_parsers.keys():
            self.sub_module[name] = Table.empty('table')

    def parse_abilities(self, headers:list, cols: list):
        for i, col in enumerate(cols):
            col_name = headers[i]
            if col_name == '画师':
                self.set_image_author(str(col))
            elif col_name == '武将技能':
                for block in col:
                    if isinstance(block, GeneralBlock):
                        name = ''
                        descs = []
                        for sub_b in block:
                            if isinstance(sub_b, B):
                                name = sub_b
                            elif isinstance(sub_b, GeneralBlock):
                                if any('bold_' in c for c in sub_b.classes):
                                    name = B(str(sub_b), sub_b.__name__)
                                else:
                                    descs.append(str(sub_b))
                            elif sub_b:
                                descs.append(sub_b)
                        self.baike_skill_names.append(name)
                        self.baike_skill_descs.append(''.join(descs))
            elif fd := self.alias_mapper.get(col_name):
                self.set_field(fd, str(col))

    def parse_lines(self, headers:list, cols: list):
        self.baike_lines = [str(d) for col in cols
                            for d in col if d]
    
    def parse_images(self, headers:list, cols: list):
        print(f'image header len: {len(headers)} {headers}')
        print(f'\trecord len: {len(cols)}')


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

    name = 'Bili Game'

    @abstractmethod
    def set_image(self, image): ...
    @abstractmethod
    def set_image_author(self, author): ...

    @property
    def skills(self):
        yield f'{BiligameParser.name}  \n' + BiligameParser.to_ulist(self.bili_skills).md_format()
        yield from super().skills
    
    @property
    def lines(self):
        yield f'{BiligameParser.name}  \n' + BiligameParser.to_ulist(self.bili_lines).md_format()
        yield from super().lines

    @property
    def title(self):
        return self.bili_title or super().title
    
    @staticmethod
    def to_ulist(lists):
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
        if sec:
            secs.append(UList('li', sec))
        return UList('ul', secs)

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
                    if not both_in_or_not('界', self.get_pack(), line):
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