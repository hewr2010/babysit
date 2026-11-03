import os
import re
import subprocess
from pathlib import Path

import requests

from .baidu import get_access_token
from .config import DATA_DIR


class BaiduAPIError(RuntimeError):
    pass


class ThumbnailNotReady(BaiduAPIError):
    pass


class BaiduImageClient:
    endpoint = "https://pan.baidu.com/rest/2.0/xpan/file"

    def __init__(self, source_path, page_size=100, timeout=30, session=None):
        self.source_path = source_path
        self.page_size = page_size
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "pan.baidu.com"})

    @staticmethod
    def _access_token():
        return os.environ.get("BABYSIT_BAIDU_ACCESS_TOKEN") or get_access_token()

    def list_page(self, page, num=None):
        token = self._access_token()
        if not token:
            raise BaiduAPIError("未找到百度 access token，请先完成 bypy 授权")
        response = self.session.get(
            self.endpoint,
            params={
                "method": "imagelist",
                "access_token": token,
                "parent_path": self.source_path,
                "recursion": 1,
                "web": 1,
                "order": "time",
                "desc": 1,
                "page": page,
                "num": num or self.page_size,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errno") != 0:
            raise BaiduAPIError(
                f"百度图片列表失败 errno={data.get('errno')}: "
                f"{data.get('errmsg') or data.get('show_msg') or data.get('newno') or ''}"
            )
        return data.get("info", [])

    def iter_pages(self):
        page = 1
        while True:
            items = self.list_page(page)
            yield items
            if len(items) < self.page_size:
                break
            page += 1

    def download_thumbnail(self, photo, destination):
        thumbs = photo.get("thumbs") or {}
        url = thumbs.get("url3") or thumbs.get("url2") or thumbs.get("url1")
        if not url:
            raise ThumbnailNotReady("缩略图尚未生成")
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        if not response.content:
            raise ThumbnailNotReady("缩略图内容为空")
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(response.content)
        temporary.replace(destination)
        return destination


class BaiduPCSClient:
    def __init__(self, executable="BaiduPCS-Go", timeout=120, config_dir=None):
        self.executable = executable
        self.timeout = timeout
        self.config_dir = Path(
            config_dir or DATA_DIR / "photo_sync" / "baidupcs-config"
        )

    def _run(self, *args):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.setdefault("BAIDUPCS_GO_CONFIG_DIR", str(self.config_dir))
        try:
            return subprocess.run(
                [self.executable, *args],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=self.timeout,
                check=False,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"找不到 {self.executable}，请安装 BaiduPCS-Go 或设置 "
                "PHOTO_SYNC_BAIDUPCS_BIN"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"BaiduPCS-Go {args[0]} 执行超时") from exc

    @staticmethod
    def _output(result):
        return (result.stdout + "\n" + result.stderr).strip()

    def who(self):
        result = self._run("who")
        output = self._output(result)
        if result.returncode != 0:
            raise RuntimeError("BaiduPCS-Go 登录检查失败：" + output)
        uid = re.search(r"uid:\s*(\d+)", output)
        if uid and int(uid.group(1)) == 0:
            raise RuntimeError("BaiduPCS-Go 尚未登录，请先按其 README 完成登录")
        return output

    def exists(self, remote_path):
        return self._run("meta", remote_path).returncode == 0

    def copy(self, source_path, target_path):
        result = self._run("cp", source_path, target_path)
        if self.exists(target_path):
            return
        raise RuntimeError(
            f"复制或复制后校验失败（exit={result.returncode}）：{self._output(result)}"
        )
