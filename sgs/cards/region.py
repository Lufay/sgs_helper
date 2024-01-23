import random
from .card import Card


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