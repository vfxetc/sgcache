#from shotgun_api3_registry import connect
#sg = connect()

import os

if False:
    from shotgun_api3_registry import connect
    sg = connect(use_cache=False)
else:
    from tests import Shotgun
    url = 'http://127.0.0.1:8010'
    sg = Shotgun(url,
        os.environ.get('SGCACHE_SHOTGUN_SCRIPT_name', 'script_name'),
        os.environ.get('SGCACHE_SHOTGUN_API_KEY', 'api_key'),
    )

if sg.server_info.get('sgcache') or sg.server_info.get('sgmock'):
    sg.clear()
    SHOT = sg.create('Shot', {'code': 'multi_entity_test'})
    USER = sg.create('HumanUser', {'first_name': 'multi_entity_user'})
    GRP1 = sg.create('Group', {'code': 'multi_entity_group1'})
    GRP2 = sg.create('Group', {'code': 'multi_entity_group2'})
    sg.create('Task', {'entity': SHOT, 'content': 'both', 'task_assignees': [USER, GRP1]})
    sg.create('Task', {'entity': SHOT, 'content': 'user', 'task_assignees': [USER]})
    sg.create('Task', {'entity': SHOT, 'content': 'group', 'task_assignees': [GRP1]})
    sg.create('Task', {'entity': SHOT, 'content': 'none', 'task_assignees': []})

else:
    SHOT = {'type': 'Shot', 'id': 10891}
    AA = {'type': 'Asset', 'id': 1008}
    AB = {'type': 'Asset', 'id': 1009}
    AC = {'type': 'Asset', 'id': 1010}
    USER = {'type': 'HumanUser', 'id': 108}
    GRP1 = {'type': 'Group', 'id': 11}
    GRP1 = {'type': 'Group', 'id': 13}


def find(filters):
    filters = list(filters)
    filters.append(('entity', 'is', SHOT))
    return sg.find('Task', filters, ['content'])

def test(filters):
    print '%d filters:' % len(filters)
    for f in filters:
        print '    %r' % (f, )
    entities = find(filters)
    print '%d entities:' % (len(entities))
    for e in entities:
        print '    {id} {content}'.format(**e)
    print

def assertTasks(filters, expected, message=''):
    tasks = find(filters)
    found = sorted(t['content'] for t in tasks)
    expected = sorted(expected)
    if found == expected:
        print '%s%sOk.' % (message or '', ': ' if message else '')
    else:
        print '%s%sERROR! Expected %s, found %s' % (message or '', ': ' if message else '', expected, found)


'''

HOLY SHIT!
>>> sg.find_one('Task', [('sg_assets.Task_sg_assets_Connection.asset.Asset.code', 'contains', 'Dummy')])
>>> sg.find_one('Task', [('sg_assets.Asset.code', 'contains', 'Dummy')])

'''

print '=== name_CONTAINS ==='
assertTasks([
    ('task_assignees', 'name_contains', 'Mike'),
], ['both', 'user'])
assertTasks([
    ('task_assignees', 'name_contains', 'GRP1'),
], ['both', 'group'])

print '=== name_NOT_CONTAINS ==='
assertTasks([
    ('task_assignees', 'name_not_contains', 'GRP1'),
], ['user', 'none'])
