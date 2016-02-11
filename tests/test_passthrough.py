from . import *


class TestPassthroughs(ApiTestCase):

    wants_events = False
    wants_scanner = False

    def test_basic_crud(self):
        fixtures.task_crud(self, self.cached, self.poll_scanner)
