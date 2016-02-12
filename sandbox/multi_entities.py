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
        os.environ.get('SGCACHE_SHOTGUN_SCRIPT_NAUSER', 'script_name'),
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

print '=== SANITY CHECK ==='
assertTasks([], ['both', 'user', 'group', 'none'])




print '=== IS ==='
assertTasks([
    ('task_assignees', 'is', USER),
],
    ['both', 'user'],
    'x in entities (user)',
)

exit()

assertTasks([
    ('task_assignees', 'is', GRP1),
],
    ['both', 'group'],
    'x in entities (group)',
)
assertTasks([
    ('task_assignees', 'is', GRP1),
], [],
    'x in entities (no match)',
)

print '=== IS_NOT ==='
assertTasks([
    ('task_assignees', 'is_not', USER),
], ['group', 'none'])
assertTasks([
    ('task_assignees', 'is_not', GRP1),
], ['user', 'none'])
assertTasks([
    ('task_assignees', 'is_not', GRP1),
], ['both', 'user', 'group', 'none'])

print '=== TYPE_IS ==='
assertTasks([
    ('task_assignees', 'type_is', 'HumanUser'),
], ['both', 'user'])
assertTasks([
    ('task_assignees', 'type_is', 'Group'),
], ['both', 'group'])
assertTasks([
    ('task_assignees', 'type_is', 'PublishEvent'),
], [])

print '=== TYPE_IS_NOT ==='
assertTasks([
    ('task_assignees', 'type_is_not', 'PublishEvent'),
], ['both', 'user', 'group', 'none'])
assertTasks([
    ('task_assignees', 'type_is_not', 'Group'),
], ['user', 'none'])

print '=== IN ==='
assertTasks([
    ('task_assignees', 'in', USER),
], ['both', 'user'])
assertTasks([
    ('task_assignees', 'in', GRP1),
], ['both', 'group'])
assertTasks([
    ('task_assignees', 'in', GRP1),
], [])
assertTasks([
    ('task_assignees', 'in', USER, GRP1),
], ['both', 'user', 'group'], 'any(x in entities)')
assertTasks([
    ('task_assignees', 'not_in', USER, GRP1),
], ['none'], 'not any(x in entities)')
assertTasks([
    ('task_assignees', 'not_in', USER, GRP1),
], ['group', 'none'], 'not any(x in entities)')


print '=== NOT_IN ==='
assertTasks([
    ('task_assignees', 'not_in', USER),
], ['group', 'none'])
assertTasks([
    ('task_assignees', 'not_in', GRP1),
], ['user', 'none'])
assertTasks([
    ('task_assignees', 'not_in', GRP1),
], ['both', 'user', 'group', 'none'])

print '=== NAUSER_CONTAINS ==='
assertTasks([
    ('task_assignees', 'naUSER_contains', 'Mike'),
], ['both', 'user'])
assertTasks([
    ('task_assignees', 'naUSER_contains', 'GRP1'),
], ['both', 'group'])

print '=== NAUSER_NOT_CONTAINS ==='
assertTasks([
    ('task_assignees', 'naUSER_not_contains', 'GRP1'),
], ['user', 'none'])


print '=== DEEP LINKS ==='


assertTasks([
    ('task_assignees.HumanUser.id', 'is', USER['id']),
], ['both', 'user'])
assertTasks([
    ('task_assignees.Group.id', 'is', GRP1['id']),
], ['both', 'group'])

assertTasks([
    ('task_assignees.HumanUser.id', 'is', USER['id']),
    ('task_assignees.Group.id', 'is', GRP1['id']),
], ['both'])

# Invert the logic above.
assertTasks([
    ('task_assignees.HumanUser.id', 'is_not', USER['id']),
], ['group', 'none'])
assertTasks([
    ('task_assignees.Group.id', 'is_not', GRP1['id']),
], ['user', 'none'])

# In order for this to work, I think they may *need* to be subqueries.
assertTasks([
    ('task_assignees.HumanUser.id', 'is_not', USER['id']),
    ('task_assignees.Group.id', 'is_not', GRP1['id']),
], ['none'])
exit()
