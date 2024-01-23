from dataclasses import dataclass, field
from functools import cached_property
import json
import re
from typing import List

import mistletoe
from mistletoe.ast_renderer import get_ast

from .crawler import GeneralBlock, Text, UList
from .hero import Hero
from common import root_path

@dataclass
class HeroMgr:
    '''加载武将的md 文件，获取武将全集
    heros: 武将列表
    level: 当前的md 层级(以header层级为准)
    cur_pack: 当前武将的所属武将包
    status: 是否处理当前节点的非正文子节点的状态开关(正文子节点始终遍历)
    line_prefix: 当前的md 列表前缀字符(用以表示当前正文是列表)

    VALID_HEADING: md 中有效的一级节点
    MONARCH_TAG: 判断是否是主公的标识
    HP_PATTERN: md 中的体力值正则
    str_patterns: hero 的字段正则
    '''
    heros: List[Hero] = field(default_factory=list)

    level: int = 1
    cur_pack: str = ''
    status: bool = True
    line_prefix: str = ''

    VALID_HEADING = '武将牌'
    MONARCH_TAG = '主公技'
    HP_PATTERN = re.compile(r'HP=(\d+)(?:/(\d+))?')
    str_patterns = {fd_name: re.compile(md_key + r':\s*([^\s]*)$')
        for fd_name, md_key in Hero.md_fields.items()
    }

    @classmethod
    def load(cls, file_path):
        '''加载并解析md 文件
        '''
        with open(file_path) as fin:
            doc = mistletoe.Document(fin)
            struct = get_ast(doc)
            (root_path / 'page_cache/md.json').write_text(json.dumps(struct, indent=2))
            mgr = cls()
            for node in struct['children']:
                mgr.process_node(node)
            return mgr

    def pre_process(self, node):
        '''节点处理的前置拦截
        遇到同级、高级、未知级别的节点则直接放行(只有header 有level 正文段落是没有level)
        遇到子节点取决于状态开关
        '''
        if node.get('level', self.level+1) <= self.level:
            return True
        return self.status or 'level' not in node

    def post_process(self):
        pass

    def process_node(self, node):
        '''有level 属于header, 则更新level
        没有level 属于正文段落, 仅在第一个段落level增一, 然后关掉开关, 避免下个段落再增
        '''
        if self.pre_process(node):
            if level := node.get('level', None):
                self.level = level
                self.status = True
            elif self.status:
                self.level += 1
                self.status = False
            getattr(self, f'process_level_{self.level}')(node)
        self.post_process()

    def process_level_1(self, node):
        '''处理一级类目节点
        '''
        if node['type'] != 'Heading' or node['children'][0]['content'] != self.VALID_HEADING:
            self.status = False

    def process_level_2(self, node):
        '''处理二级包名节点
        '''
        if node['type'] == 'Heading':
            self.cur_pack = node['children'][0]['content']

    def process_level_3(self, node):
        '''处理三级武将名节点
        '''
        if node['type'] == 'Heading':
            child = node['children'][0]
            if child['type'] == 'RawText':
                self.heros.append(Hero(self.cur_pack, child['content']))
            else:
                self.status = False

    def process_level_4(self, node):
        '''处理四级正文节点，转发给对应节点类型的处理器
        '''
        getattr(self, f'process_{node["type"]}')(node)

    def process_Paragraph(self, node):
        '''段落节点处理器
        识别段落子节点类型并处理之
        lines 就是hero.content 中的一个段落
        '''
        cur_strs = []
        lines = []
        def add_to_lines():
            '''段落行处理器
            1. 处理行正则规则
            2. 判断是否主公
            3. 不满足正则规则的都放入lines中
            '''
            block = GeneralBlock('div', cur_strs)
            raw_line = str(block)
            if raw_line:
                hero = self.heros[-1]
                if m := self.HP_PATTERN.fullmatch(raw_line):
                    hero.hp, hero.hp_max = map(int, m.groups(0))
                    if not hero.hp_max and hero.hp:
                        hero.hp_max = hero.hp
                    return
                else:
                    for fd_name, pattern in self.str_patterns.items():
                        if m := pattern.match(raw_line):
                            setattr(hero, fd_name, m.group(1))
                            return
                if self.MONARCH_TAG in raw_line:
                    self.heros[-1].is_monarch = True
                if self.line_prefix:
                    lines.append(UList.copy_from_block('li', block, self.line_prefix))
                else:
                    lines.append(block)

        for cont_node in node['children']:
            match cont_node['type']:
                case 'Strong' | 'Emphasis' as t:
                    cont = Text(cont_node['children'][0]['content'], t)
                    cur_strs.append(cont)
                case 'RawText':
                    cur_strs.append(cont_node['content'])
                case 'LineBreak':
                    add_to_lines()
                    cur_strs.clear()
                case _ as t:
                    raise TypeError(t)
        add_to_lines()
        if lines:
            self.heros[-1].contents.append(GeneralBlock('p', UList.list_collect(lines)))
    
    def process_List(self, node):
        '''处理正文中的list 段落
        将子元素按正文一样处理(用以支持list的嵌套)
        '''
        for item in node['children']:
            self.line_prefix = item['leader']
            for child in item['children']:
                self.process_node(child)
            self.line_prefix = ''

    # @cached_property
    # def packs(self):
    #     return {hero.pack for hero in self.heroes}

    def search(self, name, pack='*'):
        return [hero.crawl_by_name() for hero in self.heros
               if (pack == '*' or pack in hero.pack) and
               name in hero.name
               ]
    
    @cached_property
    def monarchs(self):
        return {hero.name for hero in self.heros if hero.is_monarch}
    
    @cached_property
    def all_heros(self):
        return [hero.uni_name for hero in self.heros]  # if hero.contents

