import sqlite3
from pathlib import Path

HANDLED_STATUSES = {"copied", "rejected", "review", "review_copied"}


class PhotoSyncStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS photo_sync_items (
                fs_id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                filename TEXT NOT NULL,
                md5 TEXT,
                size INTEGER,
                server_mtime INTEGER,
                thumbnail_path TEXT,
                face_score REAL,
                face_count INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                target_path TEXT,
                error TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_photo_sync_status "
            "ON photo_sync_items(status, server_mtime DESC)"
        )
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS photo_sync_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self.db.commit()

    def close(self):
        self.db.close()

    def get(self, fs_id):
        row = self.db.execute(
            "SELECT * FROM photo_sync_items WHERE fs_id = ?", (str(fs_id),)
        ).fetchone()
        return dict(row) if row else None

    def upsert(self, photo):
        fs_id = str(photo["fs_id"])
        existing = self.get(fs_id)
        values = (
            photo["path"],
            photo["server_filename"],
            photo.get("md5", ""),
            photo.get("size", 0),
            photo.get("server_mtime", 0),
            fs_id,
        )
        if existing is None:
            self.db.execute(
                """
                INSERT INTO photo_sync_items
                (source_path, filename, md5, size, server_mtime, fs_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                values,
            )
        else:
            changed = bool(
                photo.get("md5")
                and existing.get("md5")
                and photo["md5"] != existing["md5"]
            )
            self.db.execute(
                """
                UPDATE photo_sync_items
                SET source_path = ?, filename = ?, md5 = ?, size = ?,
                    server_mtime = ?, updated_at = CURRENT_TIMESTAMP
                WHERE fs_id = ?
                """,
                values,
            )
            if changed:
                self.db.execute(
                    """
                    UPDATE photo_sync_items
                    SET status = 'pending', target_path = NULL, error = NULL,
                        face_score = NULL, face_count = NULL, retry_count = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE fs_id = ?
                    """,
                    (fs_id,),
                )
        self.db.commit()
        return self.get(fs_id)

    def set_match(self, fs_id, status, score, face_count, thumbnail_path):
        self.db.execute(
            """
            UPDATE photo_sync_items
            SET status = ?, face_score = ?, face_count = ?, thumbnail_path = ?,
                error = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE fs_id = ?
            """,
            (status, score, face_count, str(thumbnail_path), str(fs_id)),
        )
        self.db.commit()

    def set_copying(self, fs_id, target_path):
        self.db.execute(
            """
            UPDATE photo_sync_items
            SET status = 'copying', target_path = ?, error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE fs_id = ?
            """,
            (target_path, str(fs_id)),
        )
        self.db.commit()

    def set_review_target(self, fs_id, target_path):
        self.db.execute(
            """
            UPDATE photo_sync_items
            SET target_path = ?, error = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE fs_id = ?
            """,
            (target_path, str(fs_id)),
        )
        self.db.commit()

    def set_review_copied(self, fs_id, target_path):
        self.db.execute(
            """
            UPDATE photo_sync_items
            SET status = 'review_copied', target_path = ?, error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE fs_id = ?
            """,
            (target_path, str(fs_id)),
        )
        self.db.commit()

    def set_copied(self, fs_id, target_path):
        self.db.execute(
            """
            UPDATE photo_sync_items
            SET status = 'copied', target_path = ?, error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE fs_id = ?
            """,
            (target_path, str(fs_id)),
        )
        self.db.commit()

    def set_status(self, fs_id, status):
        self.db.execute(
            """
            UPDATE photo_sync_items
            SET status = ?, error = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE fs_id = ?
            """,
            (status, str(fs_id)),
        )
        self.db.commit()

    def set_error(self, fs_id, message):
        self.db.execute(
            """
            UPDATE photo_sync_items
            SET status = 'error', error = ?, retry_count = retry_count + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE fs_id = ?
            """,
            (str(message)[:2000], str(fs_id)),
        )
        self.db.commit()
        return self.get(fs_id)

    def list_items(self, status=None, limit=100):
        if status:
            rows = self.db.execute(
                """
                SELECT * FROM photo_sync_items WHERE status = ?
                ORDER BY server_mtime DESC LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM photo_sync_items ORDER BY server_mtime DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def counts(self):
        rows = self.db.execute(
            "SELECT status, COUNT(*) AS count FROM photo_sync_items GROUP BY status"
        ).fetchall()
        return {row["status"]: row["count"] for row in rows}

    def counts_since(self, cutoff):
        rows = self.db.execute(
            """
            SELECT status, COUNT(*) AS count FROM photo_sync_items
            WHERE updated_at >= ? GROUP BY status
            """,
            (cutoff,),
        ).fetchall()
        return {row["status"]: row["count"] for row in rows}

    def list_recent(self, cutoff, limit=20, statuses=None):
        query = """
            SELECT * FROM photo_sync_items WHERE updated_at >= ?
        """
        params = [cutoff]
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            query += f" AND status IN ({placeholders})"
            params.extend(statuses)
        query += " ORDER BY updated_at DESC, fs_id DESC LIMIT ?"
        params.append(limit)
        rows = self.db.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def requeue(self, statuses, videos_only=False):
        statuses = list(statuses)
        placeholders = ",".join("?" for _ in statuses)
        query = f"""
            UPDATE photo_sync_items
            SET status = 'pending', error = NULL, retry_count = 0,
                target_path = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE status IN ({placeholders})
        """
        params = list(statuses)
        if videos_only:
            query += """
                AND (lower(filename) LIKE '%.livp'
                     OR lower(filename) LIKE '%.mp4'
                     OR lower(filename) LIKE '%.mov')
            """
        cursor = self.db.execute(query, params)
        self.db.commit()
        if cursor.rowcount:
            self.set_state("scan_backlog", "1")
        return cursor.rowcount

    def get_state(self, key):
        row = self.db.execute(
            "SELECT value FROM photo_sync_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_state(self, key, value):
        self.db.execute(
            """
            INSERT INTO photo_sync_state(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self.db.commit()
