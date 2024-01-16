from inspect import isclass
import time
from requests import HTTPError, get, post

from common import conf
from utils import classproperty
from utils.redis_util import cache_token

class FsClient:
    host = 'https://open.feishu.cn/open-apis'

    @classproperty
    @cache_token('redis://?key=fs_token', 'tenant_access_token', 'expired_at')
    def access_token(cls):
        '''reference to https://open.feishu.cn/document/ukTMukTMukTM/uMTNz4yM1MjLzUzM
        '''
        resp = post(f'{cls.host}/auth/v3/tenant_access_token/internal', json=dict(conf['Feishu']))
        resp.raise_for_status()
        r = resp.json()
        r['expired_at'] = time.time() + r.get('expire', 1800)
        return r

    @classmethod
    def common_request(cls, method, path, res_key=None, **kwargs):
        headers = kwargs.setdefault('headers', {})
        headers['Authorization'] = f'Bearer {cls.access_token}'
        resp = method(f'{cls.host}{path}', **kwargs)
        if resp.ok:
            r = resp.json()
            if r['code'] != 0:
                raise HTTPError(r['msg'])
            r = r['data']
            if isclass(res_key):
                return res_key(**r)
            elif isinstance(res_key, str):
                return r[res_key]
            else:
                return r
        else:
            print(resp.text)
            resp.raise_for_status()