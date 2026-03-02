"""
babysit 配置
"""

import os
from pathlib import Path

# 数据目录（用户主目录下）
DATA_DIR = Path.home() / ".babysit"
CACHE_DIR = DATA_DIR / "cache"
THUMBNAIL_DIR = DATA_DIR / "thumbnails"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

# 百度网盘路径（可修改）
BAIDU_REMOTE_PATH = os.environ.get("BABY_ALBUM_PATH", "/爸妈与小宝")

# 支持的文件格式
PHOTO_EXTS = ('.jpg', '.jpeg', '.png', '.heic', '.heif', '.gif', '.bmp', '.webp')
VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp')
ALL_MEDIA_EXTS = PHOTO_EXTS + VIDEO_EXTS
