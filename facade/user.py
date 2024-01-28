from biz.user import UserMgr
# from common import conf

from utils.robot_adapter import robot
from utils.router import route, MatchType as MT

# UserMgr.load(conf['Local']['UserRcordPath'])
# atexit.register(UserMgr.dump, conf['Local']['UserRcordPath'])

@route(r'win ([^+]+)\+(.+)', MT.REGEX)
def win(cmd, ctx, *args, **kwargs):
    if sender := kwargs.get('sender'):
        user = UserMgr.get_user(sender)
        if user.add_record(*ctx[0].group(1, 2)):
            robot('已记录获胜')
            return True
        else:
            robot('记录获胜 failed')
            return False
    else:
        robot('Invalid user ' + sender)
        return False


@route('rep count', MT.FULL_MATCH)
def rep_count(cmd, ctx, *args, **kwargs):
    if sender := kwargs.get('sender'):
        user = UserMgr.get_user(sender)
        robot(user.rep_num)
        return True
    else:
        robot('Invalid user ' + sender)
        return False
    
@route('luck count', MT.FULL_MATCH)
def luck_count(cmd, ctx, *args, **kwargs):
    if sender := kwargs.get('sender'):
        user = UserMgr.get_user(sender)
        robot(user.luck_num)
        return True
    else:
        robot('Invalid user ' + sender)
        return False
    
@route('cost ', MT.PREFIX)
def cost(cmd, ctx, *args, **kwargs):
    if sender := kwargs.get('sender'):
        user = UserMgr.get_user(sender)
        match ctx[0]:
            case 'luck':
                if user.luck_num > 0:
                    user.luck_consumed += 1
                    robot('消耗一个手气卡')
                else:
                    robot('已经没有手气卡')
            case 'rep':
                if user.rep_num > 0:
                    user.rep_consumed += 1
                    robot('消耗一次换将卡')
                else:
                    robot('已经没有换将卡')
            case _:
                robot('Invalid cost cmd' + cmd)
                return True
    else:
        robot('Invalid user ' + sender)
        return False
