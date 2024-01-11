import json
from flask import Flask, request

from facade import *   # add facade don't remove it
from utils.router import route_todo
from common import runtime_env

app = Flask(__name__)
runtime_env['debug'] = app.config.get('DEBUG')

@app.route('/sgs/helper', methods=['GET', 'POST'])
def sgs_main():
    # print(request.args)
    if request.content_type.startswith('application/json'):
        d = request.get_json()
        ret = verify(d)
        if ret is None:
            cmd = d.pop('content', '')
            ret = {'success': True, 'message': route_todo(cmd, **d)}
        return json.dumps(ret)
    elif request.content_type.startswith('application/form-data'):
        print(request.form)
    else:
        print(request.values)


def verify(data):
    if 'challenge' in data:
        return {'challenge': data['challenge']}


if __name__ == '__main__':
    # app.run(debug = True)
    app.run()