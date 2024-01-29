from dataclasses import dataclass
from enum import IntFlag, unique
from functools import cached_property
import inspect
from pathlib import Path
import pickle
import random
import string
import sys
from typing import Any

from utils import classproperty


@unique
class CardType(IntFlag):
    BASE = 1
    STRATAGEM = 2
    STRATAGEM_NORMAL = STRATAGEM | (1<<2)
    STRATAGEM_DELAY = STRATAGEM | (2<<2)
    EQUIPMENT = 3
    EQUIPMENT_ARMS = EQUIPMENT | (1<<2)
    EQUIPMENT_ARMOR = EQUIPMENT | (2<<2)
    EQUIPMENT_OFFENSE = EQUIPMENT | (3<<2)
    EQUIPMENT_DEFENCE = EQUIPMENT | (4<<2)
    EQUIPMENT_TREASURE = EQUIPMENT | (5<<2)

    def __eq__(self, other):
        if self > 3 and other < 4:
            return (self & 3) == other
        else:
            return super().__eq__(other)


@dataclass
class Card:
    card_id: str
    name: str
    card_type: CardType

    suit_seq = ('黑桃', '梅花', '红桃', '方块')
    name = None
    card_type = None
    @classmethod
    def make(cls, card_id):
        assert cls.name or getattr(cls, 'names', None)
        assert cls.card_type
        return cls(card_id, cls.name or random.choice(cls.names), cls.card_type)
    
    @classmethod
    def load(cls, collection='all'):
        '''从缓存或文档加载牌库
        返回Card 的生成器
        '''
        from .card_conf import doc_id, table_ids
        from common import conf
        from utils.fs_util import get_doc_table
        match collection:
            case 'all':
                colls = table_ids.keys()
            case str():
                if ',' in collection:
                    colls = collection.split(',')
                else:
                    colls = [collection]
            case list() | tuple() | set():
                colls = collection
            case _:
                raise KeyError(f'unknown collection {collection}')
        for coll in colls:
            p = Path(f"{conf['Local']['CardDumpPath']}{coll}.pickle")
            if p.is_file():
                with p.open('rb') as f:
                    yield from pickle.load(f)
            else:
                cards = []
                for table_id in table_ids[coll]:
                    d = get_doc_table(doc_id, table_id)
                    for color, ids in d.items():
                        color_key = color.rsplit('(', 2)[1].split(')', 2)[0]
                        assert len(color_key) == 1
                        for n, name in ids.items():
                            if '|' in name:
                                for i, sub_name in enumerate(name.split('|')):
                                    if sn := sub_name.strip():
                                        card = cls.sub_cls_mapping[sn].make(color_key*(i+1) + n)
                                        cards.append(card)
                            elif sn := name.strip():
                                card = cls.sub_cls_mapping[sn].make(color_key + n)
                                cards.append(card)
                with p.open('wb') as f:
                    pickle.dump(cards, f)
                yield from cards

    @classproperty(1)
    def sub_cls_mapping(cls) -> dict:
        mapping = {}
        for _, cc in inspect.getmembers(sys.modules[cls.__module__], inspect.isclass):
            if issubclass(cc, cls):
                if cc.name:
                    mapping[cc.name] = cc
                elif getattr(cc, "names", None):
                    mapping.update((name, cc) for name in cc.names)
        return mapping
    
    @cached_property
    def suit_color(self):
        idx = string.ascii_letters.index(self.card_id[0])
        return self.suit_seq[idx % 26 % 4]
    
    def __str__(self):
        return f'[{self.suit_color}{self.card_id[1]} {self.name}]'
                

class BaseCard(Card):
    name = None
    card_type = CardType.BASE

class Kill(BaseCard):
    name = '杀'

class FireKill(Kill):
    name = '火杀'

class LightningKill(Kill):
    name = '雷杀'

class Dodge(BaseCard):
    name = '闪'

class Peach(BaseCard):
    name = '桃'

class Alcohol(BaseCard):
    name = '酒'

class StratagemCard(Card):
    name = None
    card_type = CardType.STRATAGEM

class NormalStratagemCard(StratagemCard):
    card_type = CardType.STRATAGEM_NORMAL

class DelayStratagemCard(StratagemCard):
    card_type = CardType.STRATAGEM_DELAY

class Impeccable(NormalStratagemCard):
    name = '无懈可击'

class GetMore(NormalStratagemCard):
    name = '无中生有'

class Steal(NormalStratagemCard):
    name = '顺手牵羊'

class Break(NormalStratagemCard):
    name = '过河拆桥'

class Borrow(NormalStratagemCard):
    name = '借刀杀人'

class Duel(NormalStratagemCard):
    name = '决斗'

class Fire(NormalStratagemCard):
    name = '火攻'

class Chain(NormalStratagemCard):
    name = '铁索连环'

class Beacon(NormalStratagemCard):
    name = '南蛮入侵'

class Volley(NormalStratagemCard):
    name = '万箭齐发'

class Share(NormalStratagemCard):
    name = '五谷丰登'

class Inclusive(NormalStratagemCard):
    name = '桃园结义'

class Jail(DelayStratagemCard):
    name = '乐不思蜀'

class Famine(DelayStratagemCard):
    name = '兵粮寸断'

class Lightning(DelayStratagemCard):
    name = '闪电'

class EquipmentCard(Card):
    card_type = CardType.EQUIPMENT

class ArmsCard(EquipmentCard):
    card_type = CardType.EQUIPMENT_ARMS

class ArmorCard(EquipmentCard):
    card_type = CardType.EQUIPMENT_ARMOR

class OffenseHorse(EquipmentCard):
    card_type = CardType.EQUIPMENT_OFFENSE
    names = ['赤兔', '紫骍', '大宛']

class DefenceHorse(EquipmentCard):
    card_type = CardType.EQUIPMENT_DEFENCE
    names = ['绝影', '的卢', '爪黄飞电', '骅骝']

class TreasureCard(EquipmentCard):
    card_type = CardType.EQUIPMENT_TREASURE

class Crossbow(ArmsCard):
    name = '诸葛连弩'

class DoubleSword(ArmsCard):
    name = '雌雄双股剑'

class SharpSword(ArmsCard):
    name = '青釭剑'

class IceSword(ArmsCard):
    name = '寒冰剑'

class Machete(ArmsCard):
    name = '古锭刀'

class SnakeSpear(ArmsCard):
    name = '丈八蛇矛'

class Falchion(ArmsCard):
    name = '青龙偃月刀'

class Poleaxe(ArmsCard):
    name = '贯石斧'

class SilverSpear(ArmsCard):
    name = '银月枪'

class Halberd(ArmsCard):
    name = '方天画戟'

class FeatherFan(ArmsCard):
    name = '朱雀羽扇'

class Bow(ArmsCard):
    name = '麒麟弓'

class Shield(ArmorCard):
    name = '仁王盾'

class Taichi(ArmorCard):
    name = '八卦阵'

class Armour(ArmorCard):
    name = '藤甲'

class Helmet(ArmorCard):
    name = '白银狮子'

class MechanicalBull(TreasureCard):
    name = '木牛流马'


if __name__ == '__main__':
    c = OffenseHorse.make('jj')
    match c.card_type:
        case CardType.EQUIPMENT_OFFENSE:
            print('offense')
        case CardType.EQUIPMENT:
            print(c.name)
        case _:
            print('default')