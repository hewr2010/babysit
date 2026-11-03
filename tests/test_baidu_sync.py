import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from babysit.baidu_sync import BaiduAPIError, BaiduImageClient, BaiduPCSClient


class FakeResponse:
    def __init__(self, data=None, content=b""):
        self.data = data
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class BaiduImageClientTests(unittest.TestCase):
    def test_list_page_uses_recursive_image_list(self):
        session = FakeSession([FakeResponse({"errno": 0, "info": [{"fs_id": 1}]})])
        client = BaiduImageClient("/来自：手机", session=session)
        with patch.dict("os.environ", {"BABYSIT_BAIDU_ACCESS_TOKEN": "token"}):
            items = client.list_page(2)

        self.assertEqual(items, [{"fs_id": 1}])
        params = session.calls[0][1]["params"]
        self.assertEqual(params["method"], "imagelist")
        self.assertEqual(params["parent_path"], "/来自：手机")
        self.assertEqual(params["recursion"], 1)
        self.assertEqual(params["page"], 2)

    def test_list_page_raises_baidu_error(self):
        session = FakeSession([FakeResponse({"errno": -7, "errmsg": "denied"})])
        client = BaiduImageClient("/来自：手机", session=session)
        with patch.dict("os.environ", {"BABYSIT_BAIDU_ACCESS_TOKEN": "token"}), \
            self.assertRaisesRegex(BaiduAPIError, "denied"):
            client.list_page(1)

    def test_thumbnail_download_prefers_largest_url(self):
        session = FakeSession([FakeResponse(content=b"image")])
        client = BaiduImageClient("/来自：手机", session=session)
        item = {"thumbs": {"url1": "small", "url3": "large"}}
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "1.jpg"
            client.download_thumbnail(item, destination)
            self.assertEqual(destination.read_bytes(), b"image")
        self.assertEqual(session.calls[0][0], "large")


class BaiduPCSClientTests(unittest.TestCase):
    @patch("babysit.baidu_sync.subprocess.run")
    def test_copy_uses_argument_list_and_verifies_target(self, run):
        run.side_effect = [
            subprocess.CompletedProcess([], 0, "copied", ""),
            subprocess.CompletedProcess([], 0, "meta", ""),
        ]
        client = BaiduPCSClient("/opt/BaiduPCS-Go")
        client.copy("/来源/a photo.jpg", "/目标/a photo.jpg")

        self.assertEqual(
            run.call_args_list[0].args[0],
            ["/opt/BaiduPCS-Go", "cp", "/来源/a photo.jpg", "/目标/a photo.jpg"],
        )
        self.assertNotIn("shell", run.call_args_list[0].kwargs)
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["/opt/BaiduPCS-Go", "meta", "/目标/a photo.jpg"],
        )

    @patch("babysit.baidu_sync.subprocess.run")
    def test_copy_failure_includes_command_output(self, run):
        run.side_effect = [
            subprocess.CompletedProcess([], 1, "", "copy failed"),
            subprocess.CompletedProcess([], 1, "", "not found"),
        ]
        client = BaiduPCSClient()
        with self.assertRaisesRegex(RuntimeError, "copy failed"):
            client.copy("/来源/a.jpg", "/目标/a.jpg")

    @patch("babysit.baidu_sync.subprocess.run")
    def test_who_rejects_uid_zero(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, "当前帐号 uid: 0, 用户名:", ""
        )
        client = BaiduPCSClient()
        with self.assertRaisesRegex(RuntimeError, "尚未登录"):
            client.who()


if __name__ == "__main__":
    unittest.main()
