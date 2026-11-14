import os
import sqlite3
import time
from datetime import datetime, timedelta

import pytest

import babysit.db as db_module
import babysit.media_cache as cache_module
from babysit.db import init_db
from babysit.media_cache import (
    claim_next_warm_job,
    enforce_cache_budget,
    enqueue_warm,
    finish_warm_job,
    get_media_status,
    init_media_cache,
    mark_video_cache_current,
    original_livp_path,
    partial_video_path,
    preview_path,
    thumbnail_path,
    update_warm_job_progress,
    video_output_path,
)


@pytest.fixture
def media_env(tmp_path, monkeypatch):
    db_path = tmp_path / "babysit.db"
    cache_dir = tmp_path / "cache"
    for directory in ("thumbs", "previews", "videos", "temp_video"):
        (cache_dir / directory).mkdir(parents=True)
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    monkeypatch.setattr(cache_module, "DB_PATH", db_path)
    monkeypatch.setattr(cache_module, "CACHE_DIR", cache_dir)
    init_db()
    init_media_cache(db_path)
    return db_path, cache_dir


def add_media(db_path, filename, file_type="photo", date="2026-01-01", milestone=False):
    db = sqlite3.connect(db_path)
    db.execute(
        "INSERT INTO media_files "
        "(filename, file_type, file_size, md5, date, time, processed) "
        "VALUES (?, ?, 1000, ?, ?, '10:00', 1)",
        (filename, file_type, f"md5-{filename}", date),
    )
    if milestone:
        db.execute(
            "INSERT INTO milestones (media_filename, title) VALUES (?, ?)",
            (filename, "重要时刻"),
        )
    db.commit()
    db.close()
    thumb = thumbnail_path(filename)
    thumb.parent.mkdir(parents=True, exist_ok=True)
    thumb.write_bytes(b"thumb")


def write_test_video(path):
    import subprocess

    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=8",
         "-pix_fmt", "yuv420p", "-y", str(path)],
        check=True,
        capture_output=True,
    )


def jobs(db_path):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT filename, kind, priority, status FROM media_warm_jobs ORDER BY id"
    ).fetchall()
    db.close()
    return [dict(row) for row in rows]


def test_stale_warm_request_cannot_reorder_queue(media_env):
    db_path, _ = media_env
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        add_media(db_path, name)

    enqueue_warm("a.jpg", "client", ["b.jpg"], generation=1)
    enqueue_warm("b.jpg", "client", ["c.jpg"], generation=2)
    enqueue_warm("a.jpg", "client", [], generation=1)

    current_jobs = [job for job in jobs(db_path) if job["status"] == "queued"]
    assert {(job["filename"], job["kind"]) for job in current_jobs} == {
        ("b.jpg", "preview"),
        ("c.jpg", "preview"),
    }
    assert next(job for job in current_jobs if job["filename"] == "b.jpg")["priority"] == 100


def test_cold_video_only_downloads_after_explicit_request(media_env):
    db_path, _ = media_env
    add_media(db_path, "video.mp4", "video")
    add_media(db_path, "neighbor.jpg")

    status = enqueue_warm(
        "video.mp4",
        "client",
        ["neighbor.jpg"],
        generation=1,
        include_current=False,
    )
    assert status["state"] == "cold"
    assert [(job["filename"], job["kind"]) for job in jobs(db_path)] == [
        ("neighbor.jpg", "preview")
    ]

    enqueue_warm(
        "video.mp4",
        "client",
        ["neighbor.jpg"],
        generation=2,
        include_current=True,
    )
    current_jobs = [job for job in jobs(db_path) if job["status"] == "queued"]
    assert ("video.mp4", "video") in {
        (job["filename"], job["kind"]) for job in current_jobs
    }


def test_lru_preserves_hot_milestones_and_permanent_thumbs(media_env, monkeypatch):
    db_path, cache_dir = media_env
    today = datetime.now().date()
    old_date = (today - timedelta(days=60)).isoformat()
    add_media(db_path, "cold.mp4", "video", old_date)
    add_media(db_path, "hot.mp4", "video", today.isoformat())
    add_media(db_path, "milestone.jpg", date=old_date, milestone=True)
    for name in ("cold.mp4", "hot.mp4", "milestone.jpg"):
        preview_path(name).write_bytes(b"x" * 100)
    for name in ("cold.mp4", "hot.mp4"):
        video_output_path(name).write_bytes(b"x" * 200)
    for path in (preview_path("cold.mp4"), video_output_path("cold.mp4")):
        os.utime(path, (time.time() - 3600, time.time() - 3600))
    monkeypatch.setenv("BABYSIT_CACHE_MAX_BYTES", "1000")
    monkeypatch.setenv("BABYSIT_CACHE_HIGH_WATERMARK", "0.8")
    monkeypatch.setenv("BABYSIT_CACHE_LOW_WATERMARK", "0.7")

    result = enforce_cache_budget(required_bytes=500)

    assert result["within_budget"] is True
    assert not preview_path("cold.mp4").exists()
    assert not video_output_path("cold.mp4").exists()
    assert preview_path("hot.mp4").exists()
    assert video_output_path("hot.mp4").exists()
    assert preview_path("milestone.jpg").exists()
    assert thumbnail_path("cold.mp4").exists()
    assert get_media_status("cold.mp4")["state"] == "cold"


def test_lru_dry_run_does_not_delete(media_env, monkeypatch):
    db_path, _ = media_env
    old_date = (datetime.now() - timedelta(days=60)).date().isoformat()
    add_media(db_path, "cold.jpg", date=old_date)
    preview_path("cold.jpg").write_bytes(b"x" * 900)
    os.utime(preview_path("cold.jpg"), (time.time() - 3600, time.time() - 3600))
    monkeypatch.setenv("BABYSIT_CACHE_MAX_BYTES", "1000")

    result = enforce_cache_budget(dry_run=True)

    assert result["deleted"]
    assert preview_path("cold.jpg").exists()


def test_refresh_does_not_refill_evicted_assets(media_env, monkeypatch):
    import babysit.refresh_media as refresh

    db_path, cache_dir = media_env
    add_media(db_path, "cold.jpg")
    monkeypatch.setattr(refresh, "CACHE_DIR", cache_dir)

    class Result:
        returncode = 0
        stdout = f"F cold.jpg 1000 2026-01-01, 10:00:00 md5-cold.jpg"
        stderr = ""

    monkeypatch.setattr(refresh, "run_bypy", lambda command: Result())
    monkeypatch.setattr(
        refresh,
        "process_media_file",
        lambda *args, **kwargs: pytest.fail("冷缓存不应在例行刷新时重新下载"),
    )

    refresh.refresh_media()
    assert get_media_status("cold.jpg")["state"] == "cold"


def test_refresh_restores_missing_hot_assets(media_env, monkeypatch):
    import babysit.refresh_media as refresh

    db_path, cache_dir = media_env
    today = datetime.now().date().isoformat()
    add_media(db_path, "hot.mp4", "video", today)
    monkeypatch.setattr(refresh, "CACHE_DIR", cache_dir)

    class Result:
        returncode = 0
        stdout = f"F hot.mp4 1000 {today}, 10:00:00 md5-hot.mp4"
        stderr = ""

    calls = []

    def process(file_info, *args, **kwargs):
        calls.append(kwargs["include_video"])
        file_info["processed"] = True
        return True, file_info

    monkeypatch.setattr(refresh, "run_bypy", lambda command: Result())
    monkeypatch.setattr(refresh, "process_media_file", process)

    refresh.refresh_media()
    assert calls == [True]


def test_preview_only_processing_does_not_cache_video(media_env, monkeypatch, tmp_path):
    import shutil
    import subprocess
    import babysit.refresh_media as refresh

    db_path, cache_dir = media_env
    source = tmp_path / "source.mp4"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
         "-pix_fmt", "yuv420p", "-y", str(source)],
        check=True,
        capture_output=True,
    )
    monkeypatch.setattr(refresh, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(refresh, "get_download_url", lambda filename: ("http://test", None))
    monkeypatch.setattr(
        refresh,
        "_download_to_file",
        lambda url, destination, timeout=120, job_id=None: (
            (shutil.copy(source, destination), True, None)[1:]
        ),
    )
    info = {
        "name": "old.mov",
        "type": "video",
        "size": source.stat().st_size,
        "date": "2026-01-01",
        "time": "10:00",
    }

    success, _ = refresh.process_media_file(
        info,
        cache_dir / "thumbs",
        cache_dir / "previews",
        cache_dir / "videos",
        include_video=False,
    )

    assert success is True
    assert preview_path("old.mov").exists()
    assert not video_output_path("old.mov").exists()


def test_mov_is_saved_as_compressed_mp4(media_env, monkeypatch, tmp_path):
    import shutil
    import subprocess
    import babysit.refresh_media as refresh

    db_path, cache_dir = media_env
    source = tmp_path / "source.mov"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=8",
         "-pix_fmt", "yuv420p", "-y", str(source)],
        check=True,
        capture_output=True,
    )
    monkeypatch.setattr(refresh, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(refresh, "get_download_url", lambda filename: ("http://test", None))
    monkeypatch.setattr(
        refresh,
        "_download_to_file",
        lambda url, destination, timeout=120, job_id=None: (
            (shutil.copy(source, destination), True, None)[1:]
        ),
    )
    info = {
        "name": "hot.mov",
        "type": "video",
        "size": source.stat().st_size,
        "date": datetime.now().date().isoformat(),
        "time": "10:00",
    }

    success, _ = refresh.process_media_file(
        info, cache_dir / "thumbs", cache_dir / "previews", cache_dir / "videos"
    )

    output = video_output_path("hot.mov")
    assert success is True
    assert output.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=codec_name,pix_fmt", "-of", "json", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"codec_name": "h264"' in probe.stdout
    assert '"pix_fmt": "yuv420p"' in probe.stdout


def test_cold_preview_request_recovers_on_backend(media_env, monkeypatch):
    import babysit.app as app_module

    db_path, cache_dir = media_env
    add_media(db_path, "cold.jpg")
    add_media(db_path, "neighbor.jpg")
    monkeypatch.setattr(app_module, "CACHE_DIR", cache_dir)
    client = app_module.create_app().test_client()
    calls = []

    def recover(filename, client_id, neighbors, **kwargs):
        calls.append((filename, client_id, neighbors, kwargs))
        result = enqueue_warm(
            filename,
            client_id,
            neighbors,
            generation=kwargs["generation"],
            include_neighbor_videos=kwargs["include_neighbor_videos"],
        )
        preview_path(filename).write_bytes(b"preview")
        return result

    monkeypatch.setattr(app_module, "enqueue_warm", recover)
    response = client.get("/preview/cold.jpg")

    assert response.status_code == 200
    assert response.data == b"preview"
    assert calls[0][0] == "cold.jpg"
    assert calls[0][1] == "native-preview"
    assert calls[0][2] == ["neighbor.jpg"]
    assert calls[0][3]["include_neighbor_videos"] is False


def test_missing_thumbnail_is_not_ready_even_with_preview(media_env):
    db_path, _ = media_env
    add_media(db_path, "cold.jpg")
    thumbnail_path("cold.jpg").unlink()
    preview_path("cold.jpg").write_bytes(b"preview")
    enqueue_warm("cold.jpg", "client", generation=1)

    assert get_media_status("cold.jpg")["state"] == "queued"
    job = claim_next_warm_job()
    assert job["status"] == "processing"


def test_cold_thumbnail_request_recovers_real_image(media_env, monkeypatch):
    import babysit.app as app_module

    db_path, cache_dir = media_env
    add_media(db_path, "cold.jpg")
    monkeypatch.setattr(app_module, "CACHE_DIR", cache_dir)
    client = app_module.create_app().test_client()
    thumbnail_path("cold.jpg").unlink()

    def recover(filename, client_id, neighbors, **kwargs):
        result = enqueue_warm(
            filename,
            client_id,
            neighbors,
            generation=kwargs["generation"],
            include_neighbor_videos=kwargs["include_neighbor_videos"],
        )
        thumbnail_path(filename).write_bytes(b"real-thumbnail")
        preview_path(filename).write_bytes(b"preview")
        return result

    monkeypatch.setattr(app_module, "enqueue_warm", recover)
    response = client.get("/thumb/cold.jpg")

    assert response.status_code == 200
    assert response.data == b"real-thumbnail"


def test_thumbnail_can_be_generated_from_existing_preview(media_env):
    import babysit.refresh_media as refresh
    from PIL import Image

    db_path, cache_dir = media_env
    preview_path("video.mp4").parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (800, 600), "#336699").save(preview_path("video.mp4"), "JPEG")
    assert refresh.process_preview_from_existing("video.mp4") is True
    with Image.open(thumbnail_path("video.mp4")) as thumbnail:
        assert max(thumbnail.size) <= 200


def test_invalid_video_is_not_used_for_preview(media_env):
    import babysit.refresh_media as refresh

    db_path, cache_dir = media_env
    video_output_path("broken.mp4").write_bytes(b"not-a-real-video")
    assert refresh.video_file_is_valid(video_output_path("broken.mp4")) is False
    assert refresh.process_preview_from_existing("broken.mp4") is False
    enqueue_warm("broken.mp4", "client", generation=1)
    job = claim_next_warm_job()
    assert job["kind"] == "video"
    assert job["status"] == "processing"


def test_video_with_cache_but_missing_thumbnail_uses_preview_job(media_env, monkeypatch):
    import babysit.app as app_module

    db_path, cache_dir = media_env
    add_media(db_path, "video.mp4", "video")
    video_output_path("video.mp4").write_bytes(b"full-video")
    thumbnail_path("video.mp4").unlink()
    monkeypatch.setattr(app_module, "CACHE_DIR", cache_dir)
    client = app_module.create_app().test_client()
    kinds = []

    def recover(filename, client_id, neighbors, **kwargs):
        kinds.append(kwargs["current_kind"])
        result = enqueue_warm(
            filename,
            client_id,
            neighbors,
            generation=kwargs["generation"],
            include_neighbor_videos=kwargs["include_neighbor_videos"],
            current_kind=kwargs["current_kind"],
        )
        thumbnail_path(filename).write_bytes(b"video-thumbnail")
        return result

    monkeypatch.setattr(app_module, "enqueue_warm", recover)
    response = client.get("/thumb/video.mp4")

    assert response.status_code == 200
    assert response.data == b"video-thumbnail"
    assert kinds == ["preview"]


def test_streaming_partial_video_status_and_route(media_env, monkeypatch):
    import babysit.app as app_module

    db_path, cache_dir = media_env
    add_media(db_path, "large.mp4", "video")
    monkeypatch.setattr(app_module, "CACHE_DIR", cache_dir)
    client = app_module.create_app().test_client()
    enqueue_warm("large.mp4", "client", generation=1)
    job = claim_next_warm_job()
    write_test_video(partial_video_path("large.mp4"))
    update_warm_job_progress(job["id"], progress=5, stage="转码", playback_ready=1)

    assert get_media_status("large.mp4")["state"] == "streaming"
    finish_warm_job(job["id"])
    # 流式响应在任务存活期间保持打开；mock 掉路由内的 enqueue 避免重建任务
    monkeypatch.setattr(app_module, "enqueue_warm", lambda *args, **kwargs: None)
    response = client.get("/video/large.mp4")
    assert response.status_code == 200
    assert response.data == partial_video_path("large.mp4").read_bytes()

    write_test_video(video_output_path("large.mp4"))
    mark_video_cache_current(video_output_path("large.mp4"))
    assert get_media_status("large.mp4")["state"] == "ready"
    assert client.get("/video/large.mp4").data == video_output_path("large.mp4").read_bytes()


def test_large_video_transcodes_first_segment_without_full_download(media_env, monkeypatch, tmp_path):
    import subprocess
    import babysit.refresh_media as refresh

    db_path, cache_dir = media_env
    source = tmp_path / "large-source.mp4"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=12",
         "-pix_fmt", "yuv420p", "-y", str(source)],
        check=True,
        capture_output=True,
    )
    monkeypatch.setattr(refresh, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(refresh, "get_download_url", lambda filename: (str(source), None))
    monkeypatch.setattr(
        refresh,
        "_download_to_file",
        lambda *args, **kwargs: pytest.fail("大文件直转不应先下载完整原文件"),
    )
    info = {
        "name": "large.mp4",
        "type": "video",
        "size": 6 * 1024 * 1024,
        "date": "2026-01-01",
        "time": "10:00",
    }
    first_play = []

    success, _ = refresh.process_media_file(
        info,
        cache_dir / "thumbs",
        cache_dir / "previews",
        cache_dir / "videos",
        on_first_play=lambda path: first_play.append(path),
        stop_after_first_play=True,
    )

    assert success is True
    assert len(first_play) == 1
    # 短视频（< FIRST_PLAY_STOP_SECONDS）会自然转完并 faststart 落盘；
    # 长视频则在首段后停在 partial。两种形态都必须可播。
    from babysit.media_cache import video_file_is_valid

    final = video_output_path("large.mp4")
    if final.exists():
        assert video_file_is_valid(final)
    else:
        assert first_play[0].exists()


def test_cold_video_request_waits_for_first_playable_segment(media_env, monkeypatch):
    import babysit.app as app_module

    db_path, cache_dir = media_env
    add_media(db_path, "large.mp4", "video")
    monkeypatch.setattr(app_module, "CACHE_DIR", cache_dir)
    client = app_module.create_app().test_client()
    write_test_video(video_output_path(filename="large.mp4"))

    def recover(filename, client_id, neighbors, **kwargs):
        result = enqueue_warm(
            filename,
            client_id,
            neighbors,
            generation=kwargs["generation"],
            include_neighbor_videos=kwargs["include_neighbor_videos"],
        )
        job = claim_next_warm_job()
        write_test_video(partial_video_path(filename))
        update_warm_job_progress(job["id"], progress=5, stage="转码", playback_ready=1)
        # 流式响应在任务存活期间保持打开，测试里直接终结任务让流结束
        finish_warm_job(job["id"], "测试终止")
        return result

    monkeypatch.setattr(app_module, "enqueue_warm", recover)
    response = client.get("/video/large.mp4")

    assert response.status_code == 200
    assert response.data == partial_video_path("large.mp4").read_bytes()


def test_original_livp_is_unpacked_without_transcoding(media_env, monkeypatch):
    import io
    import zipfile
    import babysit.refresh_media as refresh

    db_path, cache_dir = media_env
    original = b"original-mov-bytes"
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("video.mov", original)
    monkeypatch.setattr(refresh, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(refresh, "get_download_url", lambda filename: ("http://test", None))
    monkeypatch.setattr(
        refresh,
        "_download_to_file",
        lambda url, destination, timeout=120, job_id=None: (
            (destination.write_bytes(archive_bytes.getvalue()), True, None)[1:]
        ),
    )

    success = refresh.process_original_livp({"name": "live.livp"})

    assert success is True
    assert original_livp_path("live.livp").read_bytes() == original


def test_legacy_video_cache_is_rebuilt(media_env):
    db_path, _ = media_env
    add_media(db_path, "legacy.mp4", "video")
    output = video_output_path("legacy.mp4")
    write_test_video(output)

    assert get_media_status("legacy.mp4")["state"] == "cold"
    enqueue_warm("legacy.mp4", "client", generation=1)
    assert claim_next_warm_job()["status"] == "processing"

    mark_video_cache_current(output)
    assert get_media_status("legacy.mp4")["state"] == "ready"


def test_landscape_transcode_preserves_aspect_ratio(media_env, tmp_path):
    import json
    import subprocess
    import babysit.refresh_media as refresh

    db_path, cache_dir = media_env
    source = tmp_path / "landscape-source.mp4"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=3840x2160:rate=1",
         "-pix_fmt", "yuv420p", "-y", str(source)],
        check=True,
        capture_output=True,
    )
    output = cache_dir / "videos" / "landscape.mp4"

    assert refresh.transcode_video(source, output) is True

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "json", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    assert (stream["width"], stream["height"]) == (1920, 1080)
    head = output.read_bytes()[:65536]
    boxes = [box for box, *_ in refresh._iter_boxes(head, 0, len(head))]
    assert boxes.index(b"moov") < boxes.index(b"mdat"), "最终产物必须是 faststart"
    assert get_media_status("landscape.mp4")["video_ready"] is True


def test_claim_next_warm_job_priority_bands(media_env):
    db_path, cache_dir = media_env
    add_media(db_path, "current.mp4", "video")
    add_media(db_path, "neighbor.mp4", "video")
    enqueue_warm(
        "current.mp4", "client", ["neighbor.mp4"], generation=1,
        include_neighbor_videos=True,
    )

    job = claim_next_warm_job(min_priority=100)
    assert job["filename"] == "current.mp4"

    job = claim_next_warm_job(max_priority=99)
    assert job["filename"] == "neighbor.mp4"

    assert claim_next_warm_job(min_priority=100) is None


def test_enforce_cache_budget_max_items_keeps_most_recent(media_env, monkeypatch):
    from babysit.media_cache import touch_media_access

    db_path, cache_dir = media_env
    monkeypatch.setenv("BABYSIT_CACHE_MAX_ITEMS", "2")
    monkeypatch.setenv("BABYSIT_CACHE_DISABLE_PROTECTION", "1")
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        add_media(db_path, name, "photo", date="2026-01-01")
        target = preview_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x" * 100)
        touch_media_access(name, "preview")
        time.sleep(0.01)

    report = enforce_cache_budget()

    assert report["within_budget"] is True
    assert {item["filename"] for item in report["deleted"]} == {"a.jpg"}
    assert preview_path("a.jpg").exists() is False
    assert preview_path("b.jpg").exists() is True
    assert preview_path("c.jpg").exists() is True


def test_faststart_snapshot_remuxes_growing_partial(media_env, tmp_path):
    import subprocess
    import babysit.refresh_media as rm
    from babysit.media_cache import partial_video_path

    db_path, cache_dir = media_env
    source = tmp_path / "src.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=20:size=320x240:rate=30",
         "-pix_fmt", "yuv420p", "-c:v", "h264_videotoolbox", "-b:v", "2M",
         "-movflags", "+frag_keyframe+empty_moov+default_base_moof", str(source)],
        check=True, capture_output=True,
    )
    partial = partial_video_path("clip.mov", cache_dir)
    partial.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    partial.write_bytes(data[: len(data) * 3 // 5])

    snapshot = rm._faststart_snapshot(partial, "clip.mov")

    assert snapshot is not None and snapshot.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(snapshot)],
        check=True, capture_output=True, text=True,
    )
    import json
    assert float(json.loads(probe.stdout)["format"]["duration"]) > 5
