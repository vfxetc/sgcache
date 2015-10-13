from ..api3.read import Api3ReadOperation
from ..exceptions import Passthrough
from .core import api3_method, cache, passthrough


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

    params = api3_request.copy()

    # Add all fields that we cache to the return_fields.
    request_fields = params['return_fields'] = return_fields[:]
    entity_type = cache[api3_request['type']]
    for name, field in entity_type.fields.iteritems():
        if field.is_cached():
            request_fields.append(name)

    # Make the modified request.
    response = passthrough(params=params)

    # Fail very hard if "results" doesn't exist since we want to know if the schema changes).
    created_data = response['results']
    cacheable_data = cache.filter_cacheable_data(created_data)

    # Cache this new entity.
    if cacheable_data:
        cache.create_or_update(entity_type.type_name, cacheable_data, create_with_id=True)

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


@api3_method
def update(api3_request):

    response = passthrough()

    # Fail very hard if "results" doesn't exist since we want to know if the schema changes).
    updated_data = response['results']
    cacheable_data = cache.filter_cacheable_data(updated_data)

    # Cache the updates
    if cacheable_data:
        cache.create_or_update(api3_request['type'], cacheable_data, create_with_id=True)

    return response


@api3_method
def delete(api3_request):
    response = passthrough()
    cache.retire(api3_request['type'], api3_request['id'], strict=False)
    return response


@api3_method
def revive(api3_request):
    response = passthrough()
    cache.revive(api3_request['type'], api3_request['id'], strict=False)
    return response


