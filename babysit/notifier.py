import os
from pathlib import Path

import requests


class BarkNotifier:
    def __init__(self, key=None, endpoint="https://api.day.app"):
        self.key = key or os.environ.get("BARK_KEY") or self._key_from_zshrc()
        self.endpoint = endpoint.rstrip("/")

    @staticmethod
    def _key_from_zshrc():
        path = Path.home() / ".zshrc"
        if not path.exists():
            return None
        try:
            for line in path.read_text().splitlines():
                if line.startswith("export BARK_KEY="):
                    return line.split("=", 1)[1].strip().strip("\"'")
        except OSError:
            pass
        return None

    def notify_review(self, items, destination):
        if not items or not self.key:
            return False
        names = [item["filename"] for item in items]
        summary = "、".join(names[:3])
        if len(names) > 3:
            summary += f" 等 {len(names)} 个文件"
        try:
            response = requests.post(
                f"{self.endpoint}/{self.key}",
                data={
                    "title": "宝宝照片待确认",
                    "body": f"新增 {len(names)} 个待确认文件，已复制到 {destination}。\n{summary}",
                    "sound": "minuet",
                    "level": "active",
                },
                timeout=15,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            print(f"Bark 通知失败：{type(exc).__name__}", flush=True)
            return False
