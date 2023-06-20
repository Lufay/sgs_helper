
from dataclasses import dataclass, field
from functools import cached_property
import re
from typing import List

import mistletoe
from mistletoe.ast_renderer import get_ast

from .crawler import Text
from .hero import Hero


@dataclass
class HeroMgr:
    level: int = 1
    cur_pack: str = ''
    status: bool = True
    heros: List[Hero] = field(default_factory=list)
    line_prefix: str = ''

    VALID_HEADING = '武将牌'
    MONARCH_TAG = '主公技'
    HP_PATTERN = re.compile(r'HP=(\d+)(?:/(\d+))?')

    @classmethod
    def load(cls, file_path):
        with open(file_path) as fin:
            doc = mistletoe.Document(fin)
            struct = get_ast(doc)
            mgr = cls()
            for node in struct['children']:
                mgr.process_node(node)
            return mgr

    def pre_process(self, node):
        if node.get('level', self.level+1) <= self.level:
            return True
        return self.status or 'level' not in node

    def post_process(self):
        pass

    def process_node(self, node):
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
        if node['type'] != 'Heading' or node['children'][0]['content'] != self.VALID_HEADING:
            self.status = False

    def process_level_2(self, node):
        if node['type'] == 'Heading':
            self.cur_pack = node['children'][0]['content']

    def process_level_3(self, node):
        if node['type'] == 'Heading':
            self.heros.append(Hero(self.cur_pack, node['children'][0]['content']))

    def process_level_4(self, node):
        getattr(self, f'process_{node["type"]}')(node)

    def process_Paragraph(self, node):
        cur_strs = []
        lines = []
        def add_to_lines():
            nonlocal cur_strs
            raw_line = ''.join(filter(None, cur_strs))
            if not raw_line:
                return
            hero = self.heros[-1]
            if m := self.HP_PATTERN.fullmatch(raw_line):
                hero.hp, hero.hp_max = map(int, m.groups(0))
                if not hero.hp_max and hero.hp:
                    hero.hp_max = hero.hp
                return
            if self.MONARCH_TAG in raw_line:
                self.heros[-1].is_monarch = True
            lines.append(self.line_prefix + raw_line)
            cur_strs = []

        for cont_node in node['children']:
            match cont_node['type']:
                case 'Strong' | 'Emphasis' as t:
                    cont = Text(cont_node['children'][0]['content'], t)
                    cur_strs.append(cont)
                case 'RawText':
                    cur_strs.append(cont_node['content'])
                case 'LineBreak':
                    add_to_lines()
                case _ as t:
                    raise TypeError(t)
        add_to_lines()
        if cont := '\n'.join(filter(None, lines)):
            self.heros[-1].contents.append(cont)
    
    def process_List(self, node):
        for item in node['children']:
            self.line_prefix = item['leader'] + ' '
            for child in item['children']:
                self.process_node(child)
            self.line_prefix = ''


    # @cached_property
    # def packs(self):
    #     return {hero.pack for hero in self.heroes}

    def search(self, name, pack='*'):
        return [hero for hero in self.heros
               if (pack == '*' or pack in hero.pack) and
               name in hero.name
               ]
    
    @cached_property
    def monarchs(self):
        return {hero.name for hero in self.heros if hero.is_monarch}
    
    @cached_property
    def all_heros(self):
        return [f'{hero.name}@{hero.pack}' for hero in self.heros]  # if hero.contents

