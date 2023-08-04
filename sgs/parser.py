from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import Field, dataclass, field, fields
from functools import cached_property
import logging
from typing import List, _GenericAlias, _SpecialGenericAlias

from utils import classproperty

from .crawler import B, UList, crawl, baike_crawl, Img, GeneralBlock, Text, Table, Header, Caption

def both_in_or_not(s, a, b):
    if isinstance(s, (list, tuple)):
        return all(both_in_or_not(ss, a, b) for ss in s)
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
        '''别名到field 的映射, 支持多个别名
        '''
        d = {}
        for fd in fields(self):
            if alias := fd.metadata.get('alias'):
                if isinstance(alias, tuple):
                    d.update({alias_item:fd for alias_item in alias})
                else:
                    d[alias] = fd
        return d
    
    def set_field(self, fd:Field, val):
        '''field 赋值器, 支持值转换函数
        '''
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

    @cached_property
    def hps(self):
        return [
            fv for sub_p in Parser.__subclasses__()
            for fname in vars(sub_p)
            if fname.endswith('_hp') and isinstance(fv := getattr(self, fname), int)
        ]


@dataclass(init=False, eq=False, match_args=False)
class BaiduBaikeParser(Parser):
    baike_title:str = field(default='', init=False, metadata={'alias': '称号'})
    game_mode: str = field(default='', init=False, metadata={'alias':('模式', '出现模式', '所属模式', '适用模式', '游戏模式')})
    card_id: str = field(default='', init=False, metadata={'alias': ('编号', '武将编号', '卡牌编号')})
    baike_hp: int = field(default=0, init=False, metadata={'alias': ('体力', '体力上限'), 'val_trans': lambda s: int(s.partition('勾玉')[0])})
    baike_skill_names: list = field(default_factory=list, init=False, metadata={'alias': ('技能名称', '名称')})
    baike_skill_descs: list = field(default_factory=list, init=False, metadata={'alias': ('技能描述', '描述', '技能信息', '技能介绍', '内容')})
    baike_lines: list = field(default_factory=list, init=False)
    baike_key: str = field(default='', init=False, metadata={'md_key': ''})
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
        yield f'{BaiduBaikeParser.name}  \n' + UList(
            'ul', [UList('li', line) for line in self.baike_lines]).md_format(line_break=': ')
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
            'line': ('台词', '武将台词', '角色台词', '语音台词', '身份局'),
            'image': ('角色专属', '皮肤', '武将皮肤')
        }
        parser_mapper = {name:val for name, val in vars(BaiduBaikeParser).items() if name.startswith('parse_')}
        # table_parser(f'parse_{key_type}s' if f'parse_{key_type}s' in parser_names else 'parse_abilities')
        return {key: (parser_mapper.get(f'parse_{key_type}s', cls.parse_abilities), f'baike_{key_type}_ver')
                for key_type, key_tuple in keys.items()
                for key in key_tuple}

    def crawl_parse(self, name):
        '''处理baike_crawl 抓取的每个节点, 分成两步:
        1. 处理基本信息 & 做模块映射(module_name -> module table)
        2. 逐模块(table)处理: 通过版本指示来决定生效行

        通过baike_skill_names 做幂等
        '''
        if self.baike_skill_ver != 'none' and not self.baike_skill_names:
            self.sub_mod_name = ''
            self.sub_module = {}
            # fill sub_module
            for node in baike_crawl(self.baike_key if self.baike_key else name):
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
                if (f_verkey := self.module_parsers.get(mod_name)) and table.records:
                    headers = [str(h) for h in table.headers] if table.headers else ()
                    len_header = len(headers)
                    f, ver_key = f_verkey
                    if ver_key != 'baike_skill_ver':
                        remove_col_idx = [i for i, h in enumerate(headers) if '技能' in h]
                        for i in remove_col_idx:
                            headers.pop(i)
                    self.remove_keys_prefix(headers)
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
                                       both_in_or_not(('国战', '界'), ver, record_ver) for i, ver in enumerate(vers)):
                            if ver_key != 'baike_skill_ver':
                                for i in remove_col_idx:
                                    record.pop(i)
                            if ver:
                                record = record[ver_col_idx+len(vers):]
                            # f(headers, cols)(self)
                            f(self, headers, record)
            del self.sub_mod_name, self.sub_module
        return super().crawl_parse(name)
    
    @staticmethod
    def remove_keys_prefix(headers):
        for key in ('武将称号', '武将体力', '武将势力'):
            if key in headers:
                short_key = key.removeprefix('武将')
                if isinstance(headers, dict):
                    headers.setdefault(short_key, headers.pop(key))
                else:
                    headers[headers.index(key)] = short_key
    
    def parse_basic_info(self, info:dict):
        self.remove_keys_prefix(info)
        info.setdefault('势力', info.get('所属势力', '未知')[0])
        for a_name in ('技能名称', '技能'):
            if a_name in info:
                del info[a_name]
        for alias, fd in self.alias_mapper.items():
            if alias in info:
                self.set_field(fd, info[alias])

    def new_sub_mod(self, name):
        '''探测到一个新的模块名, 就将前一个模块table 进行收集, 并生成一个新的空模块table
        '''
        if self.sub_mod_name and (table := self.sub_module.get(self.sub_mod_name)):
            table.iter_children(table.contents)
        self.sub_mod_name = name
        if name in self.module_parsers.keys():
            self.sub_module[name] = Table.empty('table')

    def parse_abilities(self, headers:list, cols: list):
        '''通用模块table 处理器
        header 是已经字符串化的表头内容
        cols 是命中ver的这一行的各列原生内容的列表
        '''
        for i, col in enumerate(cols):
            col_name = headers[i]
            if col_name == '画师':
                self.set_image_author(str(col))
            elif col_name in ('武将技能', '技能'):
                self.parse_skill_blocks(col)
            elif fd := self.alias_mapper.get(col_name):
                if fd.name == 'baike_skill_descs' and len(self.baike_skill_names) <= len(self.baike_skill_descs):
                    self.parse_skill_blocks(col)
                else:
                    self.set_field(fd, str(col))

    def parse_skill_blocks(self, blocks: List[GeneralBlock]):
        for block in blocks:
            if isinstance(block, GeneralBlock):
                name = ''
                descs = []
                for sub_b in block:
                    if isinstance(sub_b, B) and not name:
                        name = sub_b
                    elif isinstance(sub_b, GeneralBlock):
                        if any('bold_' in c for c in sub_b.classes) and not name:
                            name = B(str(sub_b), sub_b.__name__)
                        else:
                            descs.append(str(sub_b))
                    elif sub_b:
                        descs.append(sub_b)
                self.baike_skill_names.append(name)
                self.baike_skill_descs.append(''.join(descs))

    def parse_lines(self, headers:list, cols: list):
        '''台词模块table 处理器
        header 是已经字符串化的表头内容(不消费)
        cols 是命中ver的这一行的各列原生内容的列表
        '''
        lines = []
        for col in cols:
            len_line = len(lines)
            for i, block in enumerate(col):
                line = [sub_b if isinstance(sub_b, str) else str(sub_b) for sub_b in block]
                if i < len_line:
                    lines[i].extend(line)
                else:
                    lines.append(line)
        self.baike_lines.extend(lines)
    
    def parse_images(self, headers:list, cols: list):
        '''皮肤模块table 处理器
        TODO: Implement
        '''
        print(f'image header len: {len(headers)} {headers}')
        print(f'\trecord len: {len(cols)}')


@dataclass(init=False, eq=False, match_args=False)
class BiligameParser(Parser):
    bili_title: str = field(default='', init=False, metadata={'alias': '武将称号'})
    bili_hp: int = field(default=0, init=False, metadata={'alias': '勾玉', 'val_trans': int})
    bili_skills: List[str] = field(default_factory=list, init=False, metadata={
        'alias': '技能', 'anchor_num': 1, 'sections': ['技能标签']})
    bili_lines: List[str] = field(default_factory=list, init=False, metadata={
        'alias': '台词', 'anchor_num': 1, 'sections': ['basic-info-row-label']})
    biligame_pack: str = field(default='', init=False, metadata={'alias': '武将包'})
    biligame_key: str = field(default='', init=False, metadata={'md_key': ''})
    biligame_ver: str = field(default='sgs', init=False, metadata={'md_key': ''})
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
        '''将bili_skills, bili_lines 这种特殊的层级栈结构转换为Ulist
        '''
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
        '''先解析表头, 再解析指定版本的表体
        缓存是否已解析过表头, 避免重复调用parse_header

        通过biligame_pack做幂等
        '''
        if not self.biligame_pack and self.biligame_key != 'none':
            not_p_header = True
            try:
                for line in crawl(self.biligame_key if self.biligame_key else name, self.biligame_ver):
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
        '''叶子节点: 识别alias, 将field赋值给key; 根据key 给对应的field 赋值 
        '''
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
        '''解析表头
        由于表头无明显标识, 只能边解析, 边确认是否是表头
        '''
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
        '''递归解析每个锚点块
        叶子节点(str, image)交给alias_matcher
        非叶子节点(table, div)进行递归(借助anchor构建层级list)
        '''
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
            elif isinstance(line, Img):
                if '形象' in line.alt:
                    self.set_image(line)
                    self.key = 'author'
                    self.hit_alias = '形象'
                    self.anchor = Anchor()
                else:
                    self.alias_matcher(line.alt.strip())
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


class Anchor:
    '''带层级栈的辅助构造单例类
    层级栈是一个list, 这个list 可以嵌套list 从而形成层级，或者说形成一颗树，而树的叶子节点就是一个字符串
    '''
    _ins = None
    
    def __new__(cls, *args, **kwargs):
        return cls.get_ins()
    
    @classmethod
    def get_ins(cls):
        '''仅获取单例
        单例未初始化时不要使用
        '''
        if cls._ins is None:
            cls._ins = object.__new__(cls)
        return cls._ins
    
    def __init__(self, level=-1, stack=None, sections=None):
        '''获取单例并初始化
        level: 当前的层级, 负值则anchor 无效
        stack: 当前的栈顶list
        sections: 由tag.class 构成的序列，当发现命中时，序列索引+1, 栈升高一层
        sec_idx: sections 的当前待命中索引
        running: anchor 功能的控制开关。当关闭时，不再进行层级计数和升栈
        '''
        self.level = level
        self.stack = stack
        self.sections = sections
        self.sec_idx = 0 if self.sections else -1
        self.running = True

    @contextmanager
    def __call__(self, classes, cf):
        '''anchor 的核心功能：层级计数和升栈
        classes: 当前tag的class 元组
        cf: anchor 失效(level降维负)后的清理操作
        '''
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