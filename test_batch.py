
from shotgun_api3_registry import connect

sg = connect()

x = sg.batch([{
    'request_type': 'create',
    'entity_type': 'Version',
    'data': {
        'project': {'type': 'Project', 'id': 66},
        'entity': {'type': 'Shot', 'id': 9579},
        'sg_path_to_movie': '/path/to/movie.mov',
    },
    'return_fields': ['code', 'content'],
}])

print x
