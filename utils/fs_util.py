import base64
from inspect import isclass
import json
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
    def raw_request(cls, method, path, **kwargs):
        headers = kwargs.setdefault('headers', {})
        headers['Authorization'] = f'Bearer {cls.access_token}'
        return method(f'{cls.host}{path}', **kwargs)

    @classmethod
    def common_request(cls, method, path, res_key=None, **kwargs):
        resp = cls.raw_request(method, path, **kwargs)
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


def send_chat_card(chat_id, card_id, **kwargs):
    return FsClient.common_request(post, '/im/v1/messages', params={
        'receive_id_type': 'chat_id'
    }, json={
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps({
            'type': 'template',
            'data': {
                'template_id': card_id,
                'template_variable': kwargs
            }
        })
    })

def send_chat_msg(chat_id, msg):
    return FsClient.common_request(post, '/im/v1/messages', params={
        'receive_id_type': 'chat_id'
    }, json={
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({
            'text': msg,
        })
    })

def get_image_stream(msg_id, image_key):
    resp = FsClient.raw_request(get, f'/im/v1/messages/{msg_id}/resources/{image_key}', params={
        'type': 'image'})
    if resp.ok:
        image_bytes = resp.content
        image_base64 = base64.b64encode(image_bytes)
        return FsClient.common_request(post, '/optical_char_recognition/v1/image/basic_recognize', 'text_list', json={
            'image': image_base64.decode('utf8'),
        })
    else:
        print(resp.text)
        resp.raise_for_status()