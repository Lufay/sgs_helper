import logging
import random

from utils.redis_util import RedisClient
import common
from .role import Role


class Room:
    '''一局游戏的角色分配
    一局游戏的数据缓存15min
    '''
    redis_client = RedisClient()
    expire_sec = 900
    role_queue_key = 'rq_%s'
    role_user_key = 'ru_%s'
    rooms_queue = {}

    def __init__(self, room_id, n=0, traitor_cnt=1, collection='all'):
        '''仅提供ID, 则是获取一个缓存的游戏局
        否则会新建一局游戏
        '''
        self.room_id = room_id
        self.collection = collection
        if self.redis_client.client.exists(self.role_queue_key % room_id):
            self.role_queue = None
            if n == 0 or len(self) == n:
                return
            else:
                self.redis_client.client.delete(self.role_queue_key % room_id)
        if n > 1:
            self.role_queue = list(self.__class__.gen_role_seq(n, traitor_cnt))
            random.shuffle(self.role_queue)
        else:
            self.role_queue = None

    @staticmethod
    def gen_role_seq(n, traitor_cnt=1):
        '''角色分配算法：
        1主、半数反、定额内、其余忠
        '''
        yield Role.Lord
        yield from [Role.Rebel]*(n//2)
        if traitor_cnt > 0:
            yield from [Role.Traitor]*traitor_cnt
        minister_cnt = (n-1)//2 - traitor_cnt
        if minister_cnt > 0:
            yield from [Role.Minister]*minister_cnt

    def pop_role(self, user_id) -> Role:
        '''为了一个用户重复取身份, 用user_id 缓存其在该局游戏的身份
        '''
        client = self.redis_client.client
        redis_key = self.role_user_key % self.room_id
        if client.hexists(redis_key, user_id):
            value = client.hget(redis_key, user_id)
            return Role(value.decode())
        if self.role_queue is None:
            value = client.rpop(
                self.role_queue_key % self.room_id)
            role = Role(value.decode())
        else:
            role = self.role_queue.pop()
            value = role.value.encode()
        ret = client.hset(redis_key, user_id, value)
        print(f'cache user {user_id} role {role} return {ret}')
        ret = client.expire(redis_key, self.expire_sec)
        print(f'refresh user {user_id}, return {ret}')
        self.lock = common.manager.Lock()
        common.process_pool.apply_async(self.check_all_seat, callback=self.all_seat_done, error_callback=self.check_seat_error)   # call_it, (self,)
        return role

    def check_all_seat(self):
        if len(self) == 0 and self.room_id not in self.rooms_queue:
            rc = RedisClient()
            redis_key = self.role_user_key % self.room_id
            if self.lock.acquire(timeout=3):
                if self.room_id in self.rooms_queue:
                    return ()
                from .cards.region import UserRole
                role_cycle = [
                    UserRole(field.decode(), Role(value.decode()), self)
                    for field, value in rc.client.hscan_iter(redis_key)
                ]
                random.shuffle(role_cycle)
                for i, uc in enumerate(role_cycle):
                    if uc.role is Role.Lord:
                        return role_cycle[i:] + role_cycle[0:i]
                return ()

    def all_seat_done(self, role_cycle):
        if role_cycle:
            from .events import EventCenter, event_err_handler
            ec = EventCenter(self.room_id, role_cycle)
            self.rooms_queue[self.room_id] = ec.queue
            common.process_pool.apply_async(ec.start, callback=self.game_end, error_callback=event_err_handler)
        if role_cycle is not None:
            self.lock.release()
        del self.lock

    def check_seat_error(self, e):
        logger = logging.getLogger('allSeat')
        logger.exception('check all seat exception: %s', e)
        self.lock.release()
        del self.lock

    def game_end(self, res):
        print(f'房间{self.room_id} 游戏结束')
        self.offline()

    def __len__(self):
        if self.role_queue is None:
            return self.redis_client.client.llen(self.role_queue_key % self.room_id)
        else:
            return len(self.role_queue)
        
    def online(self):
        ...

    def offline(self):
        if self.room_id in self.rooms_queue:
            del self.rooms_queue[self.room_id]

    def cache(self):
        client = self.redis_client.client
        redis_key = self.role_queue_key % self.room_id
        ret = client.rpush(redis_key,
                           *(item.value.encode() for item in self.role_queue))
        rsp = client.expire(redis_key, self.expire_sec)
        print('redis expired response:', rsp)
        return ret


if __name__ == '__main__':
    r = Room('test_room_id', 8)
    print(r.cache())
    for i in range(8):
        print(r.pop_role(f'user{i}'))
    rr = Room('test_room_id', 8)
    for i in range(8):
        print(rr.pop_role(f'user{i}'))