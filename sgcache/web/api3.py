from ..api3.read import Api3ReadOperation
from ..exceptions import Passthrough
from .core import api3_method, cache


@api3_method
def info(req):
    return {
        's3_uploads_enabled': False,
        # 'totango_site_id': '374',
        'version': [6, 0, 3],
        # 'totango_site_name': 'com_shotgunstudio_keystone',
    }


@api3_method
def read(req):
    return Api3ReadOperation(req).run(cache)
