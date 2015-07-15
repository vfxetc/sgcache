from . import *

from sgcache.utils import parse_interval


class TestIntervals(TestCase):

    def test_intervals(self):
        self.assertEqual(parse_interval('1'), 1)
        self.assertEqual(parse_interval('1s'), 1)
        self.assertEqual(parse_interval('1m'), 60)
        self.assertEqual(parse_interval('1h'), 3600)
        self.assertEqual(parse_interval('1d'), 3600 * 24)
        self.assertEqual(parse_interval('1w'), 3600 * 24 * 7)
        
        self.assertEqual(parse_interval('2s'), 2)
        self.assertEqual(parse_interval('2m'), 120)
