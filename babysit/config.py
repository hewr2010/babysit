"""配置模块"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
THUMBNAIL_DIR = DATA_DIR / "thumbnails"
DB_PATH = DATA_DIR / "babysit.db"

BAIDU_REMOTE_PATH = os.environ.get("BABYSIT_PATH", "/爸妈与小宝")
PCS_API_BASE = "https://pcs.baidu.com/rest/2.0/pcs/file"

for d in [DATA_DIR, CACHE_DIR, THUMBNAIL_DIR]:
    d.mkdir(parents=True, exist_ok=True)
