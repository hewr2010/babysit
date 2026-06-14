"""测试 refresh_media 和数据库架构"""
import os
import sqlite3
import pytest
from pathlib import Path

# 设置测试环境
os.chdir(Path(__file__).parent.parent)

from babysit.config import DATA_DIR, CACHE_DIR
from babysit.db import (
    init_db, get_standalone_db, update_media_file,
    delete_media_file, get_standalone_processed_media,
    get_standalone_processed_media_by_month
)


@pytest.fixture
def test_db():
    """创建测试数据库"""
    # 使用测试数据库
    test_db_path = DATA_DIR / "test_babysit.db"

    # 备份原数据库
    orig_db = DATA_DIR / "babysit.db"
    backup_db = None
    if orig_db.exists():
        backup_db = DATA_DIR / "babysit.db.backup"
        orig_db.rename(backup_db)

    # 设置测试数据库路径
    import babysit.db as db_module
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = test_db_path

    # 初始化测试数据库
    init_db()

    yield test_db_path

    # 清理
    db_module.DB_PATH = original_db_path
    if test_db_path.exists():
        test_db_path.unlink()
    if backup_db and backup_db.exists():
        backup_db.rename(orig_db)


def test_init_db_creates_tables(test_db):
    """测试数据库初始化创建所有表"""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    assert 'baby' in tables
    assert 'records' in tables
    assert 'growth' in tables
    assert 'media_files' in tables

    conn.close()


def test_update_media_file(test_db):
    """测试更新/插入媒体文件"""
    db = get_standalone_db()

    file_info = {
        'name': 'test_2026-03-01 101234.jpg',
        'type': 'photo',
        'size': 12345,
        'md5': 'abc123',
        'date': '2026-03-01',
        'time': '10:12',
        'baidu_date': '2026-03-01',
        'processed': True,
        'processed_at': '2026-03-07T10:00:00'
    }

    update_media_file(db, file_info)
    db.commit()

    # 验证插入
    cursor = db.execute("SELECT * FROM media_files WHERE filename = ?", (file_info['name'],))
    row = cursor.fetchone()

    assert row is not None
    assert row['filename'] == file_info['name']
    assert row['file_type'] == 'photo'
    assert row['processed'] == 1

    db.close()


def test_get_processed_media(test_db):
    """测试获取已处理的媒体文件"""
    db = get_standalone_db()

    # 插入测试数据
    test_files = [
        {
            'name': 'test1_2026-03-01.jpg',
            'type': 'photo',
            'size': 1000,
            'md5': 'md5_1',
            'date': '2026-03-01',
            'time': '10:00',
            'baidu_date': '2026-03-01',
            'processed': True,
            'processed_at': '2026-03-07T10:00:00'
        },
        {
            'name': 'test2_2026-03-01.mp4',
            'type': 'video',
            'size': 5000,
            'md5': 'md5_2',
            'date': '2026-03-01',
            'time': '11:00',
            'baidu_date': '2026-03-01',
            'processed': True,
            'processed_at': '2026-03-07T10:00:00'
        },
        {
            'name': 'test3_2026-03-02.jpg',
            'type': 'photo',
            'size': 2000,
            'md5': 'md5_3',
            'date': '2026-03-02',
            'time': '09:00',
            'baidu_date': '2026-03-02',
            'processed': True,
            'processed_at': '2026-03-07T10:00:00'
        },
        {
            'name': 'test4_unprocessed.jpg',
            'type': 'photo',
            'size': 3000,
            'md5': 'md5_4',
            'date': '2026-03-03',
            'time': '08:00',
            'baidu_date': '2026-03-03',
            'processed': False,
            'processed_at': None
        }
    ]

    for f in test_files:
        update_media_file(db, f)
    db.commit()
    db.close()

    # 查询已处理的文件
    result = get_standalone_processed_media()

    # 应该只返回已处理的文件
    assert '2026-03-01' in result
    assert '2026-03-02' in result
    assert '2026-03-03' not in result  # 未处理的不应该返回

    # 检查内容
    assert len(result['2026-03-01']) == 2
    assert len(result['2026-03-02']) == 1


def test_get_processed_media_by_month(test_db):
    """测试按月获取已处理的媒体文件"""
    db = get_standalone_db()

    # 插入测试数据
    test_files = [
        {
            'name': 'mar_2026-03-01.jpg',
            'type': 'photo',
            'size': 1000,
            'md5': 'md5_mar',
            'date': '2026-03-01',
            'time': '10:00',
            'baidu_date': '2026-03-01',
            'processed': True,
            'processed_at': '2026-03-07T10:00:00'
        },
        {
            'name': 'feb_2026-02-15.jpg',
            'type': 'photo',
            'size': 2000,
            'md5': 'md5_feb',
            'date': '2026-02-15',
            'time': '14:00',
            'baidu_date': '2026-02-15',
            'processed': True,
            'processed_at': '2026-03-07T10:00:00'
        }
    ]

    for f in test_files:
        update_media_file(db, f)
    db.commit()
    db.close()

    # 查询3月份
    result = get_standalone_processed_media_by_month(2026, 3)
    assert '2026-03-01' in result
    assert len(result['2026-03-01']) == 1

    # 查询2月份
    result = get_standalone_processed_media_by_month(2026, 2)
    assert '2026-02-15' in result
    assert len(result['2026-02-15']) == 1


def test_delete_media_file(test_db):
    """测试删除媒体文件记录"""
    db = get_standalone_db()

    file_info = {
        'name': 'to_delete.jpg',
        'type': 'photo',
        'size': 1000,
        'md5': 'md5_del',
        'date': '2026-03-01',
        'time': '10:00',
        'baidu_date': '2026-03-01',
        'processed': True,
        'processed_at': '2026-03-07T10:00:00'
    }

    update_media_file(db, file_info)
    db.commit()

    # 删除
    delete_media_file(db, file_info['name'])
    db.commit()

    # 验证删除
    cursor = db.execute("SELECT * FROM media_files WHERE filename = ?", (file_info['name'],))
    row = cursor.fetchone()

    assert row is None
    db.close()


def test_process_video_uses_streaming(tmp_path, monkeypatch):
    """验证大视频在 refresh_media 中通过流式下载落盘，而不是全部读进内存"""
    import shutil
    import subprocess
    from urllib.parse import quote

    import babysit.refresh_media as rm

    fake_video = tmp_path / "fake.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-pix_fmt", "yuv420p",
            "-y",
            str(fake_video),
        ],
        check=True,
        capture_output=True,
    )

    monkeypatch.setattr(rm, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(rm, "get_download_url", lambda fn: ("http://dummy", None))

    def fake_download(url, dest_path, timeout=120):
        shutil.copy(str(fake_video), str(dest_path))
        return True, None

    monkeypatch.setattr(rm, "_download_to_file", fake_download)

    thumbs = tmp_path / "thumbs"
    previews = tmp_path / "previews"
    videos = tmp_path / "videos"
    for d in (thumbs, previews, videos):
        d.mkdir(parents=True, exist_ok=True)

    filename = "VID_20260610_140921.mp4"
    safe = quote(filename, safe="")
    info = {
        "name": filename,
        "type": "video",
        "size": fake_video.stat().st_size,
        "date": "2026-06-10",
        "time": "14:09",
        "baidu_date": "2026-06-10",
        "processed": False,
    }

    success, updated = rm.process_media_file(info, thumbs, previews, videos)

    assert success is True
    assert updated["processed"] is True
    assert (thumbs / f"{safe}_200x200.jpg").exists()
    assert (previews / f"{safe}_800x800.jpg").exists()
    assert (videos / safe).exists()


def test_repair_media_database_resets_partial_records(test_db, tmp_path, monkeypatch):
    """repair_media_database 应把缓存不完整的 processed 记录重置为 0 并清理残片"""
    import shutil
    import subprocess
    from urllib.parse import quote

    import babysit.db as db_module
    import babysit.refresh_media as rm

    fake_video = tmp_path / "fake.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-pix_fmt", "yuv420p",
            "-y",
            str(fake_video),
        ],
        check=True,
        capture_output=True,
    )

    cache_root = tmp_path / "cache"
    monkeypatch.setattr(rm, "CACHE_DIR", cache_root)
    monkeypatch.setattr(db_module, "DB_PATH", test_db)

    thumbs = cache_root / "thumbs"
    previews = cache_root / "previews"
    videos = cache_root / "videos"
    for d in (thumbs, previews, videos):
        d.mkdir(parents=True, exist_ok=True)

    filename = "VID_20260610_140921.mp4"
    safe = quote(filename, safe="")

    # 模拟磁盘满导致的半成功：缩略图生成成功，但视频缓存缺失
    shutil.copy(str(fake_video), str(videos / safe))
    # 故意不创建预览图，让数据库看起来是 processed=1
    thumb = thumbs / f"{safe}_200x200.jpg"
    thumb.write_bytes(b"")

    db = sqlite3.connect(test_db)
    db.execute(
        "INSERT INTO media_files (filename, file_type, file_size, md5, date, time, "
        "baidu_date, processed, processed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (filename, "video", 12345, "md5", "2026-06-10", "14:09", "2026-06-10", 1, "2026-06-10T00:00:00"),
    )
    db.commit()
    db.close()

    rm.repair_media_database()

    db = sqlite3.connect(test_db)
    cursor = db.execute("SELECT processed FROM media_files WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    db.close()

    assert row is not None
    assert row[0] == 0
    # 缩略图残片应被清理
    assert not thumb.exists()
    # 视频缓存完整，应保留
    assert (videos / safe).exists()
