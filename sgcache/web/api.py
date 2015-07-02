from .core import api_method, Passthrough


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

    raise Passthrough()
    
    entity_type = req['type']
    paging = req['paging']
    page = paging['current_page']
    per_page = paging['entities_per_page']


    entities = [{'type': entity_type, 'id': 1234}]

    return {
        'entities': entities,
        'paging_info': {
            'entity_count': len(entities),
        }
    }
