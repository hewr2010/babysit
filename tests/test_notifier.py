import unittest
from unittest.mock import patch

from babysit.notifier import BarkNotifier


class BarkNotifierTests(unittest.TestCase):
    @patch("babysit.notifier.requests.post")
    def test_review_notification_is_batched(self, post):
        notifier = BarkNotifier(key="test-key")
        items = [
            {"filename": "a.jpg"},
            {"filename": "b.livp"},
            {"filename": "c.jpg"},
            {"filename": "d.jpg"},
        ]
        self.assertTrue(notifier.notify_review(items, "/apps/bypy/爸妈与小宝-review"))
        data = post.call_args.kwargs["data"]
        self.assertIn("新增 4 个", data["body"])
        self.assertIn("等 4 个文件", data["body"])
        self.assertIn("/apps/bypy/爸妈与小宝-review", data["body"])
        self.assertNotIn("test-key", data["body"])

    @patch("babysit.notifier.requests.post")
    def test_notification_failure_does_not_raise(self, post):
        import requests

        post.side_effect = requests.ConnectionError("offline")
        notifier = BarkNotifier(key="test-key")
        self.assertFalse(notifier.notify_review([{"filename": "a.jpg"}], "/review"))


if __name__ == "__main__":
    unittest.main()
