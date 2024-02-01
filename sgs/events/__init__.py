from abc import ABC, abstractmethod
from itertools import chain
import logging
import common
from ..cards.region import UserRole

class Event(ABC):
    def __init__(self, event_center):
        self.event_center = event_center
        self.role_events = [[]] * len(event_center.role_cycle)

    @abstractmethod
    def trigger(self): ...
    @abstractmethod
    def each(self, user_role: UserRole, pos: int): ...


class EventCenter:

    def __init__(self, room_id, role_cycle):
        self.room_id = room_id
        self.role_cycle = role_cycle
        self.cur_idx = 0
        self.queue = common.manager.Queue()
        # self.process_pool = common.process_pool   不能传pool

    def start(self):
        from .game_events import GameStartEvent, GameCycleEvent
        GameStartEvent(self).trigger()
        GameCycleEvent(self).trigger()

    def settle_cycle(self, event: Event):
        cycle = self.role_cycle
        if (i := self.cur_idx) != 0:
            cycle = chain(cycle[i:], cycle[0:i])
        for i, user_role in enumerate(cycle):
            event.each(user_role, i+1)


def event_err_handler(e):
    logger = logging.getLogger('event')
    logger.exception('event exception: %s', e)