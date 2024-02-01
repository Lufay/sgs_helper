import random
from utils.router import route, MatchType as MT
from utils.robot_adapter import robot
from utils.fs_util import send_msg, get_image_stream

@route('我是谁', MT.KEYWORD)
def whoami(content, ctx, *args, **kwargs):
    sender = kwargs.get('sender')
    if sender:
        robot(sender)
    else:
        robot('我不知道')
    return sender


@route('roll (\d+)', MT.REGEX)
def roll(cmd, ctx, *args, **kwargs):
    n = random.randint(1, int(ctx[0].group(1)))
    return send_msg(kwargs.get('chat_id'), str(n))


@route('get image text', MT.FULL_MATCH)
def get_image_text(cmd, ctx, *args, **kwargs):
    texts = get_image_stream(kwargs['msg_id'], kwargs['image_key'])
    return send_msg(kwargs.get('chat_id'), '\n'.join(texts))