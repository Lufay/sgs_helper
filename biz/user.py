from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import cached_property
import hashlib
import os
import pickle
from typing import MappingView, Optional


@dataclass
class Record:
    game_mode: str
    role: str
    r_time: datetime = datetime.now()

    @cached_property
    def r_key(self):
        m = hashlib.md5(f'{self.game_mode}\t{self.role}'.encode('utf8'))
        return m.hexdigest()


@dataclass
class User:
    name: str
    records: dict = field(default_factory=dict)
    last_record_time: Optional[datetime] = None
    luck_consumed: int = 0
    rep_consumed: int = 0

    def add_record(self, game_mode, role):
        record = Record(game_mode, role)
        if not self.last_record_time or (record.r_time - self.last_record_time) > timedelta(minutes=5):
            self.records[record.r_key] = record
            self.last_record_time = record.r_time
            return True
        else:
            return False
        
    @property
    def luck_num(self):
        return len(self.records) - self.luck_consumed
    
    @property
    def rep_num(self):
        return len(self.records) - self.rep_consumed
    
    def __get_state__(self):
        dump_dict = vars(self).copy()
        remove_num = min(self.luck_consumed, self.rep_consumed)
        if remove_num:
            sorted_records = sorted(self.records.values(), key=lambda x: x.r_time)
            dump_dict['records'] = list(sorted_records)[remove_num:]
            dump_dict['luck_consumed'] -= remove_num
            dump_dict['rep_consumed'] -= remove_num
        else:
            dump_dict['records'] = self.records.values()
        return dump_dict
    
    def __set_state__(self, state):
        super().__setattr__(state)
        if isinstance(self.records, (list, MappingView)):
            self.records = {r.r_key: r for r in self.records}


class UserMgr:
    user_dict = {}

    @classmethod
    def load(cls, file_path:str):
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                user_list = pickle.load(f)
                cls.user_dict = {u.name: u for u in user_list}

    @classmethod
    def dump(cls, file_path:str):
        with open(file_path, 'wb') as f:
            pickle.dump(list(cls.user_dict.values()), f)
        print('dump done')
    
    @classmethod
    def get_user(cls, name) -> User:
        return cls.user_dict.setdefault(name, User(name))


if __name__ == '__main__':
    u = UserMgr.get_user('tester')
    u.add_record('3v3', '庞德')
    u = UserMgr.get_user('felix')
    u.add_record('3v3', '张星彩')
    print(UserMgr.dump('./dump_user'))
    UserMgr.user_dict = None
    u = UserMgr.get_user('felix')
    print(u)
    print(UserMgr.user_dict)
    u = UserMgr.get_user('tester')
    print(u)