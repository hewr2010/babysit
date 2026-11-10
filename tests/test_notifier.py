import unittest
from unittest.mock import patch

from babysit.notifier import BarkNotifier


class BarkNotifierTests(unittest.TestCase):
    @patch("babysit.notifier.requests.post")
    def test_round_summary_is_sent_to_all_urls(self, post):
        urls = ["https://example.test/first", "https://example.test/second"]
        notifier = BarkNotifier(urls=urls)
        results = {
            "copied": 2,
            "existing": 5,
            "review": 1,
            "review_copied": 1,
            "rejected": 20,
            "error": 0,
        }
        self.assertTrue(notifier.notify_round(results, 7))

        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[0].args[0], urls[0])
        self.assertEqual(post.call_args_list[1].args[0], urls[1])
        body = post.call_args.kwargs["data"]["body"]
        self.assertIn("新复制 2 个", body)
        self.assertIn("目标已有 5 个", body)
        self.assertIn("待确认新增 1 个", body)
        self.assertIn("当前待人工处理 7 个", body)
        self.assertIn("不匹配 20 个", body)

    @patch("babysit.notifier.requests.post")
    def test_empty_round_is_not_sent(self, post):
        notifier = BarkNotifier(urls=["https://example.test/only"])
        self.assertFalse(notifier.notify_round({}, 0))
        post.assert_not_called()

    @patch("babysit.notifier.requests.post")
    def test_notification_failure_does_not_raise(self, post):
        import requests

        post.side_effect = requests.ConnectionError("offline")
        notifier = BarkNotifier(urls=["https://example.test/only"])
        self.assertFalse(notifier.notify_round({"copied": 1}, 0))


if __name__ == "__main__":
    unittest.main()
