import random
from sgs.heros import HeroMgr
from common import conf

from utils.robot_adapter import robot
from utils.router import route, MatchType as MT

hero_mgr = HeroMgr.load(conf['Local']['MarkDownPath'])

@route('roll master', MT.PREFIX)
def rollmaster(content, ctx, *args, **kwargs):
    try:
        n = int(ctx[0])
    except ValueError:
        n = 2
    robot(', '.join(random.sample(hero_mgr.monarchs, n)), kwargs.get('sender'))
    return n


@route('roll hero', MT.PREFIX)
def rollhero(content, ctx, *args, **kwargs):
    sender = kwargs.get('sender')
    try:
        n = int(ctx[0])
        robot(', '.join(random.sample(hero_mgr.all_heros, n)), sender)
        return n
    except ValueError:
        robot(random.choice(hero_mgr.heros).crawl_by_name(), sender)
        return 1


@route(lambda cmd, *a, **kv: (len(cs := cmd.split(' ')) < 3, cs), MT.TEST)
def search_hero(cmd, ctx, *a, **kv):
    for hero in hero_mgr.search(*ctx[0]):
        robot(hero)
    return ctx[0][0]
