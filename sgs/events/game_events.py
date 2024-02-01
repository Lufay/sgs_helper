import random
from sgs.cards.region import UserRole
from utils.fs_template.cards import pick_hero_card
from utils.fs_util import send_card, send_msg
from . import Event
from ..heros import hero_mgr


class GameStartEvent(Event):
    def __init__(self, event_center):
        super().__init__(event_center)
        self.monarch_pool = random.sample(hero_mgr.monarchs, 3)
        user_cnt = len(event_center.role_cycle)
        self.hero_pool = random.sample(hero_mgr.all_heros, user_cnt*3-1)

    def trigger(self):
        self.event_center.settle_cycle(self)
        for i in range(len(self.event_center.role_cycle)):
            self.set_role_hero(*self.event_center.queue.get())
        # TODO: 更新个人消息，展示初始手牌
        # TODO: 更新群消息，展示每个位次的武将
        # TODO: 触发游戏开始时机的技能

    def each(self, user_role: UserRole, pos: int):
        if pos == 1:
            heros = self.monarch_pool + self.hero_pool[-2:]
        else:
            heros = self.hero_pool[(pos-2)*3 : (pos-1)*3]
        send_card(user_role.user_id, pick_hero_card(self.event_center.room_id, pos, heros), 'open_id')

    def set_role_hero(self, user_id, hero):
        for ur in self.event_center.role_cycle:
            if ur.user_id == user_id:
                return ur.set_hero(hero)


class GameCycleEvent(Event):
    def trigger(self):
        while True:
            # TODO: 设置轮次，可以不用设置，用cur_idx / room_size
            self.event_center.settle_cycle(self)
            # TODO: 满足获胜条件退出
            break

    def each(self, user_role: UserRole, pos: int):
        print(pos, user_role.user_id, user_role.hero_name, user_role.hero_pack)
        GameRoundEvent(self.event_center).trigger()
        self.event_center.cur_idx += 1


class GameRoundEvent(Event):
    def trigger(self):
        return super().trigger()
    
    def each(self, user_role: UserRole, pos: int):
        return super().each(user_role, pos)