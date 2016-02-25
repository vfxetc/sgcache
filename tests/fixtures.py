from . import uuid


def task_crud(self, shotgun, trigger_poll=lambda: None):

    shot_name = uuid(8)
    shot = shotgun.create('Shot', {'code': shot_name})

    name = uuid(8)
    task = shotgun.create('Task', {'content': name, 'entity': shot})
    trigger_poll()

    x = self.cached.find_one('Task', [('id', 'is', task['id'])], ['content'])
    self.assertSameEntity(task, x)

    # entity field
    x = self.cached.find_one('Task', [('id', 'is', task['id'])], ['entity'])
    self.assertSameEntity(shot, x['entity'])

    # return through entity field
    x = self.cached.find_one('Task', [('id', 'is', task['id'])], ['entity.Shot.code'])
    self.assertEqual(shot_name, x['entity.Shot.code'])

    # Updates
    name += '-2'
    shotgun.update('Task', task['id'], {'content': name})
    trigger_poll()
    x = self.cached.find_one('Task', [('id', 'is', task['id'])], ['content'])
    self.assertEqual(x['content'], name)

    # Delete
    shotgun.delete('Task', task['id'])
    trigger_poll()
    x = self.cached.find_one('Task', [('id', 'is', task['id'])], ['content'])
    self.assertIs(x, None)
    x = self.cached.find_one('Task', [('id', 'is', task['id'])], ['content'], retired_only=True)
    self.assertSameEntity(task, x)
