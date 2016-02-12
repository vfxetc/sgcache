from . import *

class TestEntities(ApiTestCase):

    wants_scanner = wants_events = False

    def setUp(self):
        super(TestEntities, self).setUp()
        sg = self.cached
        self.SHOT = sg.create('Shot', {'code': 'entity_filter_test'})
        self.USER = sg.create('HumanUser', {'first_name': 'theuser'})
        self.SCRIPT = sg.create('ApiUser', {'code': 'thescript'})
        sg.create('Version', {'entity': self.SHOT, 'code': 'none', 'user': None})
        sg.create('Version', {'entity': self.SHOT, 'code': 'user', 'user': self.USER})
        sg.create('Version', {'entity': self.SHOT, 'code': 'script', 'user': self.SCRIPT})

    def assertFilter(self, filters, expected, *args):
        filters = list(filters)
        filters.append(('entity', 'is', self.SHOT))
        SHOTs = self.cached.find('Version', filters, ['code'])
        found = sorted(t['code'] for t in SHOTs)
        expected = sorted(expected)
        self.assertEqual(found, expected, *args)

    def test_sanity(self):
        self.assertFilter([], ['user', 'script', 'none'])

    def test_is_filter(self):
        self.assertFilter([
            ('user', 'is', self.USER),
        ],
            ['user'],
            'x is user',
        )
        self.assertFilter([
            ('user', 'is', self.SCRIPT),
        ],
            ['script'],
            'x is script',
        )
        self.assertFilter([
            ('user', 'is', None),
        ], ['none'],
            'x is None',
        )

    def test_is_not_filter(self):
        self.assertFilter([
            ('user', 'is_not', self.USER),
        ], ['script', 'none'])
        self.assertFilter([
            ('user', 'is_not', self.SCRIPT),
        ], ['user', 'none'])
        self.assertFilter([
            ('user', 'is_not', None),
        ], ['user', 'script'])

    def test_in_filter(self):
        self.assertFilter([
            ('user', 'in', self.USER),
        ], ['user'])
        self.assertFilter([
            ('user', 'in', self.SCRIPT),
        ], ['script'])
        self.assertFilter([
            ('user', 'in', self.USER, self.SCRIPT),
        ], ['user', 'script'])
        self.assertFilter([
            ('user', 'in', self.USER, None),
        ], ['user', 'none'])

    def test_not_in_filter(self):

        # Same as is_not!
        self.assertFilter([
            ('user', 'not_in', self.USER),
        ], ['script', 'none'])
        self.assertFilter([
            ('user', 'not_in', self.SCRIPT),
        ], ['user', 'none'])
        self.assertFilter([
            ('user', 'not_in', None),
        ], ['user', 'script'])

        self.assertFilter([
            ('user', 'not_in', self.USER, self.SCRIPT),
        ], ['none'], 'not any(x in entities)')
        self.assertFilter([
            ('user', 'not_in', self.USER, None),
        ], ['script'], 'not any(x in entities)')


    def test_type_is(self):
        self.assertFilter([
            ('user', 'type_is', 'HumanUser'),
        ], ['user'])
        self.assertFilter([
            ('user', 'type_is', 'ApiUser'),
        ], ['script'])
        self.assertFilter([
            ('user', 'type_is', None),
        ], ['none'])
        self.assertFilter([
            ('user', 'type_is', 'Group'),
        ], [])

    def test_type_is_not(self):
        self.assertFilter([
            ('user', 'type_is_not', 'HumanUser'),
        ], ['script', 'none'])
        self.assertFilter([
            ('user', 'type_is_not', None),
        ], ['script', 'user'])
        self.assertFilter([
            ('user', 'type_is_not', 'Group'),
        ], ['user', 'script', 'none'])
