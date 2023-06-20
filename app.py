import base64
import hashlib
import hmac
import json
import random
import time
from flask import Flask, request
import requests

from common import conf

app = Flask(__name__)

from sgs import HeroMgr, Hero
hero_mgr = HeroMgr.load(conf['Local']['MarkDownPath'])


@app.route('/sgs/hero', methods=['GET', 'POST'])
def hero_main():
    # print(request.args)
    if request.content_type.startswith('application/json'):
        d = request.get_json()
    elif request.content_type.startswith('application/form-data'):
        print(request.form)
    else:
        print(request.values)
    cmd = d.get('content', '')
    if '我是谁' in cmd:
        ret = d.get('sender', 'unknown')
        if ret == 'unknown':
            robot('我不知道')
        else:
            robot(ret)
    elif cmd.startswith(ret := 'roll master'):
        try:
            n = int(cmd.removeprefix(ret))
        except ValueError:
            n = 2
        robot(', '.join(random.sample(hero_mgr.monarchs, n)), d.get('sender', None))
    elif cmd.startswith(ret := 'roll hero'):
        try:
            n = int(cmd.removeprefix(ret))
            robot(', '.join(random.sample(hero_mgr.all_heros, n)), d.get('sender', None))
        except ValueError:
            robot(random.choice(hero_mgr.heros), d.get('sender', None))
    elif len(cs := cmd.split(' ')) < 3:
        ret = 'heros'
        for hero in hero_mgr.search(*cs):
            robot(hero)
    else:
        ret = 'note'
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
            *content.contents,
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
                'elements': [
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