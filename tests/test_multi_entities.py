from . import *

class TestMultiEntities(ApiTestCase):

    wants_scanner = wants_events = False

    def setUp(self):
        super(TestMultiEntities, self).setUp()
        sg = self.cached
        self.SHOT = sg.create('Shot', {'code': 'multi_entity_test'})
        self.USER = sg.create('HumanUser', {'first_name': 'multi_entity_user'})
        self.GRP1 = sg.create('Group', {'code': 'multi_entity_group1'})
        self.GRP2 = sg.create('Group', {'code': 'multi_entity_group2'})
        sg.create('Task', {'entity': self.SHOT, 'content': 'both', 'task_assignees': [self.USER, self.GRP1]})
        sg.create('Task', {'entity': self.SHOT, 'content': 'user', 'task_assignees': [self.USER]})
        sg.create('Task', {'entity': self.SHOT, 'content': 'group', 'task_assignees': [self.GRP1]})
        sg.create('Task', {'entity': self.SHOT, 'content': 'none', 'task_assignees': []})

    def assertFilters(self, filters, expected, *args):
        filters = list(filters)
        filters.append(('entity', 'is', self.SHOT))
        tasks = self.cached.find('Task', filters, ['content'])
        found = sorted(t['content'] for t in tasks)
        expected = sorted(expected)
        self.assertEqual(found, expected, *args)

    def test_sanity(self):
        self.assertFilters([], ['both', 'user', 'group', 'none'])

    def test_deep_filters_is(self):
        self.assertFilters([
            ('task_assignees.HumanUser.id', 'is', self.USER['id']),
        ], ['both', 'user'])
        self.assertFilters([
            ('task_assignees.Group.id', 'is', self.GRP1['id']),
        ], ['both', 'group'])
        self.assertFilters([
            ('task_assignees.HumanUser.id', 'is', self.USER['id']),
            ('task_assignees.Group.id', 'is', self.GRP1['id']),
        ], ['both'])

        # Make sure that we only get one copy of 'multi'. In earlier implementations
        # this could happen.
        self.cached.create('Task', {'entity': self.SHOT, 'content': 'multi', 'task_assignees': [self.GRP1, self.GRP2]})
        self.assertFilters([
            ('task_assigness.Group.type', 'is', 'Group'),
        ], ['group', 'both', 'multi'])

    def test_deep_filters_is_not(self):
        self.assertFilters([
            ('task_assignees.HumanUser.id', 'is_not', self.USER['id']),
        ], ['group', 'none'])
        self.assertFilters([
            ('task_assignees.Group.id', 'is_not', self.GRP1['id']),
        ], ['user', 'none'])
        self.assertFilters([
            ('task_assignees.HumanUser.id', 'is_not', self.USER['id']),
            ('task_assignees.Group.id', 'is_not', self.GRP1['id']),
        ], ['none'])

    def test_is_filter(self):
        self.assertFilters([
            ('task_assignees', 'is', self.USER),
        ],
            ['both', 'user'],
            'x in entities (user)',
        )
        self.assertFilters([
            ('task_assignees', 'is', self.GRP1),
        ],
            ['both', 'group'],
            'x in entities (group)',
        )
        self.assertFilters([
            ('task_assignees', 'is', self.GRP2),
        ], [],
            'x in entities (no match)',
        )

    def test_is_not_filter(self):
        self.assertFilters([
            ('task_assignees', 'is_not', self.USER),
        ], ['group', 'none'])
        self.assertFilters([
            ('task_assignees', 'is_not', self.GRP1),
        ], ['user', 'none'])
        self.assertFilters([
            ('task_assignees', 'is_not', self.GRP1),
        ], ['both', 'user', 'group', 'none'])

    def test_in_filter(self):
        # Same as is!
        self.assertFilters([
            ('task_assignees', 'in', self.USER),
        ], ['both', 'user'])
        self.assertFilters([
            ('task_assignees', 'in', self.GRP1),
        ], ['both', 'group'])
        self.assertFilters([
            ('task_assignees', 'in', self.GRP1),
        ], [])

        self.assertFilters([
            ('task_assignees', 'in', self.USER, self.GRP1),
        ], ['both', 'user', 'group'], 'any(x in entities)')

    def test_not_in_filter(self):

        # Same as is_not!
        self.assertFilters([
            ('task_assignees', 'not_in', self.USER),
        ], ['group', 'none'])
        self.assertFilters([
            ('task_assignees', 'not_in', self.GRP1),
        ], ['user', 'none'])
        self.assertFilters([
            ('task_assignees', 'not_in', self.GRP1),
        ], ['both', 'user', 'group', 'none'])

        self.assertFilters([
            ('task_assignees', 'not_in', self.USER, self.GRP1),
        ], ['none'], 'not any(x in entities)')
        self.assertFilters([
            ('task_assignees', 'not_in', self.USER, self.GRP1),
        ], ['group', 'none'], 'not any(x in entities)')

    def test_type_is(self):
        self.assertFilters([
            ('task_assignees', 'type_is', 'HumanUser'),
        ], ['both', 'user'])
        self.assertFilters([
            ('task_assignees', 'type_is', 'Group'),
        ], ['both', 'group'])
        self.assertFilters([
            ('task_assignees', 'type_is', 'PublishEvent'),
        ], [])

    def test_type_is_not(self):
        self.assertFilters([
            ('task_assignees', 'type_is_not', 'PublishEvent'),
        ], ['both', 'user', 'group', 'none'])
        self.assertFilters([
            ('task_assignees', 'type_is_not', 'Group'),
        ], ['user', 'none'])
