import os
from pathlib import Path

import requests


class BarkNotifier:
    def __init__(self, key=None, endpoint="https://api.day.app", urls=None):
        if urls:
            self.urls = list(urls)
        elif os.environ.get("BARK_URLS"):
            self.urls = [
                url.strip()
                for url in os.environ["BARK_URLS"].split(",")
                if url.strip()
            ]
        else:
            key = key or os.environ.get("BARK_KEY") or self._key_from_zshrc()
            self.urls = [f"{endpoint.rstrip('/')}/{key}"] if key else []

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

    def notify_round(self, results, pending_review):
        activity_keys = ("copied", "existing", "review", "rejected", "error")
        if not any(results.get(key, 0) for key in activity_keys):
            return False
        body = (
            f"本轮新复制 {results.get('copied', 0)} 个，"
            f"目标已有 {results.get('existing', 0)} 个；\n"
            f"待确认新增 {results.get('review', 0)} 个，"
            f"已归档 {results.get('review_copied', 0)} 个，"
            f"当前待人工处理 {pending_review} 个；\n"
            f"不匹配 {results.get('rejected', 0)} 个，"
            f"失败 {results.get('error', 0)} 个。"
        )
        success = True
        for url in self.urls:
            try:
                response = requests.post(
                    url,
                    data={
                        "title": "宝宝照片同步汇总",
                        "body": body,
                        "sound": "minuet",
                        "level": "active",
                    },
                    timeout=15,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                print(f"Bark 通知失败：{type(exc).__name__}", flush=True)
                success = False
        return success
