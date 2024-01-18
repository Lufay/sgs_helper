import json
import random
import time

from biz.room import Room
from utils.fs_util import send_chat_card
from utils.router import route, MatchType as MT


@route('make room(\d)? (\d)', MT.REGEX)
def make_room(cmd, ctx, *args, **kwargs):
    ma = ctx[0]
    user_cnt = int(ma.group(2))
    if user_cnt < 5 or user_cnt > 10:
        raise ValueError('人数限于5-10人之间')
    cnt = ma.group(1)
    room = Room(f'{time.time()}{random.random()}', user_cnt, int(cnt) if cnt else 1)
    if (cached_cnt := room.cache()) != user_cnt:
        print('cache room', room.room_id, ' size:', cached_cnt)
        return
    res = send_chat_card(kwargs.get('chat_id'), 'ctp_AAy5FDrz9DNP', room.room_id)
    print(res)


@route('get_role', MT.FULL_MATCH)
def get_role(cmd, ctx, *args, **kwargs):
    room_id = kwargs.get('room_id')
    op_open_id = kwargs.get('op_open_id')
    room = Room(room_id)
    return {
        "elements": [
        # {
        #     "tag": "markdown",
        #     "content": "This is a blank card content."
        # },
        {
            "tag": "div",
            "text": {
                "content": room.pop_role(op_open_id).value,
                "tag": "plain_text"
            }
        }
    ]}