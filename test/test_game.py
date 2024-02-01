import time
import requests

def make_room(n):
    resp = requests.post('http://127.0.0.1:5000/sgs/helper', json={
        'schema': '2.0',
        'header': {'event_id': '5b54d27e4d164664a6daf42314b716b8', 'token': '', 'create_time': '1706240245907', 'event_type': 'im.message.receive_v1', 'tenant_key': '736588c9260f175d', 'app_id': 'cli_a4e6371b20789013'},
        'event': {
            'message': {
                'chat_id': 'oc_a7718e4eb060b73600558caff5e43511',
                'chat_type': 'group',
                'content': '{"text":"make room %d"}' % n,
                'create_time': '1706240245327',
                'message_id': f'om_{time.time()}',
                'message_type': 'text', 'update_time': '1706240245327'
            },
        'sender': {
            'sender_id': {
                'open_id': 'ou_90ee536d2787207251490ab874d22e25',
                'union_id': 'on_6367d9fa57b5fd7ae84425dee89bdf27',
                'user_id': '88db4be5'
            },
            'sender_type': 'user',
            'tenant_key': '736588c9260f175d'}}})
    resp.raise_for_status()
    ret = resp.json()
    if ret['success']:
        return ret['message']
    else:
        print('make room failed\n', ret['message'])


def get_role(room_id, i):
    resp = requests.post('http://127.0.0.1:5000/sgs/helper', json={
        'app_id': 'cli_a4e6371b20789013',
        'open_id': f'test-{i}',
        'user_id': '88db4be5',
        'open_message_id': f'om_{time.time()}',
        'open_chat_id': 'oc_a7718e4eb060b73600558caff5e43511',
        'tenant_key': '736588c9260f175d', 'token': '',
        'action': {
            'value': {
                'cmd': 'get_role',
                'room_id': room_id
            }, 'tag': 'button'}})
    resp.raise_for_status()
    ret = resp.json()
    print(ret)


def pick_hero(room_id, i):
    resp = requests.post('http://127.0.0.1:5000/sgs/helper', json={
        'app_id': 'cli_a4e6371b20789013',
        'open_id': f'test-{i}',
        'user_id': '88db4be5',
        'open_message_id': f'om_{time.time()}',
        'open_chat_id': 'oc_4113799c9c7fc622413d96654e3ddf6a',
        'tenant_key': '736588c9260f175d', 'token': '',
        'action': {
            'value': {
                'cmd': 'pick_hero',
                'room_id': room_id,
                'uname': '许褚@标准版'
            }, 'tag': 'button'}})
    resp.raise_for_status()
    ret = resp.json()
    print(ret)

def mock_user(n):
    room_id = make_room(n)
    if room_id is None:
        return
    for i in range(1, n):
        get_role(room_id, i)
    input('room done?')
    for i in range(1, n):
        pick_hero(room_id, i)


if __name__ == '__main__':
    mock_user(5)