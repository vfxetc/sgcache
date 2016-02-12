from . import *

class TestMultiEntities(ApiTestCase):

    # wants_scanner = wants_events = False

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

    def assertTasks(self, filters, expected, *args):
        filters = list(filters)
        filters.append(('entity', 'is', self.SHOT))
        tasks = self.cached.find('Task', filters, ['content'])
        found = sorted(t['content'] for t in tasks)
        expected = sorted(expected)

    def test_sanity(self):
        self.assertTasks([], ['both', 'user', 'group', 'none'])

    def test_deep_filters_is(self):
        self.assertTasks([
            ('task_assignees.HumanUser.id', 'is', self.USER['id']),
        ], ['both', 'user'])
        self.assertTasks([
            ('task_assignees.Group.id', 'is', self.GRP1['id']),
        ], ['both', 'group'])
        self.assertTasks([
            ('task_assignees.HumanUser.id', 'is', self.USER['id']),
            ('task_assignees.Group.id', 'is', self.GRP1['id']),
        ], ['both'])

    def test_deep_filters_is_not(self):
        self.assertTasks([
            ('task_assignees.HumanUser.id', 'is_not', self.USER['id']),
        ], ['group', 'none'])
        self.assertTasks([
            ('task_assignees.Group.id', 'is_not', self.GRP1['id']),
        ], ['user', 'none'])
        self.assertTasks([
            ('task_assignees.HumanUser.id', 'is_not', self.USER['id']),
            ('task_assignees.Group.id', 'is_not', self.GRP1['id']),
        ], ['none'])

    def test_is_filter(self):
        self.assertTasks([
            ('task_assignees', 'is', self.USER),
        ],
            ['both', 'user'],
            'x in entities (user)',
        )
        self.assertTasks([
            ('task_assignees', 'is', self.GRP1),
        ],
            ['both', 'group'],
            'x in entities (group)',
        )
        self.assertTasks([
            ('task_assignees', 'is', self.GRP2),
        ], [],
            'x in entities (no match)',
        )

    def test_is_not_filter(self):
        self.assertTasks([
            ('task_assignees', 'is_not', self.USER),
        ], ['group', 'none'])
        self.assertTasks([
            ('task_assignees', 'is_not', self.GRP1),
        ], ['user', 'none'])
        self.assertTasks([
            ('task_assignees', 'is_not', self.GRP1),
        ], ['both', 'user', 'group', 'none'])
