from dataclasses import dataclass, field
import random

from ..role import Role
from .card import Card
from ..heros.hero import Camp


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


@dataclass
class UserRole:
    user_id: str
    role: Role
    hero_id: str = ''
    hp: int = 0
    hp_max: int = 0
    camp: Camp = Camp.UNKNOWN
    gender: int = 0
    judge_region: list = field(default_factory=list)
    equip_region: dict = field(default_factory=dict)
    own_region: list = field(default_factory=list)
    tag_dict: dict = field(default_factory=dict)