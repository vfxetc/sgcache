import copy
import json

from flask import request, Response, g

from ..api3.read import Api3ReadOperation
from ..exceptions import Passthrough
from .core import api3_method, cache, FALLBACK_URL, http_session


@api3_method
def info(api3_request):
    return {
        's3_uploads_enabled': False,
        # 'totango_site_id': '374',
        'version': [6, 0, 3],
        # 'totango_site_name': 'com_shotgunstudio_keystone',
        'sgcache': True,
    }


@api3_method
def read(api3_request):
    return Api3ReadOperation(api3_request).run(cache)


@api3_method
def create(api3_request):

    return_fields = api3_request['return_fields'][:]

    passthrough_payload = copy.deepcopy(g.api3_payload)
    create_params = passthrough_payload['params'][1] = copy.deepcopy(api3_request)

    # Add all fields that we cache to the return_fields.
    request_fields = create_params['return_fields'] = return_fields[:]
    entity_type = cache[api3_request['type']]
    for name, field in entity_type.fields.iteritems():
        if field.is_cached():
            request_fields.append(name)

    # Make the modified request to the real server.
    headers = dict(request.headers)
    headers.pop('Host') # Our "Host" is different.
    http_response = http_session.post(FALLBACK_URL, data=json.dumps(passthrough_payload), headers=headers)

    if http_response.status_code == 200:

        create_res_payload = json.loads(http_response.text)

        if 'exception' in create_res_payload:
            return create_res_payload

        # We don't check for results, since we want to fail very hard if
        # this doesn't have the shape we expect it to.
        created_data = create_res_payload['results']

        # Cache this new entity.
        cache.create_or_update(entity_type.type_name, created_data, create_with_id=True)

        # Reduce the returned data to that which was requested.
        return_data = {
            'type': entity_type.type_name,
            'id': created_data['id'],
        }
        for field in return_fields:
            try:
                return_data[field] = created_data[field]
            except KeyError:
                pass

        return {'results': return_data}

    else:
        # An error, or something.
        return http_response.text, http_response.status_code, [('Content-Type', 'application/json')]


@api3_method
def update(api3_request):

    # Pass through the request.
    headers = dict(request.headers)
    headers.pop('Host') # Our "Host" is different.
    http_response = http_session.post(FALLBACK_URL, data=request.data, headers=headers)

    if http_response.status_code == 200:

        res_payload = json.loads(http_response.text)

        # Cache the updates.
        cache.create_or_update(api3_request['type'], res_payload['results'], create_with_id=True)

        return res_payload

    else:
        # An error, or something.
        return http_response.text, http_response.status_code, [('Content-Type', 'application/json')]

