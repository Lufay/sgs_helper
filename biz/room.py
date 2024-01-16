from enum import Enum
import random

from utils.redis_util import RedisClient


class Role(Enum):
    Lord = '主公'
    Minister = '忠臣'
    Traitor = '内奸'
    Rebel = '反贼'

class Room:
    redis_client = RedisClient()
    expire_sec = 900
    role_queue_key = 'rq_%s'
    role_user_key = 'ru_%s'

    def __init__(self, room_id, n=0, traitor_cnt=1):
        self.room_id = room_id
        if self.redis_client.client.exists(self.role_queue_key % room_id):
            self.role_queue = None
            if n == 0 or len(self) == n:
                return
            else:
                self.redis_client.client.delete(self.role_queue_key % room_id)
        self.role_queue = list(self.__class__.gen_role_seq(n, traitor_cnt))
        random.shuffle(self.role_queue)

    @staticmethod
    def gen_role_seq(n, traitor_cnt=1):
        yield Role.Lord
        yield from [Role.Rebel]*(n//2)
        if traitor_cnt > 0:
            yield from [Role.Traitor]*traitor_cnt
        minister_cnt = (n-1)//2 - traitor_cnt
        if minister_cnt > 0:
            yield from [Role.Minister]*minister_cnt

    def pop_role(self, user_id) -> Role:
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
        return role
    
    def __len__(self):
        if self.role_queue is None:
            return self.redis_client.client.llen(self.role_queue_key % self.room_id)
        else:
            return len(self.role_queue)
    
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