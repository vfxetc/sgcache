from tests import connect

from shotgun_api3 import Shotgun

if True:
    sg = connect()
else:
    sg = Shotgun('http://127.0.0.1:8020', 'name', 'key')

print sg.server_info


proj =  sg.create('Project', {'name': 'Mock Project Test'})
seq = sg.create('Sequence', {'code': 'AA', 'project': proj})
shot = sg.create('Shot', {'code': 'AA_001', 'sg_sequence': seq})

print proj
print seq
print shot
#
# print sg.find('Project', [('id', 'is_not', 0)], ['name'], order=[
#     {'field_name': 'id', 'direction': 'asc'},
# ])

print sg._call_rpc('count', None)
exit()

print sg.create('Project', {'name': 'Test Project'})
print sg.count()
print sg.find_one('Project', [], order=[
    {'field_name': 'id', 'direction': 'asc'},
], fields=['task_assignees'])
