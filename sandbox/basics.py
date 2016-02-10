from shotgun_api3_registry import connect

sg = connect()
sg.pragma = {}

old_build_payload = sg._build_payload
def build_payload(*args, **kwargs):
    payload = old_build_payload(*args, **kwargs)
    if sg.pragma:
        payload['pragma'] = sg.pragma
    return payload
sg._build_payload = build_payload

sg.pragma['sgcache_local_only'] = True

print sg.find_one('Task', [], order=[
    {'field_name': 'id', 'direction': 'asc'},
], fields=['task_assignees'])
