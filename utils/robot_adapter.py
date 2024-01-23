import base64
import hashlib
import hmac
from itertools import chain, repeat
import time

import requests
from common import conf, runtime_env
from sgs.heros.hero import Hero


def get_content_dict(content, at):
    '''识别content 类型构造符合robot json格式的message
    '''
    if isinstance(content, (int, float, str)):
        at_str = f'<at user_id="">{at}</at> ' if at else ''
        return {
            'msg_type': 'text',
            'content': {
                'text': f'{at_str}{content}'
            }
        }
    elif isinstance(content, Hero):
        hp = f' {content.hp}/{content.hp_max}' if content.hp or content.hp_max else ''
        conts = []
        if at:
            conts.append(f'<at id="">{at}</at>')
        conts.extend([
            f'性别: {content.gender}',
            f'势力: {content.camp.value}',
            f'定位: {content.position}',
            '技能: ', *chain(*zip(filter(None, content.skills), repeat('***'))),
            *(c.md_format(line_break='\n') for c in content.contents),
            '台词: ', *chain(*zip(repeat('***'), filter(None, content.lines))),
        ])
        return {
            'msg_type': 'interactive',
            'card': {
                'header': {
                    'title': {
                        'content': f'{content.pack} {content.name}{hp} {content.title}',
                        'tag': "plain_text"
                    }
                },
                'elements': [{'tag': 'hr'} if cont == '***' else
                    {
                        'tag': 'div',
                        'text': {
                            'tag': 'lark_md',
                            'content': cont
                        }
                    } for cont in conts
                ]
            }
        }


def robot(content, at=None):
    conf_section = conf["ChatRobot.debug"] if runtime_env.get('debug', True) else conf['ChatRobot']
    timestamp = int(time.time())
    sign = f'{timestamp}\n{conf_section["Token"]}'
    hmac_code = hmac.new(sign.encode("utf-8"), digestmod=hashlib.sha256).digest()

    cont_dict = get_content_dict(content, at)
    cont_dict.update({
        'timestamp': str(timestamp),
        'sign': base64.b64encode(hmac_code).decode('utf-8')})
    resp = requests.post(conf_section['HookUrl'], json=cont_dict)
    if resp.ok:
        print(resp.json())
    else:
        print(resp.text)