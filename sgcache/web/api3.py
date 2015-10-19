from inspect import isgeneratorfunction
from types import GeneratorType
import json
import sys

from ..api3.read import Api3ReadOperation
from ..exceptions import Passthrough
from .core import _api3_methods, api3_method, cache, passthrough


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
def batch(api3_requests):

    # Collect generators and parameters for them. If everything is a generator,
    # then we can continue. In generally, we already know that all batchable
    # methods are implemented here as generators, but lets be safe anyways.
    generators = []
    for req in api3_requests:
        # Remove the request_type since it is not expected.
        req = req.copy()
        req_type = req.pop('request_type', None)
        func = _api3_methods.get(req_type)
        if not func:
            raise Passthrough('unknown api3 method in batch mode: %s' % req_type)
        if not isgeneratorfunction(func):
            raise Passthrough('api3 method %s is not a generator' % req_type)
        generators.append((func, req_type, req))

    # Allow each method to mutate the request before it is passed-through.
    pt_payload = []
    coroutines = []
    for func, req_type, params in generators:
        iter_ = func(params)
        coroutines.append(iter_)
        pt_params = next(iter_) or params
        pt_params['request_type'] = req_type
        pt_payload.append(pt_params)

    # Do the batch.
    try:
        pt_results = passthrough(params=pt_payload)
    except Exception as e:
        # Feed the exception through all coroutines so that they clean up.
        exc_info = sys.exc_info()
        for iter_ in coroutines:
            try:
                iter_.throw(*exc_info)
            except StopIteration:
                pass
            except Exception as e2:
                if e is not e2:
                    raise
        raise exc_info[0], exc_info[1], exc_info[2]

    # Allow each method to update the cache, mutate the response, etc..
    final_results = []
    for i, iter_ in enumerate(coroutines):

        # The "results" key is at the top-level of the batch request, so
        # we need to modify it when we split it up to look like lots of
        # individual requests.
        pt_result = {'results': pt_results['results'][i]}

        # Get the method's results.
        result = iter_.send(pt_result) or pt_result

        # Make sure there is nothing else.
        for x in iter_:
            log.warning('Extra yielded from generator method: %r' % x)

        # Strip any new "results" wrapper.
        result = result.get('results', result)

        final_results.append(result)

    return final_results


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
    response = yield params

    # Fail very hard if "results" doesn't exist since we want to know if the schema changes).
    created_data = response['results']
    cacheable_data = cache.filter_cacheable_data(created_data)

    # Cache this new entity.
    if cacheable_data:
        cache.create_or_update(entity_type.type_name, cacheable_data, create_with_id=True)

    # Reduce the returned data...
    return_data = {
        'type': entity_type.type_name,
        'id': created_data['id'],
    }
    # ... to that which was specified in the creation...
    for data_spec in api3_request['fields']:
        field = data_spec['field_name']
        try:
            return_data[field] = created_data[field]
        except KeyError:
            # Should never get here; everything passed in should have been
            # returned to us.
            pass
    # ... and additionally what was explicitly requested.
    for field in return_fields:
        try:
            return_data[field] = created_data[field]
        except KeyError:
            pass


    yield {'results': return_data}


@api3_method
def update(api3_request):

    response = yield

    # Fail very hard if "results" doesn't exist since we want to know if the schema changes).
    updated_data = response['results']
    cacheable_data = cache.filter_cacheable_data(updated_data)

    # Cache the updates
    if cacheable_data:
        cache.create_or_update(api3_request['type'], cacheable_data, create_with_id=True)

    yield response


@api3_method
def delete(api3_request):
    response = yield
    cache.retire(api3_request['type'], api3_request['id'], strict=False)
    yield response


@api3_method
def revive(api3_request):
    response = yield
    cache.revive(api3_request['type'], api3_request['id'], strict=False)
    yield response


