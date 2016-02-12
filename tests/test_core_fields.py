from . import *

class TestEntities(ApiTestCase):

    wants_scanner = wants_events = False

    def setUp(self):
        super(TestEntities, self).setUp()
        sg = self.cached
        self.SHOT = sg.create('Shot', {'code': 'entity_filter_test'})
        #self.USER = sg.create('HumanUser', {'first_name': 'theuser'})
        #self.SCRIPT = sg.create('ApiUser', {'code': 'thescript'})
        #sg.create('Version', {'entity': self.SHOT, 'code': 'none', 'user': None})
        #sg.create('Version', {'entity': self.SHOT, 'code': 'user', 'user': self.USER})
        #sg.create('Version', {'entity': self.SHOT, 'code': 'script', 'user': self.SCRIPT})

    def create_version(self, code, **kwargs):
        kwargs.setdefault('entity', self.SHOT)
        kwargs['code'] = code
        return self.cached.create('Version', kwargs)

    def assertFilter(self, filters, expected, *args):
        filters = list(filters)
        filters.append(('entity', 'is', self.SHOT))
        SHOTs = self.cached.find('Version', filters, ['code'])
        found = sorted(t['code'] for t in SHOTs)
        expected = sorted(expected)
        self.assertEqual(found, expected, *args)

    def test_text_filters(self):

        abc = self.create_version('abc')
        apple = self.create_version('apple')
        xyz = self.create_version('xyz')

        self.assertFilter([
            ('code', 'starts_with', 'a')
        ], ['abc', 'apple'])
        self.assertFilter([
            ('code', 'ends_with', 'z')
        ], ['xyz'])
        self.assertFilter([
            ('code', 'contains', 'b')
        ], ['abc'])
        self.assertFilter([
            ('code', 'not_contains', 'a')
        ], ['xyz'])
        self.assertFilter([
            ('code', 'not_contains', 'b')
        ], ['apple', 'xyz'])

    def test_between_filters(self):

        X = [self.create_version(str(i)) for i in range(5)]

        self.assertFilter([
            ('id', 'between', X[0]['id'], X[4]['id'])
        ], ['0', '1', '2', '3', '4'])

        self.assertFilter([
            ('id', 'not_between', X[0]['id'], X[4]['id'])
        ], [])

        self.assertFilter([
            ('id', 'between', X[1]['id'], X[3]['id'])
        ], ['1', '2', '3'])

        self.assertFilter([
            ('id', 'not_between', X[1]['id'], X[3]['id'])
        ], ['0', '4'])
