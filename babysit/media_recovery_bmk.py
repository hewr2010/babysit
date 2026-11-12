import argparse
import fcntl
import json
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from . import refresh_media as media
from .config import DB_PATH

WORK_DIR = Path(__file__).parent / "data" / "media_recovery_bmk"
SAMPLE_QUERIES = {
    "small_photo": "file_type = 'photo' AND file_size BETWEEN 1000000 AND 6000000 ORDER BY file_size DESC LIMIT 1",
    "large_photo": "file_type = 'photo' AND file_size > 6000000 ORDER BY file_size DESC LIMIT 1",
    "live_photo": "file_type = 'video' AND filename LIKE '%.livp' ORDER BY file_size DESC LIMIT 1",
    "small_video": "file_type = 'video' AND filename NOT LIKE '%.livp' AND file_size < 20000000 ORDER BY file_size DESC LIMIT 1",
    "large_video": "file_type = 'video' AND file_size BETWEEN 40000000 AND 180000000 ORDER BY file_size LIMIT 1",
    "gb_video": "file_type = 'video' AND file_size >= 500000000 ORDER BY file_size DESC LIMIT 1",
}


def select_samples(db_path, categories):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    samples = []
    try:
        for category, query in SAMPLE_QUERIES.items():
            if categories and category not in categories:
                continue
            row = db.execute(f"SELECT * FROM media_files WHERE {query}").fetchone()
            if row:
                samples.append({
                    "category": category,
                    "info": {
                        "name": row["filename"],
                        "type": row["file_type"],
                        "size": row["file_size"],
                        "date": row["date"],
                        "time": row["time"] or "",
                        "baidu_date": row["baidu_date"] or "",
                        "processed": True,
                    },
                })
    finally:
        db.close()
    return samples


def run_directories(category, mode, repeat):
    root = WORK_DIR / "cache" / f"{category}-{mode}-{repeat}"
    if root.exists():
        shutil.rmtree(root)
    for name in ("thumbs", "previews", "videos", "temp_video"):
        (root / name).mkdir(parents=True, exist_ok=True)
    media.CACHE_DIR = root
    return root


def measure(category, info, mode, repeat):
    root = run_directories(category, mode, repeat)
    original_get_url = media.get_download_url
    original_download = media._download_to_file
    started = time.monotonic()
    first_play = {"at": None}
    download_seconds = None
    try:
        if mode == "optimized":
            def on_first_play(_):
                first_play["at"] = time.monotonic() - started

            success, _ = media.process_media_file(
                dict(info),
                root / "thumbs",
                root / "previews",
                root / "videos",
                include_video=info["type"] == "video",
                prefer_thumbnail=False,
                on_first_play=on_first_play,
                stop_after_first_play=True,
            )
            elapsed = first_play["at"]
        else:
            url, error = original_get_url(info["name"])
            if error or not url:
                raise RuntimeError(error or "无法获取下载链接")
            source = root / "temp_video" / f"baseline-{quote(info['name'], safe='')}"
            download_started = time.monotonic()
            success, error = original_download(url, source)
            download_seconds = time.monotonic() - download_started
            if not success:
                raise RuntimeError(error)
            media.get_download_url = lambda _: (str(source), None)

            def copy_source(_, destination, timeout=120, job_id=None):
                shutil.copyfile(source, destination)
                return True, None

            media._download_to_file = copy_source
            success, _ = media.process_media_file(
                dict(info),
                root / "thumbs",
                root / "previews",
                root / "videos",
                include_video=info["type"] == "video",
                prefer_thumbnail=False,
            )
            elapsed = time.monotonic() - started
        if not success:
            raise RuntimeError("媒体处理失败")
        if elapsed is None:
            raise RuntimeError("没有产生可播放内容")
        return {
            "category": category,
            "filename": info["name"],
            "source_bytes": info["size"],
            "mode": mode,
            "repeat": repeat,
            "ttfp_seconds": round(elapsed, 3),
            "download_seconds": round(download_seconds, 3) if download_seconds is not None else None,
            "processing_seconds": round(elapsed - download_seconds, 3) if download_seconds is not None else None,
            "success": True,
        }
    except Exception as error:
        return {
            "category": category,
            "filename": info["name"],
            "source_bytes": info["size"],
            "mode": mode,
            "repeat": repeat,
            "success": False,
            "error": str(error),
            "ttfp_seconds": round(time.monotonic() - started, 3),
        }
    finally:
        media.get_download_url = original_get_url
        media._download_to_file = original_download


def main():
    parser = argparse.ArgumentParser(description="测量冷图片/视频首次可播放时间")
    parser.add_argument("--mode", choices=("baseline", "optimized", "compare"), default="compare")
    parser.add_argument("--only", help="逗号分隔的样本类别")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--output", default=str(WORK_DIR / "report.json"))
    args = parser.parse_args()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    lock = (WORK_DIR / "benchmark.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("另一个 TTFP benchmark 正在运行，请等待它完成后再测")
    categories = set(args.only.split(",")) if args.only else set()
    samples = select_samples(args.db, categories)
    if not samples:
        raise SystemExit("没有可用样本")
    modes = ("baseline", "optimized") if args.mode == "compare" else (args.mode,)
    results = []
    for sample in samples:
        for mode in modes:
            for repeat in range(1, args.repeat + 1):
                result = measure(sample["category"], sample["info"], mode, repeat)
                results.append(result)
                status = f"{result['ttfp_seconds']:.2f}s" if result["success"] else result["error"]
                print(f"{sample['category']:14} {mode:9} #{repeat}: {status}", flush=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "created_at": datetime.now().isoformat(),
        "results": results,
    }, ensure_ascii=False, indent=2))
    if args.mode == "compare":
        for sample in samples:
            category = sample["category"]
            baseline = next((r for r in results if r["category"] == category and r["mode"] == "baseline" and r["success"]), None)
            optimized = next((r for r in results if r["category"] == category and r["mode"] == "optimized" and r["success"]), None)
            if baseline and optimized:
                improvement = (1 - optimized["ttfp_seconds"] / baseline["ttfp_seconds"]) * 100
                print(f"{category:14} TTFP 改善 {improvement:.1f}%")
    print(f"报告: {output}")
    if any(not result["success"] for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
