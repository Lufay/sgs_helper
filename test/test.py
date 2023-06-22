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


def test_hero_mgr(name):
    from sgs import HeroMgr
    mgr = HeroMgr.load(conf['Local']['MarkDownPath'])
    print(len(mgr.heros))
    print(mgr.monarchs)
    roles = mgr.search(name)
    for role in roles:
        role.crawl_by_name()
        print(role)
        if role.image:
            print(role.image.author)


if __name__ == '__main__':
    # test_robot('我是谁')
    # test_robot('roll master')
    # test_robot('roll hero 5')
    # test_robot('张宝')
    # test_robot('win 5人身份+魏延')
    test_hero_mgr('孙亮')