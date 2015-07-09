import json

from requests import Session


class SGAPIError(Exception):
    pass


class SGAPI(object):

    def __init__(self, host, script_name, script_key):

        self.host = host
        self.endpoint = host.rstrip('/') + '/api3/json'

        self.script_name = script_name
        self.script_key = script_key

        self.session = None

    def call(self, method_name, method_params=None, authenticate=True):

        if method_name == 'info' and method_params is not None:
            raise ValueError('info takes no params')
        if method_name != 'info' and method_params is None:
            raise ValueError('%s takes params' % method_name)

        if not self.session:
            self.session = Session()
        
        params = []
        request = {
            'method_name': method_name,
            'params': params,
        }

        if authenticate:
            params.append({
                'script_name': self.script_name,
                'script_key': self.script_key,
            })

        if method_params is not None:
            params.append(method_params)


        response_handle = self.session.post(self.endpoint, data=json.dumps(request), headers={
            'User-Agent': 'sgcache/0.1',
        })
        content_type = (response_handle.headers.get('Content-Type') or 'application/json').lower()
        if content_type.startswith('application/json') or content_type.startswith('text/javascript'):
            response = json.loads(response_handle.text)
            if response.get('exception'):
                raise SGAPIError(response.get('message', 'unknown error'))
            return response['results']
        else:
            return response_handle.text




if __name__ == '__main__':

    from shotgun_api3_registry import get_args
    api = SGAPI(*get_args())

