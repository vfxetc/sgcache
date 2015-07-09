import json
import logging
import os
import threading

import requests
from flask import Flask, request, Response
import sqlalchemy as sa
import yaml

from ..schema.core import Schema
from ..exceptions import Passthrough
from ..eventlog import EventLog

log = logging.getLogger(__name__)
app = Flask(__name__)

app.config['SQLA_URL'] = 'sqlite://'
app.config['SGCACHE_SCHEMA'] = 'schema/keystone-basic.yml'
for k, v in os.environ.iteritems():
    if k.startswith('SGCACHE_'):
        app.config[k[8:]] = v

#db = sa.create_engine('postgresql://127.0.0.1/sgcache', echo=True)
db = sa.create_engine(app.config['SQLA_URL'], echo=True)

schema_spec = yaml.load(open('schema/keystone-basic.yml').read())
schema = Schema(db, schema_spec) # the schema is created here; watch out!

events = EventLog(schema)

event_watcher = threading.Thread(target=events.watch)
event_watcher.daemon = True
event_watcher.start()






FALLBACK_SERVER = 'https://keystone.shotgunstudio.com'
FALLBACK_URL = FALLBACK_SERVER + '/api3/json'

http_session = requests.Session()


@app.route('/api3/json', methods=['POST'])
@app.route('/<path:params>/api3/json', methods=['POST'])
def json_api(params=None):

    # TODO: pull server URL from params

    payload = json.loads(request.data)

    if not isinstance(payload, dict):
        return '', 400, []

    print json.dumps(payload, sort_keys=True, indent=4)

    try:
        method_name = payload['method_name']
    except KeyError:
        return '', 400, []

    try:
        method = _api_methods[method_name]
    except KeyError as e:
        return passthrough()

    try:
        res = method(payload['params'][1] if len(payload['params']) > 1 else {})
    except Passthrough as pt:
        return passthrough(pt)

    res = json.dumps(res)
    return res, 200, [('Content-Type', 'application/json')]


def passthrough(e=None):

    if e:
        if isinstance(e, Exception):
            log.info('passthrough request (%s): %s' % (e.__class__.__name__, e))
        else:
            log.info('passthrough request: %s' % e)
    else:
        log.info('passthrough request')

    # our "Host" is different than theirs
    headers = dict(request.headers)
    headers.pop('Host')

    res = http_session.post(FALLBACK_URL, data=request.data, headers=headers, stream=True)

    if res.status_code == 200:
        return Response(_process_passthrough_response(res), mimetype='application/json')
    else:
        return res.text, res.status_code, [('Content-Type', 'application/json')]


def _process_passthrough_response(res):

    buffer_ = []
    for chunk in res.iter_content(512):
        yield chunk
        buffer_.append(chunk)

    # TODO: analyze it here



# register api methods

_api_methods = {}
def api_method(func):
    _api_methods[func.__name__] = func
    return func

from . import api
