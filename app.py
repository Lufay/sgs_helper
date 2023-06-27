import json
from flask import Flask, request

import facade   # add facade don't remove it
from utils.router import route_todo
from common import runtime_env

app = Flask(__name__)
runtime_env['debug'] = app.config.get('DEBUG')

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


if __name__ == '__main__':
    # app.run(debug = True)
    app.run()