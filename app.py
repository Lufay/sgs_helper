import json
from flask import Flask, request

from facade import *   # add facade don't remove it
from utils.router import route_todo
from utils.redis_util import RedisClient
from common import runtime_env

app = Flask(__name__)
runtime_env['debug'] = app.config.get('DEBUG')

@app.route('/sgs/helper', methods=['GET', 'POST'])
def sgs_main():
    # print(request.args)
    if request.content_type.startswith('application/json'):
        d = request.get_json()
        ret = verify(d)
        if ret is None:
            cmd = d.pop('content', '')
            ret = {'success': True, 'message': route_todo(cmd, **d)}
        return json.dumps(ret)
    elif request.content_type.startswith('application/form-data'):
        print(request.form)
    else:
        print(request.values)


def verify(data):
    if 'challenge' in data:
        return {'challenge': data['challenge']}
    elif 'event' in data and data.get('schema') == '2.0':
        return process_event(**data['event'])
    elif 'action' in data:
        return process_action(data['open_message_id'], data['open_chat_id'], data['action'], data['token'], data['open_id'])


def process_event(sender: dict, message: dict):
    '''format sample: https://open.feishu.cn/document/server-docs/im-v1/message/events/receive
    '''
    msg_id = message['message_id']
    if RedisClient().idempotent(msg_id, 600) is None:
        return {'success': False, 'message': 'Msg id idempotent'}
    content = json.loads(message['content'])['text']
    ret = route_todo(content,
                     chat_id=message['chat_id'],
                     sender_open_id=sender['sender_id']['open_id'],
                     create_time_ms=message['create_time'])
    return {'success': True, 'message': ret}


def process_action(msg_id, chat_id, action: dict, token: str, op_open_id: str):
    cmd = action['value'].pop('cmd')
    return route_todo(cmd,
                     chat_id=chat_id,
                     token=token,
                     op_open_id=op_open_id,
                     **action['value'])


if __name__ == '__main__':
    # app.run(debug = True)
    app.run()