from . import *


class TestScanner(SGTestCase):

    def setUp(self):
        self._was_watching = self.cached.control('events', 'stop')
        self.cached.clear()
        self.direct.clear()

    def tearDown(self):
        if self._was_watching:
            self.cached.control('events', 'start')

    def test_create_basics(self):

        self.direct.log('>>> test_create_basics')
        a = self.direct.create('Task', {'content': uuid(8)})
        self.direct.log('scanning...')
        self.poll_scanner()
        self.direct.log('Done scanning.')

        b = self.cached.find_one('Task', [('id', 'is', a['id'])], ['content'])

        self.assertSameEntity(a, b)
