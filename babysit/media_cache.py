import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from .config import CACHE_DIR, DB_PATH

VIDEO_EXTS = (".mp4", ".mov", ".livp")
DEFAULT_MAX_BYTES = 5 * 1024**3


def _db_path(db_path=None):
    return Path(db_path or DB_PATH)


def _cache_dir(cache_dir=None):
    return Path(cache_dir or CACHE_DIR)


def _connect(db_path=None):
    db = sqlite3.connect(_db_path(db_path), timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    return db


def init_media_cache(db_path=None):
    db = _connect(db_path)
    try:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS media_cache (
                filename TEXT PRIMARY KEY,
                preview_bytes INTEGER NOT NULL DEFAULT 0,
                video_bytes INTEGER NOT NULL DEFAULT 0,
                preview_last_access REAL,
                video_last_access REAL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS media_warm_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                kind TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                client_id TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                error TEXT,
                progress REAL,
                stage TEXT,
                playback_ready INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_warm_jobs_queue
            ON media_warm_jobs(status, priority DESC, id);
            CREATE INDEX IF NOT EXISTS idx_warm_jobs_filename
            ON media_warm_jobs(filename, kind, id DESC);
            CREATE TABLE IF NOT EXISTS media_warm_clients (
                client_id TEXT PRIMARY KEY,
                generation INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS download_url_cache (
                filename TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                expires REAL NOT NULL
            );
            """
        )
        columns = {row[1] for row in db.execute("PRAGMA table_info(media_warm_jobs)")}
        for name, definition in (
            ("progress", "REAL"),
            ("stage", "TEXT"),
            ("playback_ready", "INTEGER NOT NULL DEFAULT 0"),
        ):
            if name not in columns:
                db.execute(f"ALTER TABLE media_warm_jobs ADD COLUMN {name} {definition}")
        db.execute(
            "UPDATE media_warm_jobs SET status = 'queued', updated_at = ? "
            "WHERE status = 'processing'",
            (time.time(),),
        )
        db.commit()
    finally:
        db.close()


def preview_path(filename, cache_dir=None):
    return _cache_dir(cache_dir) / "previews" / f"{quote(filename, safe='')}_800x800.jpg"


def thumbnail_path(filename, cache_dir=None):
    return _cache_dir(cache_dir) / "thumbs" / f"{quote(filename, safe='')}_200x200.jpg"


def video_candidates(filename, cache_dir=None):
    root = _cache_dir(cache_dir) / "videos"
    safe_name = quote(filename, safe="")
    ext = Path(filename).suffix.lower()
    if ext == ".livp":
        return [root / f"{safe_name}.mp4", root / f"{safe_name}.mov"]
    if ext == ".mov":
        return [root / f"{safe_name}.mp4", root / safe_name]
    return [root / safe_name]


def video_output_path(filename, cache_dir=None):
    return video_candidates(filename, cache_dir)[0]


def partial_video_path(filename, cache_dir=None):
    output = video_output_path(filename, cache_dir)
    return output.with_name(f".{output.name}.stream.mp4")


def existing_video_path(filename, cache_dir=None):
    for path in video_candidates(filename, cache_dir):
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


VIDEO_CACHE_VERSION = 2


def video_metadata_path(video_path):
    video_path = Path(video_path)
    return video_path.with_name(f".{video_path.name}.json")


def mark_video_cache_current(video_path):
    metadata_path = video_metadata_path(video_path)
    temp_path = metadata_path.with_name(f"{metadata_path.name}.{os.getpid()}.partial")
    try:
        temp_path.write_text(json.dumps({"version": VIDEO_CACHE_VERSION}))
        os.replace(temp_path, metadata_path)
    finally:
        temp_path.unlink(missing_ok=True)


def video_asset_is_ready(filename, cache_dir=None):
    video_path = existing_video_path(filename, cache_dir)
    if not video_path:
        return False
    try:
        metadata = json.loads(video_metadata_path(video_path).read_text())
        if metadata.get("version") != VIDEO_CACHE_VERSION:
            return False
    except (OSError, ValueError, AttributeError):
        return False
    return video_file_is_valid(video_path)


def _file_size(path):
    return path.stat().st_size if path and path.is_file() else 0


_VIDEO_VALIDATION_CACHE = {}


def video_file_is_valid(path):
    if not path:
        return False
    path = Path(path)
    try:
        stat = path.stat()
        key = (str(path), stat.st_mtime_ns, stat.st_size)
        if key in _VIDEO_VALIDATION_CACHE:
            return _VIDEO_VALIDATION_CACHE[key]
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=pix_fmt:format=duration", "-of", "json", str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            valid = False
        else:
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            duration = float(data.get("format", {}).get("duration", 0))
            valid = bool(streams and streams[0].get("pix_fmt") and duration > 0)
        _VIDEO_VALIDATION_CACHE[key] = valid
        return valid
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def image_assets_ready(filename, cache_dir=None):
    return (
        _file_size(thumbnail_path(filename, cache_dir)) > 0
        and _file_size(preview_path(filename, cache_dir)) > 0
    )


def record_cache_assets(filename, cache_dir=None, db_path=None):
    preview_size = _file_size(preview_path(filename, cache_dir))
    video_size = _file_size(existing_video_path(filename, cache_dir))
    db = _connect(db_path)
    try:
        db.execute(
            """
            INSERT INTO media_cache
                (filename, preview_bytes, video_bytes, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                preview_bytes = excluded.preview_bytes,
                video_bytes = excluded.video_bytes,
                updated_at = excluded.updated_at
            """,
            (filename, preview_size, video_size, time.time()),
        )
        db.commit()
    finally:
        db.close()
    return {"preview_bytes": preview_size, "video_bytes": video_size}


def touch_media_access(filename, kind, cache_dir=None, db_path=None):
    if kind not in ("preview", "video"):
        return
    record_cache_assets(filename, cache_dir, db_path)
    column = f"{kind}_last_access"
    db = _connect(db_path)
    try:
        db.execute(
            f"UPDATE media_cache SET {column} = ?, updated_at = ? WHERE filename = ?",
            (time.time(), time.time(), filename),
        )
        db.commit()
    finally:
        db.close()


def update_warm_job_progress(job_id, progress=None, stage=None, playback_ready=None, db_path=None):
    assignments = ["updated_at = ?"]
    values = [time.time()]
    for column, value in (("progress", progress), ("stage", stage), ("playback_ready", playback_ready)):
        if value is not None:
            assignments.append(f"{column} = ?")
            values.append(value)
    values.append(job_id)
    db = _connect(db_path)
    try:
        db.execute(
            f"UPDATE media_warm_jobs SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        db.commit()
    finally:
        db.close()


def _latest_job(db, filename, kind):
    return db.execute(
        """
        SELECT * FROM media_warm_jobs
        WHERE filename = ? AND kind = ?
        ORDER BY id DESC LIMIT 1
        """,
        (filename, kind),
    ).fetchone()


def get_warm_job_error(filename, kind, db_path=None):
    db = _connect(db_path)
    try:
        job = _latest_job(db, filename, kind)
        return job["error"] if job else None
    finally:
        db.close()


def get_media_status(filename, cache_dir=None, db_path=None):
    preview_ready = image_assets_ready(filename, cache_dir)
    is_video = Path(filename).suffix.lower() in VIDEO_EXTS
    video_ready = video_asset_is_ready(filename, cache_dir)
    db = _connect(db_path)
    try:
        kind = "video" if is_video else "preview"
        job = _latest_job(db, filename, kind)
    finally:
        db.close()
    ready = video_ready if is_video else preview_ready
    state = "ready" if ready else "cold"
    if not ready and job and job["status"] in ("queued", "processing", "streaming"):
        state = "processing" if job["status"] == "streaming" else job["status"]
        if (
            is_video
            and job["status"] in ("processing", "streaming")
            and job["playback_ready"]
            and video_file_is_valid(partial_video_path(filename, cache_dir))
        ):
            state = "streaming"
    elif not ready and job and job["status"] == "error":
        state = "error"
    return {
        "filename": filename,
        "type": "video" if is_video else "photo",
        "state": state,
        "preview_ready": preview_ready,
        "video_ready": video_ready if is_video else None,
        "job": dict(job) if job else None,
    }


def enqueue_warm(
    filename,
    client_id,
    neighbors=(),
    generation=1,
    include_current=True,
    include_neighbor_videos=False,
    current_kind=None,
    current_priority=100,
    cache_dir=None,
    db_path=None,
):
    is_video = Path(filename).suffix.lower() in VIDEO_EXTS
    requested = []
    if include_current:
        requested.append((filename, current_kind or ("video" if is_video else "preview"), current_priority))
    requested.extend(
        (
            name,
            "video" if include_neighbor_videos and Path(name).suffix.lower() in VIDEO_EXTS else "preview",
            30,
        )
        for name in neighbors if name != filename
    )
    requested_keys = {(name, kind) for name, kind, _ in requested}
    now = time.time()
    db = _connect(db_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        client = db.execute(
            "SELECT generation FROM media_warm_clients WHERE client_id = ?", (client_id,)
        ).fetchone()
        if client and generation < client["generation"]:
            db.commit()
            return get_media_status(filename, cache_dir, db_path)
        db.execute(
            "INSERT INTO media_warm_clients (client_id, generation) VALUES (?, ?) "
            "ON CONFLICT(client_id) DO UPDATE SET generation = excluded.generation",
            (client_id, generation),
        )
        queued = db.execute(
            "SELECT id, filename, kind FROM media_warm_jobs "
            "WHERE client_id = ? AND status = 'queued'",
            (client_id,),
        ).fetchall()
        for job in queued:
            if (job["filename"], job["kind"]) not in requested_keys:
                db.execute(
                    "UPDATE media_warm_jobs SET status = 'cancelled', updated_at = ? WHERE id = ?",
                    (now, job["id"]),
                )
        for name, kind, priority in requested:
            ready = (
                video_asset_is_ready(name, cache_dir)
                if kind == "video"
                else image_assets_ready(name, cache_dir)
            )
            if ready:
                continue
            active = db.execute(
                """
                SELECT id, priority FROM media_warm_jobs
                WHERE filename = ? AND kind = ? AND status IN ('queued', 'processing')
                ORDER BY id DESC LIMIT 1
                """,
                (name, kind),
            ).fetchone()
            if active:
                db.execute(
                    "UPDATE media_warm_jobs SET priority = ?, client_id = ?, "
                    "status = CASE WHEN status = 'queued' THEN 'queued' ELSE status END, "
                    "updated_at = ? WHERE id = ?",
                    (max(priority, active["priority"]), client_id, now, active["id"]),
                )
            else:
                db.execute(
                    """
                    INSERT INTO media_warm_jobs
                        (filename, kind, priority, client_id, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'queued', ?, ?)
                    """,
                    (name, kind, priority, client_id, now, now),
                )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return get_media_status(filename, cache_dir, db_path)


def original_livp_path(filename, cache_dir=None):
    return _cache_dir(cache_dir) / "livp_original" / f"{quote(filename, safe='')}.mov"


def _job_output_ready(job, cache_dir=None):
    if job["kind"] == "original_livp":
        return _file_size(original_livp_path(job["filename"], cache_dir)) > 0
    if job["kind"] == "video":
        return video_asset_is_ready(job["filename"], cache_dir)
    return image_assets_ready(job["filename"], cache_dir)


def enqueue_original_livp(filename, cache_dir=None, db_path=None):
    if _file_size(original_livp_path(filename, cache_dir)) > 0:
        return {"state": "ready"}
    now = time.time()
    db = _connect(db_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        active = db.execute(
            "SELECT id FROM media_warm_jobs WHERE filename = ? AND kind = 'original_livp' "
            "AND status IN ('queued', 'processing') ORDER BY id DESC LIMIT 1",
            (filename,),
        ).fetchone()
        if not active:
            db.execute(
                "INSERT INTO media_warm_jobs "
                "(filename, kind, priority, client_id, status, created_at, updated_at) "
                "VALUES (?, 'original_livp', 100, 'native-download', 'queued', ?, ?)",
                (filename, now, now),
            )
        db.commit()
    finally:
        db.close()
    return get_original_livp_status(filename, cache_dir, db_path)


def get_original_livp_status(filename, cache_dir=None, db_path=None):
    if _file_size(original_livp_path(filename, cache_dir)) > 0:
        return {"state": "ready"}
    db = _connect(db_path)
    try:
        job = _latest_job(db, filename, "original_livp")
    finally:
        db.close()
    if job and job["status"] in ("queued", "processing", "error"):
        return {"state": job["status"], "job": dict(job)}
    return {"state": "cold", "job": dict(job) if job else None}


def has_queued_warm_job(db_path=None):
    db = _connect(db_path)
    try:
        return db.execute(
            "SELECT 1 FROM media_warm_jobs WHERE status = 'queued' LIMIT 1"
        ).fetchone() is not None
    finally:
        db.close()


def claim_next_warm_job(cache_dir=None, db_path=None, min_priority=None, max_priority=None):
    db = _connect(db_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        conditions = ["status = 'queued'"]
        params = []
        if min_priority is not None:
            conditions.append("priority >= ?")
            params.append(min_priority)
        if max_priority is not None:
            conditions.append("priority <= ?")
            params.append(max_priority)
        where = " AND ".join(conditions)
        while True:
            job = db.execute(
                f"SELECT * FROM media_warm_jobs WHERE {where} "
                "ORDER BY priority DESC, id LIMIT 1",
                params,
            ).fetchone()
            if not job:
                db.commit()
                return None
            ready = _job_output_ready(job, cache_dir)
            now = time.time()
            db.execute(
                "UPDATE media_warm_jobs SET status = ?, updated_at = ? WHERE id = ?",
                ("ready" if ready else "processing", now, job["id"]),
            )
            db.commit()
            if not ready:
                claimed = dict(job)
                claimed["status"] = "processing"
                return claimed
            db.execute("BEGIN IMMEDIATE")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def finish_warm_job(job_id, error=None, cache_dir=None, db_path=None):
    db = _connect(db_path)
    try:
        row = db.execute(
            "SELECT filename, kind FROM media_warm_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if not row:
            return
        ready = _job_output_ready(row, cache_dir)
        status = "ready" if ready else "error"
        db.execute(
            "UPDATE media_warm_jobs SET status = ?, error = ?, updated_at = ? WHERE id = ?",
            (status, None if ready else (error or "缓存文件未生成"), time.time(), job_id),
        )
        db.commit()
    finally:
        db.close()


def _cache_limits():
    max_bytes = int(os.environ.get("BABYSIT_CACHE_MAX_BYTES", DEFAULT_MAX_BYTES))
    high_ratio = float(os.environ.get("BABYSIT_CACHE_HIGH_WATERMARK", "0.85"))
    low_ratio = float(os.environ.get("BABYSIT_CACHE_LOW_WATERMARK", "0.70"))
    if max_bytes <= 0 or not 0 < low_ratio < high_ratio <= 1:
        raise ValueError("缓存容量或水位配置无效")
    return max_bytes, int(max_bytes * high_ratio), int(max_bytes * low_ratio)


def enforce_cache_budget(
    required_bytes=0, now=None, dry_run=False, cache_dir=None, db_path=None
):
    max_bytes, high_watermark, low_watermark = _cache_limits()
    max_items = int(os.environ.get("BABYSIT_CACHE_MAX_ITEMS", "0"))
    disable_protection = os.environ.get("BABYSIT_CACHE_DISABLE_PROTECTION") == "1"
    now = now or time.time()
    cutoff = (datetime.fromtimestamp(now) - timedelta(days=30)).date().isoformat()
    db = _connect(db_path)
    deleted = []
    try:
        rows = db.execute(
            """
            SELECT mf.filename, mf.date, mf.file_type,
                   mc.preview_last_access, mc.video_last_access,
                   EXISTS(
                       SELECT 1 FROM milestones m WHERE m.media_filename = mf.filename
                   ) AS is_milestone
            FROM media_files mf
            LEFT JOIN media_cache mc ON mc.filename = mf.filename
            WHERE mf.processed = 1
            """
        ).fetchall()
        assets = []
        usage = 0
        for row in rows:
            paths = [("preview", preview_path(row["filename"], cache_dir))]
            if row["file_type"] == "video":
                paths.append(("video", existing_video_path(row["filename"], cache_dir)))
            for kind, path in paths:
                size = _file_size(path)
                if not size:
                    continue
                usage += size
                last_access = row[f"{kind}_last_access"] or path.stat().st_mtime
                protected = (
                    row["date"] >= cutoff
                    or (kind == "preview" and row["is_milestone"])
                    or last_access >= now - 600
                )
                assets.append(
                    {
                        "filename": row["filename"],
                        "kind": kind,
                        "path": path,
                        "bytes": size,
                        "last_access": last_access,
                        "protected": protected and not disable_protection,
                    }
                )

        def evict(asset):
            nonlocal usage
            deleted.append({k: asset[k] for k in ("filename", "kind", "bytes")})
            usage -= asset["bytes"]
            if not dry_run:
                try:
                    asset["path"].unlink()
                    if asset["kind"] == "video":
                        video_metadata_path(asset["path"]).unlink(missing_ok=True)
                except FileNotFoundError:
                    pass

        if max_items > 0:
            items = {}
            for asset in assets:
                item = items.setdefault(asset["filename"], {"last_access": 0})
                item["last_access"] = max(item["last_access"], asset["last_access"])
            keep = set(
                sorted(items, key=lambda name: items[name]["last_access"], reverse=True)[
                    :max_items
                ]
            )
            for asset in assets:
                if asset["filename"] not in keep:
                    evict(asset)
            assets = [asset for asset in assets if asset["filename"] in keep]

        target = low_watermark
        if required_bytes:
            target = min(target, max_bytes - required_bytes)
        if usage + required_bytes <= high_watermark:
            if not dry_run and deleted:
                for item in deleted:
                    column = f"{item['kind']}_bytes"
                    db.execute(
                        f"UPDATE media_cache SET {column} = 0, updated_at = ? WHERE filename = ?",
                        (now, item["filename"]),
                    )
                db.commit()
            return {"usage": usage, "deleted": deleted, "target": target, "within_budget": True}
        candidates = sorted(
            (asset for asset in assets if not asset["protected"]),
            key=lambda asset: asset["last_access"],
        )
        for asset in candidates:
            if usage + required_bytes <= target:
                break
            evict(asset)
        if not dry_run and deleted:
            for item in deleted:
                column = f"{item['kind']}_bytes"
                db.execute(
                    f"UPDATE media_cache SET {column} = 0, updated_at = ? WHERE filename = ?",
                    (now, item["filename"]),
                )
            db.commit()
        return {
            "usage": usage,
            "deleted": deleted,
            "target": target,
            "within_budget": usage + required_bytes <= max_bytes,
        }
    finally:
        db.close()
