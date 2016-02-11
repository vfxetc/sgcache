from . import *


class TestEvents(SGTestCase):

    def setUp(self):
        self._was_scanning = self.cached.control('scanner', 'stop')
        self.cached.clear()
        self.direct.clear()

    def tearDown(self):
        if self._was_scanning:
            self.cached.control('scanner', 'start')

    def test_create_basics(self):

        name = uuid(8)
        a = self.direct.create('Task', {'content': name})
        self.poll_events()
        b = self.cached.find_one('Task', [('id', 'is', a['id'])], ['content'])
        self.assertSameEntity(a, b)

        name += '-2'
        self.direct.update('Task', a['id'], {'content': name})
        self.poll_events()
        c = self.cached.find_one('Task', [('id', 'is', a['id'])], ['content'])
        self.assertEqual(c['content'], name)

        self.direct.delete('Task', a['id'])
        self.poll_events()
        self.poll_events()
        d = self.cached.find_one('Task', [('id', 'is', a['id'])], ['content'])
        self.assertIs(d, None)
