import json
import sys, os
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


def test_components():
    from utils.fs_template.cards import pick_hero_card
    print(json.dumps(pick_hero_card('111', 3, ['a', 'bb', 'ccc', 'dddd', 'eeeee'])))


if __name__ == '__main__':
    # test_robot('我是谁')
    # test_robot('roll master 3')
    # test_robot('roll hero 3')
    # test_robot('华佗 标')
    # test_robot('win 5人身份+魏延')
    # check_hero('纪灵')
    # load_hero('嵇康')
    # test_card()
    test_components()

