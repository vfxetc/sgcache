import json
from wsgiref.simple_server import make_server


def app(environ, start_response):

    for x in 'REQUEST_METHOD', 'PATH_INFO', 'QUERY_STRING':
        print '%s = %r' % (x, environ[x])

    if environ['REQUEST_METHOD'] == 'CONNECT':
        start_response('200 OK', [])
        return ['']

    if environ['PATH_INFO'] == '/api3/json':
        return api3_entrypoint(environ, start_response)
    start_response('404 NOT FOUND', [])
    return ['']

methods = {}
def method(func):
    methods[func.__name__] = func
    return func

def api3_entrypoint(environ, start_response):

    encoded_request = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))
    request = json.loads(encoded_request)
    print json.dumps(request, sort_keys=True, indent=4)

    method_name = request['method_name']
    method = methods.get(method_name)
    if not method:
        start_response('400 Not Found', [])
        return  ['']

    res = method(request['params'][1] if len(request['params']) > 1 else {})

    start_response('200 OK', [])
    return [json.dumps(res)]

@method
def info(req):
    return {
        's3_uploads_enabled': False,
        # 'totango_site_id': '374',
        'version': [6, 0, 2],
        # 'totango_site_name': 'com_shotgunstudio_keystone',
    }

@method
def read(req):
    return {
        'entities': [{
            'type': req['type'],
            'id': 1234
        }],
        'paging_info': {
            'entity_count': 1,
        }
    }


if __name__ == '__main__':
    server = make_server('', 8000, app)
    server.serve_forever()
