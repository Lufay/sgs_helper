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


def mock_test(func):
    return lambda *args, **kwargs: 'mock send to test' if args[0].startswith('test-') else func(*args, **kwargs)

@mock_test
def send_card(receive_id, card_id_or_cont, id_type='chat_id', **kwargs):
    if isinstance(card_id_or_cont, str):
        card_id_or_cont = {
            'type': 'template',
            'data': {
                'template_id': card_id_or_cont,
                'template_variable': kwargs
            }
        }
    return FsClient.common_request(post, '/im/v1/messages', params={
        'receive_id_type': id_type
    }, json={
        "receive_id": receive_id,
        "msg_type": "interactive",
        "content": json.dumps(card_id_or_cont)
    })

@mock_test
def send_msg(receive_id, msg, id_type='chat_id'):
    return FsClient.common_request(post, '/im/v1/messages', params={
        'receive_id_type': id_type
    }, json={
        "receive_id": receive_id,
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

def get_doc_block(doc_id, block_id):
    return FsClient.common_request(get, f'/docx/v1/documents/{doc_id}/blocks/{block_id}', 'block')

def get_doc_table(doc_id, table_block_id):
    '''去除表格左上角的一个单元格
    第一行为表头, 第一列为行标
    表头为空, 或者行标为空均不收录, 返回一个二维字典
    '''
    block = get_doc_block(doc_id, table_block_id)
    assert block['block_type'] == 31
    table = block['table']
    cells = table['cells']
    column_size = table['property']['column_size']
    # row_size = table['property']['row_size']
    table_dict = {}
    headers = ['']
    for i, cell in enumerate(cells[1:]):
        block = get_doc_block(doc_id, cell)
        block_c = get_doc_block(doc_id, block['children'][0])
        conts = block_c['text']['elements']
        cont = ''.join(e['text_run']['content'] for e in conts)
        column = (i+1) % column_size
        row = (i+1) // column_size
        if row == 0:
            if cont:
                table_dict[cont] = {}
            headers.append(cont)
        elif column == 0:
            col_key = cont
        elif col_name := headers[column]:
            table_dict[col_name][col_key] = cont
    return table_dict
            
if __name__ == '__main__':
    td = get_doc_table('QcTidCaTTovc9zxt2pkl7mFng4c', 'I2GTdMPlIoHcmpxomT0lgu5Igkb')
    print(td)