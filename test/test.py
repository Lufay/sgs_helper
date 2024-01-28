import sys, os
import time
import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from common import conf
from sgs.heros import Hero
from utils.robot_adapter import robot

def test_robot(cmd):
    resp = requests.post('http://127.0.0.1:5000/sgs/helper', json={
        'content': cmd,
        'sender': 'tester',
    })
    resp.raise_for_status()
    print(resp.text)


def show_hero(hero: Hero):
    print(hero)
    for c in hero.contents:
        print(c.md_format(line_break='\n'))
    if hero.image:
        print(hero.image.author)


def check_hero(name=None):
    from sgs.heros import HeroMgr
    mgr = HeroMgr.load(conf['Local']['MarkDownPath'])
    dump_dir = conf['Local']['HeroDumpPath']
    print('Total:', len(mgr.heros))
    print(mgr.monarchs)
    if name:
        heros = mgr.search(*name.split())
    else:
        heros = mgr.heros
    for hero in heros:
        if not os.path.isfile(dump_dir + hero.uni_name + '.pickle'):
            show_hero(hero.crawl_by_name())     # 测试幂等
            robot(hero)
            if input('dump (y/n)?') == 'y':
                hero.dump(dump_dir)
   

def load_hero(name):
    dump_dir = conf['Local']['HeroDumpPath']
    for hero in Hero.load(dump_dir, name):
        show_hero(hero)
        robot(hero)


def test_card():
    from sgs.cards.region import CardHeap
    ch = CardHeap()
    print(list(ch.pop(4)))


def test_game(n):
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
        room_id = ret['message']
    else:
        print('make room failed\n', ret['message'])
    for i in range(1, n):
        resp = requests.post('http://127.0.0.1:5000/sgs/helper', json={
            'app_id': 'cli_a4e6371b20789013',
            'open_id': f'ou_90ee536d2787207251490ab874d22e-{i}',
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


if __name__ == '__main__':
    # test_robot('我是谁')
    # test_robot('roll master 3')
    # test_robot('roll hero 3')
    # test_robot('华佗 标')
    # test_robot('win 5人身份+魏延')
    # check_hero('纪灵')
    # load_hero('嵇康')
    # test_card()
    test_game(5)

