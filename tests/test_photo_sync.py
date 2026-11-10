import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from babysit.face_matcher import FaceMatch, VideoFaceMatch
from babysit.photo_sync import PhotoSyncService
from babysit.photo_sync_config import PhotoSyncConfig
from babysit.photo_sync_db import PhotoSyncStore


def photo(fs_id, name=None, md5=None):
    return {
        "fs_id": str(fs_id),
        "path": f"/来自：手机/{name or f'IMG_{fs_id}.jpg'}",
        "server_filename": name or f"IMG_{fs_id}.jpg",
        "md5": md5 or f"md5-{fs_id}",
        "size": 123,
        "server_mtime": 1000 + int(fs_id),
        "thumbs": {"url3": f"https://example.test/{fs_id}.jpg"},
    }


class FakeImageClient:
    def __init__(self, pages, target_files=()):
        self.pages = pages
        self.target_files = list(target_files)
        self.page_size = 100

    def iter_pages(self):
        yield from self.pages

    def list_files(self, remote_path):
        return self.target_files

    def download_thumbnail(self, item, destination):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(str(item["fs_id"]).encode())
        return destination

    def prefetch_thumbnails(self, photos, cache_dir, workers):
        for item in photos:
            self.download_thumbnail(item, Path(cache_dir) / f"{item['fs_id']}.jpg")
        return {}


class FakeMatcher:
    def __init__(self, scores):
        self.scores = scores
        self.calls = 0

    def match(self, image_bytes):
        self.calls += 1
        score = self.scores[image_bytes.decode()]
        return FaceMatch(score=score, face_count=0 if score is None else 1)

    def match_frames(self, frame_paths):
        frame_path = Path(frame_paths[0])
        match = self.match(frame_path.read_bytes())
        return VideoFaceMatch(
            score=match.score,
            face_count=match.face_count,
            supporting_frames=int(match.score is not None and match.score >= 0.35),
            frame_count=len(frame_paths),
            best_frame_path=str(frame_path) if match.score is not None else None,
        )


class FakeCopier:
    def __init__(self, existing=(), fail_times=0):
        self.existing = set(existing)
        self.copies = []
        self.fail_times = fail_times
        self.matcher_calls = 0

    def exists(self, remote_path):
        return remote_path in self.existing

    def copy(self, source_path, target_path):
        if self.fail_times:
            self.fail_times -= 1
            raise RuntimeError("temporary copy failure")
        self.copies.append((source_path, target_path))
        self.existing.add(target_path)

    def ensure_directory(self, remote_path):
        self.existing.add(remote_path)


class FakeNotifier:
    def __init__(self):
        self.calls = []

    def notify_round(self, results, pending_review):
        self.calls.append((results, pending_review))
        return True


class PhotoSyncTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.config = PhotoSyncConfig(
            source_path="/来自：手机",
            destination_path="/apps/bypy/爸妈与小宝",
            review_destination_path="/apps/bypy/爸妈与小宝-review",
            reference_dir=root / "references",
            cache_dir=root / "thumbnails",
            db_path=root / "sync.db",
            baidupcs_bin="unused",
            auto_threshold=0.55,
            review_threshold=0.35,
            scan_limit=50,
            page_size=100,
            interval=1800,
            backlog_interval=60,
            download_workers=4,
            max_retries=3,
            model_name="unused",
            model_dir=root / "models",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def service(self, pages, scores, copier=None, target_files=()):
        store = PhotoSyncStore(self.config.db_path)
        matcher = FakeMatcher(scores)
        service = PhotoSyncService(
            self.config,
            store=store,
            image_client=FakeImageClient(pages, target_files),
            copier=copier or FakeCopier(),
            matcher=matcher,
        )
        service.notifier = FakeNotifier()
        self.addCleanup(store.close)
        return service, store, service.copier, matcher

    def test_high_score_is_copied_and_not_processed_again(self):
        import io
        from contextlib import redirect_stdout

        service, store, copier, matcher = self.service([[photo(1)]], {"1": 0.7})

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(service.sync()["copied"], 1)
        self.assertIn("已复制", output.getvalue())
        self.assertIn(photo(1)["path"], output.getvalue())
        self.assertIn("/apps/bypy/爸妈与小宝/IMG_1.jpg", output.getvalue())
        self.assertIn("0.700", output.getvalue())
        self.assertEqual(
            copier.copies,
            [(photo(1)["path"], "/apps/bypy/爸妈与小宝/IMG_1.jpg")],
        )
        self.assertEqual(store.get(1)["status"], "copied")
        self.assertEqual(service.sync()["skipped"], 1)
        self.assertEqual(matcher.calls, 1)
        self.assertEqual(len(copier.copies), 1)

    def test_video_uses_extracted_frames(self):
        service, store, _, _ = self.service(
            [[photo(1, name="clip.livp")]], {"1": 0.7}
        )

        class Extractor:
            called = False

            def extract(self, item):
                self.called = True
                return [Path(service.config.cache_dir) / "1.jpg"]

        extractor = Extractor()
        service._video_extractor = extractor
        self.assertEqual(service.sync()["copied"], 1)
        self.assertTrue(extractor.called)
        self.assertEqual(store.get(1)["status"], "copied")

    def test_review_is_archived_and_notified_only_once(self):
        service, store, copier, _ = self.service([[photo(1)]], {"1": 0.45})

        results = service.sync()
        self.assertEqual(results["review"], 1)
        self.assertEqual(results["review_copied"], 1)
        self.assertEqual(store.get(1)["status"], "review_copied")
        self.assertEqual(
            store.get(1)["target_path"],
            "/apps/bypy/爸妈与小宝-review/IMG_1.jpg",
        )
        self.assertEqual(len(service.notifier.calls), 1)
        self.assertEqual(len(copier.copies), 1)

        self.assertEqual(service.sync()["review_copied"], 0)
        self.assertEqual(len(service.notifier.calls), 1)
        self.assertEqual(len(copier.copies), 1)

    def test_medium_and_low_scores_and_no_face(self):
        service, store, _, _ = self.service(
            [[photo(1), photo(2), photo(3), photo(4)]],
            {"1": 0.45, "2": 0.2, "3": None, "4": 0.8},
        )

        results = service.sync(dry_run=True)

        self.assertEqual(results["review"], 2)
        self.assertEqual(results["rejected"], 2)
        self.assertEqual(store.get(1)["status"], "review")
        self.assertEqual(store.get(2)["status"], "rejected")
        self.assertEqual(store.get(3)["status"], "rejected")
        self.assertEqual(store.get(4)["status"], "review")

    def test_target_filename_is_processed_without_face_analysis(self):
        target = "/apps/bypy/爸妈与小宝/IMG_1.jpg"
        target_files = [{"server_filename": "IMG_1.jpg", "path": target, "md5": "md5-1"}]
        service, store, copier, matcher = self.service(
            [[photo(1)]], {"1": 0.8}, target_files=target_files
        )

        self.assertEqual(service.sync()["existing"], 1)
        self.assertEqual(store.get(1)["status"], "copied")
        self.assertEqual(store.get(1)["target_path"], target)
        self.assertEqual(matcher.calls, 0)
        self.assertEqual(copier.copies, [])

    def test_same_filename_with_different_md5_is_not_skipped(self):
        original = "/apps/bypy/爸妈与小宝/IMG_1.jpg"
        target_files = [{"server_filename": "IMG_1.jpg", "path": original, "md5": "other"}]
        copier = FakeCopier(existing={original})
        service, store, _, matcher = self.service(
            [[photo(1)]], {"1": 0.8}, copier, target_files
        )

        self.assertEqual(service.sync()["copied"], 1)
        self.assertEqual(
            store.get(1)["target_path"], "/apps/bypy/爸妈与小宝/IMG_1_1.jpg"
        )
        self.assertEqual(matcher.calls, 1)

    def test_target_fs_id_suffix_is_processed(self):
        target = "/apps/bypy/爸妈与小宝/IMG_1_1.jpg"
        target_files = [{"server_filename": "IMG_1_1.jpg", "path": target}]
        service, store, copier, matcher = self.service(
            [[photo(1)]], {"1": 0.8}, target_files=target_files
        )

        self.assertEqual(service.sync()["existing"], 1)
        self.assertEqual(store.get(1)["target_path"], target)
        self.assertEqual(matcher.calls, 0)
        self.assertEqual(copier.copies, [])

    def test_target_md5_is_processed_even_when_renamed(self):
        target = "/apps/bypy/爸妈与小宝/renamed.jpg"
        target_files = [
            {"server_filename": "renamed.jpg", "path": target, "md5": "md5-1"}
        ]
        service, store, copier, matcher = self.service(
            [[photo(1)]], {"1": 0.8}, target_files=target_files
        )

        self.assertEqual(service.sync()["existing"], 1)
        self.assertEqual(store.get(1)["target_path"], target)
        self.assertEqual(matcher.calls, 0)
        self.assertEqual(copier.copies, [])

    def test_duplicate_source_is_only_copied_once_per_run(self):
        first = photo(1, name="first.jpg", md5="same")
        second = photo(2, name="second.jpg", md5="same")
        service, _, copier, matcher = self.service(
            [[first, second]], {"1": 0.8, "2": 0.8}
        )

        results = service.sync()
        self.assertEqual(results["copied"], 1)
        self.assertEqual(results["existing"], 1)
        self.assertEqual(matcher.calls, 1)
        self.assertEqual(len(copier.copies), 1)

    def test_copy_failure_resumes_without_recognition_or_rename(self):
        copier = FakeCopier(fail_times=1)
        service, store, _, matcher = self.service(
            [[photo(1)]], {"1": 0.8}, copier
        )

        self.assertEqual(service.sync()["error"], 1)
        failed = store.get(1)
        self.assertEqual(failed["status"], "error")
        target = failed["target_path"]
        self.assertEqual(service.sync()["copied"], 1)
        self.assertEqual(store.get(1)["target_path"], target)
        self.assertEqual(matcher.calls, 1)
        self.assertEqual(len(copier.copies), 1)

    def test_prefetch_failure_is_recorded_and_retried(self):
        service, store, _, _ = self.service([[photo(1)]], {"1": 0.8})
        service.image_client.prefetch_thumbnails = lambda *args: {
            "1": RuntimeError("network timeout")
        }

        self.assertEqual(service.sync()["error"], 1)
        self.assertEqual(store.get(1)["status"], "error")
        self.assertEqual(store.get(1)["retry_count"], 1)
        self.assertEqual(store.get(1)["source_path"], photo(1)["path"])

    def test_requeue_only_reprocesses_selected_videos(self):
        store = PhotoSyncStore(self.config.db_path)
        self.addCleanup(store.close)
        store.upsert(photo(1, name="photo.jpg"))
        store.upsert(photo(2, name="clip.livp"))
        store.upsert(photo(3, name="other.livp"))
        store.upsert(photo(4, name="copied.livp"))
        store.set_status(1, "rejected")
        store.set_status(2, "rejected")
        store.set_status(3, "review")
        store.set_status(4, "copied")

        self.assertEqual(store.requeue(["rejected", "review"], videos_only=True), 2)
        self.assertEqual(store.get(1)["status"], "rejected")
        self.assertEqual(store.get(2)["status"], "pending")
        self.assertEqual(store.get(3)["status"], "pending")
        self.assertEqual(store.get(4)["status"], "copied")

    def test_backlog_is_processed_on_later_runs(self):
        from dataclasses import replace

        self.config = replace(self.config, page_size=2)
        pages = [[photo(1), photo(2)], [photo(3)]]
        service, store, _, _ = self.service(
            pages, {"1": 0.8, "2": 0.8, "3": 0.8}
        )

        service.sync(limit=1)
        self.assertEqual(store.get_state("scan_backlog"), "1")
        service.sync(limit=1)
        self.assertEqual(store.get(2)["status"], "copied")
        service.sync(limit=1)
        self.assertEqual(store.get(3)["status"], "copied")
        self.assertEqual(store.get_state("scan_backlog"), "0")

    def test_approve_and_reject_review_items(self):
        service, store, copier, _ = self.service(
            [[photo(1), photo(2)]], {"1": 0.4, "2": 0.4}
        )
        service.sync()

        service.approve(1)
        service.reject(2)
        self.assertEqual(store.get(1)["status"], "copied")
        self.assertEqual(store.get(2)["status"], "rejected")
        self.assertEqual(len(copier.copies), 3)

    def test_changed_content_is_pending_again(self):
        store = PhotoSyncStore(self.config.db_path)
        self.addCleanup(store.close)
        store.upsert(photo(1, md5="old"))
        store.set_status(1, "rejected")

        store.upsert(photo(1, md5="old"))
        self.assertEqual(store.get(1)["status"], "rejected")
        store.upsert(photo(1, md5="new"))
        item = store.get(1)
        self.assertEqual(item["status"], "pending")
        self.assertEqual(item["md5"], "new")
        self.assertEqual(item["retry_count"], 0)

    def test_max_retries_moves_item_to_review(self):
        service, store, _, _ = self.service([[photo(1)]], {"1": 0.8})
        for _ in range(self.config.max_retries):
            service.image_client.download_thumbnail = lambda *args: (_ for _ in ()).throw(
                RuntimeError("not ready")
            )
            service.process_photo(photo(1))

        self.assertEqual(store.get(1)["status"], "review")

    def test_source_and_destination_cannot_overlap(self):
        config = self.config
        config = type(config)(
            source_path="/来自：手机",
            destination_path="/来自：手机/精选",
            review_destination_path=config.review_destination_path,
            reference_dir=config.reference_dir,
            cache_dir=config.cache_dir,
            db_path=config.db_path,
            baidupcs_bin=config.baidupcs_bin,
            auto_threshold=config.auto_threshold,
            review_threshold=config.review_threshold,
            scan_limit=config.scan_limit,
            page_size=config.page_size,
            interval=config.interval,
            backlog_interval=config.backlog_interval,
            download_workers=config.download_workers,
            max_retries=config.max_retries,
            model_name=config.model_name,
            model_dir=config.model_dir,
        )
        with self.assertRaises(ValueError):
            config.validate()

    def test_recent_counts_and_items_use_update_time_and_status_filter(self):
        from datetime import datetime, timedelta, timezone

        store = PhotoSyncStore(self.config.db_path)
        self.addCleanup(store.close)
        for fs_id in (1, 2, 3, 4):
            store.upsert(photo(fs_id))
        store.set_copied(1, "/apps/bypy/爸妈与小宝/IMG_1.jpg")
        store.set_status(2, "review")
        store.set_status(3, "rejected")
        store.set_status(4, "copied")
        now = datetime.now(timezone.utc)
        recent = now.strftime("%Y-%m-%d %H:%M:%S")
        older = (now + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
        old = (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        store.db.execute("UPDATE photo_sync_items SET updated_at = ? WHERE fs_id = '1'", (recent,))
        store.db.execute("UPDATE photo_sync_items SET updated_at = ? WHERE fs_id = '2'", (older,))
        store.db.execute("UPDATE photo_sync_items SET updated_at = ? WHERE fs_id = '3'", (recent,))
        store.db.execute("UPDATE photo_sync_items SET updated_at = ? WHERE fs_id = '4'", (old,))
        cutoff = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

        self.assertEqual(
            store.counts_since(cutoff), {"copied": 1, "review": 1, "rejected": 1}
        )
        items = store.list_recent(cutoff, 20, ("copied", "review"))
        self.assertEqual([item["fs_id"] for item in items], ["2", "1"])
        self.assertEqual(len(store.list_recent(cutoff, 20)), 3)

    def test_environment_thresholds(self):
        with patch.dict(
            "os.environ",
            {
                "PHOTO_SYNC_SOURCE_PATH": "/来自：手机",
                "PHOTO_SYNC_AUTO_THRESHOLD": "0.65",
                "PHOTO_SYNC_REVIEW_THRESHOLD": "0.4",
            },
        ):
            config = PhotoSyncConfig.from_env()
            self.assertEqual(config.auto_threshold, 0.65)
            self.assertEqual(config.review_threshold, 0.4)


if __name__ == "__main__":
    unittest.main()
