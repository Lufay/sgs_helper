from dataclasses import dataclass, field
import random

from ..role import Role
from .card import Card
from ..heros.hero import Camp, Hero
from ..room import Room


class CardHeapEmpty(EOFError):
    ...

class CardHeap:
    def __init__(self, collection='all'):
        self.coll = collection
        cards = list(Card.load(collection))
        random.shuffle(cards)
        self.un_cards = cards
        self.us_cards = []

    def pop(self, n=2):
        length = len(self.un_cards)
        if (length + len(self.us_cards)) < n:
            raise CardHeapEmpty()
        if length < n:
            self.shuffle()
        for i in range(n):
            yield self.un_cards.pop()

    def shuffle(self):
        random.shuffle(self.us_cards)
        self.us_cards.extend(self.un_cards)
        self.un_cards = self.us_cards
        self.us_cards = []

    def push_up(self, *cards):
        self.un_cards.extend(cards)

    def push_down(self, *cards):
        self.un_cards = cards + self.un_cards

    def discard(self, *cards):
        self.us_cards.extend(cards)


class CardHeapMgr:
    card_heap_map = {}

    def __get__(self, ins, owner=None):
        room_id = ins.room.room_id
        if room_id in self.card_heap_map:
            return self.card_heap_map[room_id]
        else:
            ch = CardHeap(ins.room.collection)
            self.card_heap_map[room_id] = ch
            return ch
    
    def __set__(self, ins, value):
        raise NotImplementedError('CardHeap cannot be set')
    
    def __delete__(self, ins):
        del self.card_heap_map[ins.room.room_id]


@dataclass
class UserRole:
    user_id: str
    role: Role
    room: Room
    hero_name: str = ''
    hero_pack: str = ''
    hp: int = 0
    hp_max: int = 0
    camp: Camp = Camp.UNKNOWN
    gender: int = 0
    judge_region: list = field(default_factory=list)
    equip_region: dict = field(default_factory=dict)
    tag_dict: dict = field(default_factory=dict)

    card_heap = CardHeapMgr()

    def __post_init__(self):
        self.own_region = list(self.card_heap.pop(4))

    def set_hero(self, hero: Hero):
        self.hero_name = hero.name
        self.hero_pack = hero.pack
        self.hp = hero.hp
        self.hp_max = hero.hp_max
        self.camp = hero.camp
        self.gender = hero.gender