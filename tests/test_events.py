from . import *


class TestEvents(ApiTestCase):

    wants_events = True
    wants_scanner = False

    def test_basic_crud(self):
        fixtures.task_crud(self, self.direct, self.poll_events)
