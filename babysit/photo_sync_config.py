import os
from dataclasses import dataclass
from pathlib import Path

from .config import BAIDU_REMOTE_PATH, DATA_DIR, DB_PATH


@dataclass(frozen=True)
class PhotoSyncConfig:
    source_path: str
    destination_path: str
    reference_dir: Path
    cache_dir: Path
    db_path: Path
    baidupcs_bin: str
    auto_threshold: float
    review_threshold: float
    scan_limit: int
    page_size: int
    interval: int
    backlog_interval: int
    download_workers: int
    max_retries: int
    model_name: str
    model_dir: Path

    @classmethod
    def from_env(cls):
        destination = os.environ.get(
            "PHOTO_SYNC_DESTINATION_PATH", f"/apps/bypy{BAIDU_REMOTE_PATH}"
        )
        local_baidupcs = DATA_DIR / "photo_sync" / "bin" / "BaiduPCS-Go"
        default_baidupcs = (
            str(local_baidupcs) if local_baidupcs.exists() else "BaiduPCS-Go"
        )
        return cls(
            source_path=os.environ.get("PHOTO_SYNC_SOURCE_PATH", "").rstrip("/"),
            destination_path=destination.rstrip("/"),
            reference_dir=Path(
                os.environ.get(
                    "PHOTO_SYNC_REFERENCE_DIR",
                    DATA_DIR / "photo_sync" / "references",
                )
            ),
            cache_dir=Path(
                os.environ.get(
                    "PHOTO_SYNC_CACHE_DIR", DATA_DIR / "photo_sync" / "thumbnails"
                )
            ),
            db_path=Path(os.environ.get("PHOTO_SYNC_DB_PATH", DB_PATH)),
            baidupcs_bin=os.environ.get(
                "PHOTO_SYNC_BAIDUPCS_BIN", default_baidupcs
            ),
            auto_threshold=float(os.environ.get("PHOTO_SYNC_AUTO_THRESHOLD", "0.55")),
            review_threshold=float(
                os.environ.get("PHOTO_SYNC_REVIEW_THRESHOLD", "0.35")
            ),
            scan_limit=int(os.environ.get("PHOTO_SYNC_SCAN_LIMIT", "50")),
            page_size=int(os.environ.get("PHOTO_SYNC_PAGE_SIZE", "100")),
            interval=int(os.environ.get("PHOTO_SYNC_INTERVAL", "1800")),
            backlog_interval=int(os.environ.get("PHOTO_SYNC_BACKLOG_INTERVAL", "60")),
            download_workers=int(os.environ.get("PHOTO_SYNC_DOWNLOAD_WORKERS", "4")),
            max_retries=int(os.environ.get("PHOTO_SYNC_MAX_RETRIES", "10")),
            model_name=os.environ.get("PHOTO_SYNC_MODEL", "buffalo_l"),
            model_dir=Path(
                os.environ.get(
                    "PHOTO_SYNC_MODEL_DIR", DATA_DIR / "photo_sync" / "models"
                )
            ),
        )

    def validate(self, require_source=True):
        if require_source and not self.source_path:
            raise ValueError("请设置 PHOTO_SYNC_SOURCE_PATH 为手机照片备份目录")
        if self.source_path == "/":
            raise ValueError("PHOTO_SYNC_SOURCE_PATH 不能是网盘根目录")
        if self.destination_path == "/":
            raise ValueError("PHOTO_SYNC_DESTINATION_PATH 不能是网盘根目录")
        if self.source_path and self.destination_path.startswith(self.source_path + "/"):
            raise ValueError("目标目录不能位于来源目录内，否则会重复扫描已复制照片")
        if not -1 <= self.review_threshold < self.auto_threshold <= 1:
            raise ValueError("识别阈值需满足 -1 <= review < auto <= 1")
        if self.scan_limit < 1 or not 1 <= self.page_size <= 1000:
            raise ValueError("scan_limit 必须大于 0，page_size 必须在 1 到 1000 之间")
        if self.interval < 1 or self.backlog_interval < 1 or self.max_retries < 1:
            raise ValueError("interval、backlog_interval 和 max_retries 必须大于 0")
        if not 1 <= self.download_workers <= 16:
            raise ValueError("download_workers 必须在 1 到 16 之间")
