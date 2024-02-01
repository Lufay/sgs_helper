import random
from sgs.heros import hero_mgr
import common
from sgs.room import Room
from utils.fs_template.cards import simple_card
from utils.robot_adapter import robot
from utils.router import route, MatchType as MT

from sgs.events import event_err_handler

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


@route('pick_hero', MT.FULL_MATCH)
def pick(cmd, ctx, *args, **kwargs):
    room_id = kwargs.get('room_id')
    op_open_id = kwargs.get('op_open_id')
    hero_uname = kwargs['uname']
    name, _, pack = hero_uname.partition('@')
    def set_role_hero(heros):
        Room.rooms_queue[room_id].put((op_open_id, heros[0]))
    common.process_pool.apply_async(hero_mgr.search, (name, pack),
                                    callback=set_role_hero, error_callback=event_err_handler)
    return simple_card(room_id, f'你已选择{hero_uname}, 请等待其他玩家选择完毕')
    
