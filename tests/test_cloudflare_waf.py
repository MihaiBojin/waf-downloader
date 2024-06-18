from typing import Any, Dict
import unittest

from waf_logs.cloudflare_waf import WAF
from waf_logs.downloader import merge_logs


class TestMergeLogs(unittest.TestCase):
    def test_merge_logs(self):
        # ARRANGE
        result1 = [
            _data("ray1", "2021-01-01T00:00:00Z", "field1", "value1"),
            _data("ray2", "2021-01-01T00:00:00Z", "field2", "value2"),
        ]
        result2 = [
            _data("ray2", "2021-01-01T00:00:00Z", "field21", "value21"),
            _data("ray3", "2021-01-01T00:00:00Z", "field3", "value3"),
        ]
        result3 = [
            _data("ray4", "2021-01-01T00:00:00Z", "field4", "value4"),
        ]

        # ACT
        results = [result1, result2, result3]
        result = merge_logs(results)
        print(result)

        # ASSERT
        expected = [
            _wrap(
                {
                    "rayName": "ray1",
                    "datetime": "2021-01-01T00:00:00Z",
                    "data": {"field1": "value1"},
                }
            ),
            _wrap(
                {
                    "rayName": "ray2",
                    "datetime": "2021-01-01T00:00:00Z",
                    "data": {"field2": "value2", "field21": "value21"},
                }
            ),
            _wrap(
                {
                    "rayName": "ray3",
                    "datetime": "2021-01-01T00:00:00Z",
                    "data": {"field3": "value3"},
                }
            ),
            _wrap(
                {
                    "rayName": "ray4",
                    "datetime": "2021-01-01T00:00:00Z",
                    "data": {"field4": "value4"},
                }
            ),
        ]

        self.assertEqual(result, expected)


def _data(id: str, dt: str, field_name: str, value: str) -> WAF:
    data = {
        "rayName": id,
        "datetime": dt,
        "data": {field_name: value},
    }

    return _wrap(data)


def _wrap(data: Dict[str, Any]) -> WAF:
    values = data["data"]
    return WAF(str(data["rayName"]), str(data["datetime"]), data=values)


if __name__ == "__main__":
    unittest.main()
