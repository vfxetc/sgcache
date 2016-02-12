from . import *

class TestOrder(ApiTestCase):

    def test_number_order(self):

        sg = self.cached

        shot = sg.create('Shot', {'code': 'multi_entity_test'})
        for i in xrange(4):
            sg.create('Task', {'entity': shot, 'content': '%d' % i})

        tasks = sg.find('Task', [('entity', 'is', shot)], ['content'], order=[
            {'field_name': 'id', 'direction': 'asc'}
        ])
        content = [e['content'] for e in tasks]
        self.assertEqual(content, ['0', '1', '2', '3'])

        tasks = sg.find('Task', [('entity', 'is', shot)], ['content'], order=[
            {'field_name': 'id', 'direction': 'desc'}
        ])
        content = [e['content'] for e in tasks]
        self.assertEqual(content, ['3', '2', '1', '0'])
