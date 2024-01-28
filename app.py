import json
import logging
from multiprocessing import Pool, cpu_count, Manager
from flask import Flask, request

from facade import *   # add facade don't remove it
from utils.router import route_todo
from utils.redis_util import RedisClient
import common
from common import runtime_env, conf
from biz.user import user_mgr_ctx

app = Flask(__name__)
runtime_env['debug'] = app.config.get('DEBUG')

@app.route('/sgs/helper', methods=['GET', 'POST'])
def sgs_main():
    # print(request.args)
    if request.content_type.startswith('application/json'):
        logger = logging.getLogger('request')
        data = request.get_json()
        logger.debug('request: %s' % data)
        if 'challenge' in data:
            ret = {'challenge': data['challenge']}
        elif 'event' in data and data.get('schema') == '2.0':
            ret = process_event(**data['event'])
        elif 'action' in data:
            ret = process_action(data['open_message_id'], data['open_chat_id'], data['action'], data['token'], data['open_id'])
        elif 'content' in data:
            cmd = data.pop('content', '')
            ret = {'success': True, 'message': route_todo(cmd, **data)}
        else:
            ret = {'success': False, 'message': f'unknown data.\n{data}'}
        return json.dumps(ret)
    elif request.content_type.startswith('application/form-data'):
        print(request.form)
    else:
        print(request.values)


def process_event(sender: dict, message: dict):
    '''飞书应用消息
    format sample: https://open.feishu.cn/document/server-docs/im-v1/message/events/receive
    '''
    msg_id = message['message_id']
    if RedisClient().idempotent(msg_id, 600) is None:
        return {'success': False, 'message': 'Msg id idempotent'}
    content = json.loads(message['content'])
    if 'text' in content:
        ret = route_todo(content['text'],
                        chat_id=message['chat_id'],
                        sender_open_id=sender['sender_id']['open_id'],
                        create_time_ms=message['create_time'])
    elif 'image_key' in content:
        ret = route_todo('get image text',
                         chat_id=message['chat_id'],
                         sender_open_id=sender['sender_id']['open_id'],
                         create_time_ms=message['create_time'],
                         msg_id=msg_id,
                         image_key=content['image_key'])
    elif 'content' in content:
        ...
    return {'success': True, 'message': ret}


def process_action(msg_id, chat_id, action: dict, token: str, op_open_id: str):
    '''飞书卡片回调
    '''
    cmd = action['value'].pop('cmd')
    return route_todo(cmd,
                     chat_id=chat_id,
                     token=token,
                     op_open_id=op_open_id,
                     **action['value'])


if __name__ == '__main__':
    print('CPU count:', cpu_count())
    with (Manager() as manager,
          Pool() as pool,
          user_mgr_ctx(conf['Local']['UserRcordPath'])):
        common.manager = manager
        common.process_pool = pool
        # app.run(debug = True)
        app.run()