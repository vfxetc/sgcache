#from shotgun_api3_registry import connect
#sg = connect()

import os
from shotgun_api3 import Shotgun

url = 'http://127.0.0.1:8010'
#url = os.environ['SGCACHE_SHOTGUN_URL']
sg = Shotgun(url, os.environ['SGCACHE_SHOTGUN_SCRIPT_NAME'], os.environ['SGCACHE_SHOTGUN_API_KEY'])


AA = {'type': 'Asset', 'id': 1008}
AB = {'type': 'Asset', 'id': 1009}
AC = {'type': 'Asset', 'id': 1010}
ME = {'type': 'HumanUser', 'id': 108}
TOOLS = {'type': 'Group', 'id': 11}
FX = {'type': 'Group', 'id': 13}


def find(filters):
    filters = list(filters)
    filters.append(('entity.Shot.id', 'is', 10891))
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


print '=== DEEP LINKS ==='

assertTasks([
    ('task_assignees.HumanUser.id', 'is', ME['id']),
], ['both', 'user'])
assertTasks([
    ('task_assignees.HumanUser.id', 'is', ME['id']),
    ('task_assignees.Group.id', 'is', FX['id']),
], ['both'])

# In order for this to work, I think they may *need* to be subqueries.
assertTasks([
    ('task_assignees.HumanUser.id', 'is_not', ME['id']),
    ('task_assignees.Group.id', 'is_not', FX['id']),
], ['none'])
exit()



print '=== IS ==='
assertTasks([
    ('task_assignees', 'is', ME),
],
    ['both', 'user'],
    'x in entities (user)',
)
assertTasks([
    ('task_assignees', 'is', FX),
],
    ['both', 'group'],
    'x in entities (group)',
)
assertTasks([
    ('task_assignees', 'is', TOOLS),
], [],
    'x in entities (no match)',
)

print '=== IS_NOT ==='
assertTasks([
    ('task_assignees', 'is_not', ME),
], ['group', 'none'])
assertTasks([
    ('task_assignees', 'is_not', FX),
], ['user', 'none'])
assertTasks([
    ('task_assignees', 'is_not', TOOLS),
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
    ('task_assignees', 'in', ME),
], ['both', 'user'])
assertTasks([
    ('task_assignees', 'in', FX),
], ['both', 'group'])
assertTasks([
    ('task_assignees', 'in', TOOLS),
], [])
assertTasks([
    ('task_assignees', 'in', ME, FX),
], ['both', 'user', 'group'], 'any(x in entities)')
assertTasks([
    ('task_assignees', 'not_in', ME, FX),
], ['none'], 'not any(x in entities)')
assertTasks([
    ('task_assignees', 'not_in', ME, TOOLS),
], ['group', 'none'], 'not any(x in entities)')


print '=== NOT_IN ==='
assertTasks([
    ('task_assignees', 'not_in', ME),
], ['group', 'none'])
assertTasks([
    ('task_assignees', 'not_in', FX),
], ['user', 'none'])
assertTasks([
    ('task_assignees', 'not_in', TOOLS),
], ['both', 'user', 'group', 'none'])

print '=== NAME_CONTAINS ==='
assertTasks([
    ('task_assignees', 'name_contains', 'Mike'),
], ['both', 'user'])
assertTasks([
    ('task_assignees', 'name_contains', 'FX'),
], ['both', 'group'])

print '=== NAME_NOT_CONTAINS ==='
assertTasks([
    ('task_assignees', 'name_not_contains', 'FX'),
], ['user', 'none'])


print '=== DEEP LINKS ==='

assertTasks([
    ('task_assignees.HumanUser.id', 'is', ME['id']),
], ['both', 'user'])
assertTasks([
    ('task_assignees.HumanUser.id', 'is', ME['id']),
    ('task_assignees.Group.id', 'is', FX['id']),
], ['both'])
