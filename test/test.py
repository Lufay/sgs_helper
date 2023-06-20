from configparser import ConfigParser
import sys, os
import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from common import conf

def test_robot(cmd):
    resp = requests.post('http://127.0.0.1:5000/sgs/hero', json={
        'content': cmd,
        'sender': 'tester',
    })
    resp.raise_for_status()
    print(resp.text)


def test_hero_mgr():
    from sgs import HeroMgr
    mgr = HeroMgr.load(conf['Local']['MarkDownPath'])
    print(len(mgr.heros))
    print(mgr.monarchs)
    roles = mgr.search('刘备')
    roles[0].crawl_by_name()
    print(roles, roles[0].image.author)


if __name__ == '__main__':
    # test_robot('我是谁')
    # test_robot('roll master')
    # test_robot('roll hero 3')
    test_robot('关羽')
    # test_hero_mgr()