from .core import api_method, Passthrough, schema, db


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

    # raise Passthrough()

    entity_type = req['type']
    paging = req['paging']
    page = paging['current_page']
    per_page = paging['entities_per_page']

    entity_cls = schema[entity_type]

    # make sure we have everything
    # TODO: also look in filters
    fields_used = {entity_type: list(req['return_fields'])}
    for used_type_name, used_field_names in fields_used.iteritems():
        try:
            used_type_cls = schema[used_type_name]
        except KeyError:
            raise Passthrough('unknown entity type %s' % used_type_name)
        try:
            used_fields = [used_type_cls[x] for x in used_field_names]
        except KeyError as e:
            raise Passthrough('unknown field %s.%s' % (used_type_name, e.args[0]))

    # make up an entity
    # TODO: actually query the database
    entities = [{'type': entity_type, 'id': 1234}]

    return {
        'entities': entities,
        'paging_info': {
            'entity_count': len(entities),
        }
    }
