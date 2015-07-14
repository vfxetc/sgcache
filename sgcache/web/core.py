import json
import logging
import os
import time

import requests
from flask import Flask, request, Response
import sqlalchemy as sa
import yaml

from shotgun_api3_registry import get_args as get_sg_args

from ..schema.core import Schema
from ..exceptions import Passthrough
from ..eventlog import EventLog
from ..logs import setup_logs, log_globals

log = logging.getLogger(__name__)


app = Flask(__name__)
app.config.from_object('sgcache.config')

db = sa.create_engine(app.config['SQLA_URL'], echo=app.config['SQLA_ECHO'])

# Setup logging *after* SQLA so that it can deal with its handlers.
setup_logs(app)

schema_spec = yaml.load(open(app.config['SCHEMA']).read())
schema = Schema(db, schema_spec) # SQL DDL is executed here; watch out!

# Get the fallback server from shotgun_api3_registry.
FALLBACK_SERVER, _, _ = get_sg_args()
FALLBACK_URL = FALLBACK_SERVER.strip('/') + '/api3/json'

# We use one HTTP session for everything.
http_session = requests.Session()


@app.route('/api3/json', methods=['POST'])
@app.route('/<path:params>/api3/json', methods=['POST'])
def json_api(params=None):

    # TODO: pull server URL from params

    payload = json.loads(request.data)

    if not isinstance(payload, dict):
        return '', 400, []

    #print json.dumps(payload, sort_keys=True, indent=4)

    try:
        method_name = payload['method_name']
    except KeyError:
        return '', 400, []

    try:
        method = _api_methods[method_name]
    except KeyError as e:
        return passthrough('unknown API method %s' % method_name)

    try:
        method_params = payload['params'][1] if len(payload['params']) > 1 else {}
        start_time = time.time()
        res = method(method_params)
    except Passthrough as pt:
        return passthrough(pt)
    else:
        elapsed_ms = 1000 * (time.time() - start_time)
        log.info('API %s %s returned %sin %.1fms' % (
            method_name,
            method_params.get('type'),
            '%s entities ' % len(res['entities']) if 'entities' in res else '',
            elapsed_ms
        ))
        log_globals.skip_http_log = True

    res = json.dumps(res)
    return res, 200, [('Content-Type', 'application/json')]


def passthrough(e=None):

    if e:
        if isinstance(e, Exception):
            log.info('Passing through request (%s): %s' % (e.__class__.__name__, e))
        else:
            log.info('Passing through request: %s' % e)
    else:
        log.info('Passing through request')

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



# Register api methods
_api_methods = {}
def api_method(func):
    _api_methods[func.__name__] = func
    return func
from . import api
