import shutil
import sqlite3
from pathlib import Path

from babysit.config import CACHE_DIR, DB_PATH
from babysit.media_cache import existing_video_path, preview_path, thumbnail_path
from babysit.refresh_media import process_preview_from_existing

DEMO = Path("babysit/data/lru_demo").resolve()
SOURCE_DB = Path("babysit/data/babysit.db")
SOURCE_CACHE = Path("babysit/data/cache").resolve()


def main():
    if DEMO.exists():
        shutil.rmtree(DEMO)
    for directory in ("thumbs", "previews", "videos", "temp_video"):
        (DEMO / "cache" / directory).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE_DB, DEMO / "babysit.db")
    db = sqlite3.connect(DEMO / "babysit.db")
    for table in ("media_warm_jobs", "media_warm_clients", "media_cache"):
        db.execute(f"DELETE FROM {table}")
    db.commit()

    copied = 0
    copied_names = []
    for filename, file_type in db.execute(
        "SELECT filename, file_type FROM media_files WHERE processed = 1 "
        "ORDER BY date DESC, time DESC LIMIT 30"
    ):
        if file_type == "video" and copied >= 6:
            break
        if file_type == "photo" and copied >= 12:
            break
        copied += 1
        copied_names.append(filename)
        for source in (preview_path(filename), thumbnail_path(filename), existing_video_path(filename)):
            if source and source.exists():
                relative = source.relative_to(SOURCE_CACHE)
                target = DEMO / "cache" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    placeholders = ",".join("?" for _ in copied_names)
    db.execute(f"DELETE FROM media_files WHERE filename NOT IN ({placeholders})", copied_names)
    db.execute("DELETE FROM milestones")
    db.commit()
    for filename in copied_names:
        process_preview_from_existing(filename)
    db.close()
    print(f"Prepared {copied} media files in {DEMO}")


if __name__ == "__main__":
    main()
