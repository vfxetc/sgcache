from . import *


class TestScanner(ApiTestCase):

    wants_events = False
    wants_scanner = True

    def test_basic_crud(self):
        fixtures.task_crud(self, self.direct, self.poll_scanner)
