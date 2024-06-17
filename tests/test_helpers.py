import unittest

from waf_logs import compute_time
from datetime import timedelta, datetime, timezone


class TestSelect(unittest.TestCase):
    def setUp(self):
        now = datetime.now(tz=timezone.utc)
        self.expected = now - timedelta(minutes=now.minute % 5)
        self.expected = self.expected.replace(second=0, microsecond=0)

    def test_compute_time(self):
        result = compute_time(at=None, delta_by_minutes=0)
        self.assertGreaterEqual(result, self.expected)


if __name__ == "__main__":
    unittest.main()
