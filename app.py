import base64
import hashlib
import hmac
import json
import random
import time
from flask import Flask, request
import requests

from common import conf
from utils.router import route, route_todo, MatchType as MT

app = Flask(__name__)

from sgs import HeroMgr, Hero
hero_mgr = HeroMgr.load(conf['Local']['MarkDownPath'])

@route('我是谁', MT.KEYWORD)
def whoami(content, sender='unknown'):
    if sender == 'unknown':
        robot('我不知道')
    else:
        robot(sender)
    return sender


@route('roll master', MT.PREFIX)
def rollmaster(content, sender=None):
    try:
        n = int(content)
    except ValueError:
        n = 2
    robot(', '.join(random.sample(hero_mgr.monarchs, n)), sender)
    return n


@route('roll hero', MT.PREFIX)
def rollhero(content, sender=None):
    try:
        n = int(content)
        robot(', '.join(random.sample(hero_mgr.all_heros, n)), sender)
        return n
    except ValueError:
        robot(random.choice(hero_mgr.heros).crawl_by_name(), sender)
        return 1
    
@route(lambda cmd: (len(cs := cmd.split(' ')) < 3, cs), MT.TEST)
def search_hero(cmd, ctx):
    for hero in hero_mgr.search(*ctx[0]):
        robot(hero)
    return ctx[0][0]

@app.route('/sgs/hero', methods=['GET', 'POST'])
def hero_main():
    # print(request.args)
    if request.content_type.startswith('application/json'):
        d = request.get_json()
    elif request.content_type.startswith('application/form-data'):
        print(request.form)
    else:
        print(request.values)
    cmd = d.pop('content', '')
    ret = route_todo(cmd, **d)
    return json.dumps({'success': True, 'message': ret})


def get_content_dict(content, at):
    if isinstance(content, str):
        at_str = f'<at user_id="">{at}</at> ' if at else ''
        return {
            'msg_type': 'text',
            'content': {
                'text': at_str + content
            }
        }
    elif isinstance(content, Hero):
        hp = f' {content.hp}/{content.hp_max}' if content.hp else ''
        conts = []
        if at:
            conts.append(f'<at id="">{at}</at>')
        conts.extend([
            f'性别: {content.gender}',
            f'势力: {content.camp.zn_name}',
            f'定位: {content.position}',
            f'技能:  \n {content.skill_str}',
            '***',
            *content.contents,
            '***',
            f'台词:  \n {content.lines_str}',
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
    timestamp = int(time.time())
    sign = f'{timestamp}\n{conf["ChatRobot"]["Token"]}'
    hmac_code = hmac.new(sign.encode("utf-8"), digestmod=hashlib.sha256).digest()

    cont_dict = get_content_dict(content, at)
    cont_dict.update({
        'timestamp': str(timestamp),
        'sign': base64.b64encode(hmac_code).decode('utf-8')})
    resp = requests.post(conf['ChatRobot']['HookUrl'], json=cont_dict)
    if resp.ok:
        print(resp.json())
    else:
        print(resp.text)


if __name__ == '__main__':
   app.run(debug = True)