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
        self.assertEqual(
            body,
            "新处理 23 个，正例 2 个，需人工到「爸妈与小宝-review」确认 1 个。",
        )

    @patch("babysit.notifier.requests.post")
    def test_title_body_placeholder_is_replaced(self, post):
        notifier = BarkNotifier(
            urls=["https://example.test/title/body?group=example&ttl=600"]
        )
        self.assertTrue(notifier.notify_round({"copied": 1}, 2))
        url = post.call_args.args[0]
        self.assertNotIn("/title/body", url)
        self.assertIn("%E5%AE%9D%E5%AE%9D", url)
        self.assertIn("group=example", url)
        self.assertIn("ttl=600", url)

    def test_urls_can_be_loaded_from_ignored_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bark-urls.txt"
            path.write_text("https://example.test/first\nhttps://example.test/second\n")
            notifier = BarkNotifier(urls_file=path)
        self.assertEqual(
            notifier.urls,
            ["https://example.test/first", "https://example.test/second"],
        )

    @patch("babysit.notifier.requests.post")
    def test_empty_round_is_not_sent(self, post):
        notifier = BarkNotifier(urls=["https://example.test/only"])
        self.assertFalse(notifier.notify_round({}, 0))
        post.assert_not_called()

    @patch("babysit.notifier.requests.post")
    def test_reconciliation_and_retry_round_is_not_sent(self, post):
        notifier = BarkNotifier(urls=["https://example.test/only"])
        results = {"existing": 17, "review_copied": 2, "error": 1}
        self.assertFalse(notifier.notify_round(results, 3))
        post.assert_not_called()

    @patch("babysit.notifier.requests.post")
    def test_notification_failure_does_not_raise(self, post):
        import requests

        post.side_effect = requests.ConnectionError("offline")
        notifier = BarkNotifier(urls=["https://example.test/only"])
        self.assertFalse(notifier.notify_round({"copied": 1}, 0))


if __name__ == "__main__":
    unittest.main()
