from . import uuid


def task_crud(self, shotgun, trigger_poll=lambda: None):

    name = uuid(8)
    a = shotgun.create('Task', {'content': name})
    trigger_poll()
    b = self.cached.find_one('Task', [('id', 'is', a['id'])], ['content'])
    self.assertSameEntity(a, b)

    name += '-2'
    shotgun.update('Task', a['id'], {'content': name})
    trigger_poll()
    c = self.cached.find_one('Task', [('id', 'is', a['id'])], ['content'])
    self.assertEqual(c['content'], name)

    shotgun.delete('Task', a['id'])
    trigger_poll()
    d = self.cached.find_one('Task', [('id', 'is', a['id'])], ['content'])
    self.assertIs(d, None)
