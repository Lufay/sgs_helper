from contextlib import contextmanager, closing
import json
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from click import Path
from redis import Redis, from_url as redis_from_url


class RedisClient:
    def __init__(self):
        self.client = Redis()

    def idempotent(self, key, timeout=60):
        '''return:
        True: 幂等通过
        None: 幂等失败
        '''
        return self.client.set(key, 0, timeout, nx=True)
    
    @contextmanager
    def lock(self, key, timeout=5, retry_times=0, retry_interval=0.1):
        if retry_times:
            for i in range(retry_times):
                if self.client.set(key, i, timeout, nx=True):
                    yield True
                    self.client.delete(key)
                    break
                else:
                    time.sleep(retry_interval)
            else:
                yield False
        else:
            yield self.client.set(key, 1, timeout, nx=True)
            self.client.delete(key)


def cache_token(target: str, token_key, expire_key, r_token_key=None):
    '''缓存dict 结果装饰器
    token_key: dict 中token 的key
    expire_key: dict 中token 过期时间戳的key
    r_token_key: dict 中用于刷新token 的key
    '''
    up = urlparse(target)
    if up.scheme == 'file':
        f = Path(up.path)
    elif up.scheme == 'redis':
        q_dict = parse_qs(up.query)
        key = q_dict.pop('key')[0]
        if up.netloc:
            url = urlunparse(up._replace(query=urlencode(q_dict)))
            f = redis_from_url(url)
        else:
            f = RedisClient().client
    if not f:
        raise ValueError('target must start with file or redis')
    
    def decr(func):

        def load_conf() -> dict:
            if isinstance(f, Path) and f.is_file():
                with closing(f.open()) as conf_file:
                    return json.load(conf_file)
            elif f.exists(key):
                return json.loads(f.get(key))
        def save_conf(data):
            if isinstance(f, Path):
                with closing(f.open('w')) as conf_file:
                    json.dump(data, conf_file)
            elif (secs := float(data.get(expire_key, 0)) - time.time()) > 0:
                f.setex(key, int(secs+1), json.dumps(data))
            else:
                f.set(key, json.dumps(data))
        def wrapper(*args, **kwargs):
            if (conf := load_conf()):
                if time.time() <= float(conf.get(expire_key, 0)) and (token := conf.get(token_key)):
                    return token
                if r_token_key and (r_token := conf.get(r_token_key)):
                    args = [*args, r_token]
            conf = func(*args, **kwargs)
            save_conf(conf)
            return conf.get(token_key)
        return wrapper
    return decr


if __name__ == '__main__':
    c = RedisClient()
    print(c.idempotent('aaa'))