from utils.router import route, MatchType as MT
from utils.robot_adapter import robot

@route('我是谁', MT.KEYWORD)
def whoami(content, ctx, *args, **kwargs):
    sender = kwargs.get('sender')
    if sender:
        robot(sender)
    else:
        robot('我不知道')
    return sender