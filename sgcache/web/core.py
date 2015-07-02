import json
import logging

import requests
from flask import Flask, request


log = logging.getLogger(__name__)
app = Flask(__name__)


_api_methods = {}
def api_method(func):
    _api_methods[func.__name__] = func
    return func

class Passthrough(Exception):
    pass

# register api methods
from . import api


FALLBACK_SERVER = 'https://keystone.shotgunstudio.com'
FALLBACK_URL = FALLBACK_SERVER + '/api3/json'

http_session = requests.Session()


@app.route('/api3/json', methods=['POST'])
@app.route('/<path:params>/api3/json', methods=['POST'])
def json_api(params=None):

    # TODO: pull server URL from params

    encoded_payload = request.data
    payload = json.loads(encoded_payload)

    if not isinstance(payload, dict):
        return '', 400, []

    print encoded_payload

    try:
        method_name = payload['method_name']
    except KeyError:
        return '', 400, []

    try:
        
        try:
            method = _api_methods[method_name]
        except KeyError as e:
            raise Passthrough('unknown API method %s' % e.args[0])

        res = method(payload['params'][1] if len(payload['params']) > 1 else {})
        res = json.dumps(res)
        return res, 200, [('Content-Type', 'application/json')]

    except Passthrough as pt:

        log.info('passthrough request')

        # our "Host" is different than theirs
        headers = dict(request.headers)
        headers.pop('Host')

        res = http_session.post(FALLBACK_URL, data=encoded_payload, headers=headers)
        # we don't need to go as efficient as possible returning the un-decoded
        # body since we intend to inspect it anyways to update our own information
        # TODO: return a generator that buffers the response via res.iter_content(),
        # and updates our data-stores at the end
        return res.text, res.status_code, [('Content-Type', 'application/json')]




