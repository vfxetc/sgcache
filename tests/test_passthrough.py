from . import *


class TestPassthroughs(SGTestCase):

    def test_create_basics(self):

        self.cached.clear()
        self.direct.clear()
        
        a = self.cached.create('Task', {'content': uuid(8)})
        b = self.direct.find_one('Task', [('id', 'is', a['id'])], ['content'])

        self.assertSameEntity(a, b)
