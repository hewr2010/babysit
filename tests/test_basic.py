"""基本功能测试"""
import pytest
import sys
sys.path.insert(0, '/Users/hwr/storage/babysit')

from babysit.utils import calculate_age
from babysit.baidu import get_exif_cache, save_exif_cache, extract_datetime_from_filename


def test_calculate_age():
    """测试年龄计算"""
    # 测试正常情况
    assert calculate_age("2024-01-01") >= 0
    # 测试空值
    assert calculate_age(None) is None
    assert calculate_age("") is None


def test_cache_operations(tmp_path, monkeypatch):
    """测试缓存操作"""
    import babysit.config as config
    
    # 使用临时缓存目录
    test_cache = tmp_path / "cache"
    test_cache.mkdir()
    monkeypatch.setattr(config, "CACHE_DIR", test_cache)
    
    # 测试 EXIF 缓存
    cache_data = {'test.jpg': {'date': '2025-01-01', 'time': '12:00'}}
    save_exif_cache(cache_data)
    
    loaded = get_exif_cache()
    assert 'test.jpg' in loaded
    assert loaded['test.jpg']['date'] == '2025-01-01'


def test_filename_parsing():
    """测试文件名日期解析"""
    # 测试标准格式
    date, time = extract_datetime_from_filename("2026-03-01 101239.jpg")
    assert date == "2026-03-01"
    assert time == "10:12"
    
    # 测试 IMG_ 格式
    date, time = extract_datetime_from_filename("IMG_20251220_100715.jpg")
    assert date == "2025-12-20"
    assert time == "10:07"
    
    # 测试 video_ 格式
    date, time = extract_datetime_from_filename("video_20260210_105828.mp4")
    assert date == "2026-02-10"
    assert time == "10:58"
    
    # 测试 mmexport 格式
    date, time = extract_datetime_from_filename("mmexport1764123257729.jpg")
    assert date is not None
    
    # 测试无法识别的格式
    date, time = extract_datetime_from_filename("unknown.jpg")
    assert date is None
    assert time is None


def test_processing_status():
    """测试处理状态追踪"""
    from babysit.baidu import set_processing_status, get_processing_status, register_sse_client, unregister_sse_client
    
    # 设置状态
    set_processing_status("test.jpg", "thumb_200", "processing")
    set_processing_status("test.jpg", "thumb_800", "pending")
    
    # 获取状态
    status = get_processing_status("test.jpg")
    assert status["thumb_200"] == "processing"
    assert status["thumb_800"] == "pending"
    
    # 更新状态
    set_processing_status("test.jpg", "thumb_200", "done")
    status = get_processing_status("test.jpg")
    assert status["thumb_200"] == "done"
    
    # 测试 SSE 客户端注册/注销
    import queue
    client = register_sse_client()
    assert isinstance(client, queue.Queue)
    unregister_sse_client(client)


def test_media_status_api():
    """测试媒体状态 API"""
    from babysit.app import create_app
    
    app = create_app()
    with app.test_client() as client:
        # 测试媒体状态 API
        response = client.get('/api/media/status/test.jpg')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
