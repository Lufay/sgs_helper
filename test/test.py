import sys, os
import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from common import conf
from sgs import Hero
from utils.robot_adapter import robot

def test_robot(cmd):
    resp = requests.post('http://127.0.0.1:5000/sgs/hero', json={
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
    from sgs import HeroMgr
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
    hero = Hero.load(dump_dir + name + '.pickle')
    show_hero(hero)
    robot(hero)


if __name__ == '__main__':
    # test_robot('我是谁')
    # test_robot('roll master 3')
    # test_robot('roll hero')
    # test_robot('华佗 标')
    # test_robot('win 5人身份+魏延')
    # test_hero_mgr('纪灵')
    check_hero('华佗')
    # load_hero('华佗')