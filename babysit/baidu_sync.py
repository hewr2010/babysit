import os
import re
import subprocess
import time
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

    def list_files(self, remote_path):
        token = self._access_token()
        if not token:
            raise BaiduAPIError("未找到百度 access token，请先完成 bypy 授权")
        files = []
        start = 0
        limit = 1000
        while True:
            response = self.session.get(
                self.endpoint,
                params={
                    "method": "list",
                    "access_token": token,
                    "dir": remote_path,
                    "start": start,
                    "limit": limit,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("errno") != 0:
                raise BaiduAPIError(
                    f"目标目录读取失败 errno={data.get('errno')}: "
                    f"{data.get('errmsg') or data.get('show_msg') or data.get('newno') or ''}"
                )
            batch = data.get("list", [])
            files.extend(item for item in batch if not item.get("isdir"))
            if len(batch) < limit:
                break
            start += len(batch)
        return files

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

    def prefetch_thumbnails(self, photos, cache_dir, workers):
        import threading
        from concurrent.futures import ThreadPoolExecutor

        local = threading.local()

        def fetch(photo):
            fs_id = str(photo["fs_id"])
            try:
                if not hasattr(local, "client"):
                    local.client = BaiduImageClient(
                        self.source_path, self.page_size, self.timeout
                    )
                destination = Path(cache_dir) / f"{fs_id}.jpg"
                local.client.download_thumbnail(photo, destination)
                return fs_id, None
            except (OSError, RuntimeError, requests.RequestException) as exc:
                return fs_id, exc

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = pool.map(fetch, photos)
        return {fs_id: error for fs_id, error in results if error is not None}


class BaiduPCSClient:
    def __init__(self, executable=None, timeout=120, config_dir=None):
        local_executable = DATA_DIR / "photo_sync" / "bin" / "BaiduPCS-Go"
        default_executable = (
            str(local_executable) if local_executable.exists() else "BaiduPCS-Go"
        )
        self.executable = executable or os.environ.get(
            "PHOTO_SYNC_BAIDUPCS_BIN", default_executable
        )
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

    def ensure_directory(self, remote_path):
        if self.exists(remote_path):
            return
        result = self._run("mkdir", remote_path)
        if not self.exists(remote_path):
            raise RuntimeError(f"创建目录失败：{self._output(result)}")

    def copy(self, source_path, target_path):
        result = self._run("cp", source_path, target_path)
        if self.exists(target_path):
            return
        raise RuntimeError(
            f"复制或复制后校验失败（exit={result.returncode}）：{self._output(result)}"
        )

    def download(self, source_path, destination_dir):
        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        target = destination_dir / source_path.rsplit("/", 1)[-1]
        result = None
        for attempt in range(3):
            result = self._run(
                "download", "--saveto", str(destination_dir), source_path
            )
            if result.returncode == 0 and target.exists() and target.stat().st_size:
                return target
            if attempt < 2:
                time.sleep(2**attempt)
        raise RuntimeError(
            f"视频下载失败（exit={result.returncode}）：{self._output(result)}"
        )
