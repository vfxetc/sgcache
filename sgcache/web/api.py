from ..exceptions import Passthrough
from .core import api_method, schema, db
from ..apimethods.read import ReadHandler


@api_method
def info(req):
    return {
        's3_uploads_enabled': False,
        # 'totango_site_id': '374',
        'version': [6, 0, 3],
        # 'totango_site_name': 'com_shotgunstudio_keystone',
    }


@api_method
def read(req):

    handler = ReadHandler(req)
    entities = handler(schema)

    return {
        'entities': entities,
        'paging_info': {
            'entity_count': len(entities),
        }
    }
