import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from babysit.face_matcher import FaceMatch
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


class FakeMatcher:
    def __init__(self, scores):
        self.scores = scores
        self.calls = 0

    def match(self, image_bytes):
        self.calls += 1
        score = self.scores[image_bytes.decode()]
        return FaceMatch(score=score, face_count=0 if score is None else 1)


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


class PhotoSyncTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.config = PhotoSyncConfig(
            source_path="/来自：手机",
            destination_path="/apps/bypy/爸妈与小宝",
            reference_dir=root / "references",
            cache_dir=root / "thumbnails",
            db_path=root / "sync.db",
            baidupcs_bin="unused",
            auto_threshold=0.55,
            review_threshold=0.35,
            scan_limit=50,
            page_size=100,
            interval=1800,
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
        self.addCleanup(store.close)
        return service, store, service.copier, matcher

    def test_high_score_is_copied_and_not_processed_again(self):
        service, store, copier, matcher = self.service([[photo(1)]], {"1": 0.7})

        self.assertEqual(service.sync()["copied"], 1)
        self.assertEqual(
            copier.copies,
            [(photo(1)["path"], "/apps/bypy/爸妈与小宝/IMG_1.jpg")],
        )
        self.assertEqual(store.get(1)["status"], "copied")
        self.assertEqual(service.sync()["skipped"], 1)
        self.assertEqual(matcher.calls, 1)
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
        target_files = [{"server_filename": "IMG_1.jpg", "path": target, "md5": "other"}]
        service, store, copier, matcher = self.service(
            [[photo(1)]], {"1": 0.8}, target_files=target_files
        )

        self.assertEqual(service.sync()["existing"], 1)
        self.assertEqual(store.get(1)["status"], "copied")
        self.assertEqual(store.get(1)["target_path"], target)
        self.assertEqual(matcher.calls, 0)
        self.assertEqual(copier.copies, [])

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
        self.assertEqual(len(copier.copies), 1)

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
            reference_dir=config.reference_dir,
            cache_dir=config.cache_dir,
            db_path=config.db_path,
            baidupcs_bin=config.baidupcs_bin,
            auto_threshold=config.auto_threshold,
            review_threshold=config.review_threshold,
            scan_limit=config.scan_limit,
            page_size=config.page_size,
            interval=config.interval,
            max_retries=config.max_retries,
            model_name=config.model_name,
            model_dir=config.model_dir,
        )
        with self.assertRaises(ValueError):
            config.validate()

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
