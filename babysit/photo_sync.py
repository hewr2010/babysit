import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

import requests

from .baidu_sync import BaiduImageClient, BaiduPCSClient
from .face_matcher import InsightFaceMatcher
from .photo_sync_config import PhotoSyncConfig
from .photo_sync_db import HANDLED_STATUSES, PhotoSyncStore


class PhotoSyncService:
    def __init__(self, config, store=None, image_client=None, copier=None, matcher=None):
        self.config = config
        self.store = store or PhotoSyncStore(config.db_path)
        self.image_client = image_client or BaiduImageClient(
            config.source_path, page_size=config.page_size
        )
        self.copier = copier or BaiduPCSClient(config.baidupcs_bin)
        self._matcher = matcher

    @property
    def matcher(self):
        if self._matcher is None:
            self._matcher = InsightFaceMatcher(
                self.config.reference_dir,
                self.config.model_name,
                self.config.model_dir,
            )
        return self._matcher

    def _target_path(self, item):
        if item.get("target_path"):
            return item["target_path"]
        filename = item["filename"]
        candidate = f"{self.config.destination_path}/{filename}"
        if self.copier.exists(candidate):
            path = Path(filename)
            candidate = (
                f"{self.config.destination_path}/{path.stem}_{item['fs_id']}{path.suffix}"
            )
        return candidate

    def copy_item(self, item):
        target_path = self._target_path(item)
        self.store.set_copying(item["fs_id"], target_path)
        self.copier.copy(item["source_path"], target_path)
        self.store.set_copied(item["fs_id"], target_path)
        return target_path

    def _record_error(self, fs_id, exc):
        item = self.store.set_error(fs_id, exc)
        if item["retry_count"] >= self.config.max_retries:
            self.store.set_status(fs_id, "review")
            return "review"
        return "error"

    def process_photo(self, photo, dry_run=False):
        item = self.store.upsert(photo)
        fs_id = item["fs_id"]
        if item["status"] in HANDLED_STATUSES:
            return "skipped"
        if item["retry_count"] >= self.config.max_retries:
            self.store.set_status(fs_id, "review")
            return "review"
        if item.get("target_path") and item.get("face_score") is not None:
            if dry_run:
                self.store.set_status(fs_id, "review")
                return "review"
            try:
                self.copy_item(item)
                return "copied"
            except (OSError, RuntimeError, ValueError, requests.RequestException) as exc:
                return self._record_error(fs_id, exc)

        thumbnail_path = self.config.cache_dir / f"{fs_id}.jpg"
        try:
            self.image_client.download_thumbnail(photo, thumbnail_path)
            match = self.matcher.match(thumbnail_path.read_bytes())
            if match.score is None or match.score < self.config.review_threshold:
                self.store.set_match(
                    fs_id, "rejected", match.score, match.face_count, thumbnail_path
                )
                return "rejected"
            status = (
                "review"
                if dry_run or match.score < self.config.auto_threshold
                else "matched"
            )
            self.store.set_match(
                fs_id, status, match.score, match.face_count, thumbnail_path
            )
            if status == "review":
                return "review"
            self.copy_item(self.store.get(fs_id))
            return "copied"
        except (OSError, RuntimeError, ValueError, requests.RequestException) as exc:
            return self._record_error(fs_id, exc)

    def sync(self, limit=None, dry_run=False):
        self.config.validate()
        limit = limit or self.config.scan_limit
        if limit < 1:
            raise ValueError("limit 必须大于 0")
        _ = self.matcher
        results = {
            "copied": 0,
            "review": 0,
            "rejected": 0,
            "error": 0,
            "skipped": 0,
        }
        processed = 0
        limit_hit = False
        backlog = self.store.get_state("scan_backlog") == "1"
        for page in self.image_client.iter_pages():
            for photo in page:
                fs_id = str(photo["fs_id"])
                existing = self.store.get(fs_id)
                if existing and existing["status"] in HANDLED_STATUSES:
                    results["skipped"] += 1
                    continue
                if processed >= limit:
                    limit_hit = True
                    break
                outcome = self.process_photo(photo, dry_run=dry_run)
                results[outcome] += 1
                processed += 1
            if limit_hit:
                break
            if page and all(
                (item := self.store.get(str(photo["fs_id"])))
                and item["status"] in HANDLED_STATUSES
                for photo in page
            ) and not backlog:
                break
            if len(page) < self.config.page_size:
                break
        self.store.set_state("scan_backlog", "1" if limit_hit else "0")
        return results

    def approve(self, fs_id):
        item = self.store.get(fs_id)
        if not item:
            raise ValueError(f"找不到同步记录 {fs_id}")
        if item["status"] == "copied":
            return item["target_path"]
        return self.copy_item(item)

    def reject(self, fs_id):
        if not self.store.get(fs_id):
            raise ValueError(f"找不到同步记录 {fs_id}")
        self.store.set_status(fs_id, "rejected")

    def doctor(self):
        self.config.validate()
        photos = self.image_client.list_page(1, num=1)
        reference_count = len(self.matcher._reference_embeddings)
        account = self.copier.who()
        return {
            "photos_visible": len(photos),
            "reference_count": reference_count,
            "account": account,
        }


def _config_from_args(args, require_source=True):
    config = PhotoSyncConfig.from_env()
    overrides = {
        "source_path": args.source,
        "destination_path": args.destination,
        "reference_dir": Path(args.references) if args.references else None,
        "baidupcs_bin": args.baidupcs_bin,
    }
    config = replace(
        config, **{key: value for key, value in overrides.items() if value is not None}
    )
    config.validate(require_source=require_source)
    return config


def _print_results(results):
    print(
        "本轮：复制 {copied}，待确认 {review}，跳过不匹配 {rejected}，"
        "失败 {error}，已处理 {skipped}".format(**results)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="自动筛选并复制手机网盘照片中的女儿照片")
    parser.add_argument("--source", help="手机照片网盘来源目录")
    parser.add_argument("--destination", help="复制目标目录")
    parser.add_argument("--references", help="女儿参考照片本地目录")
    parser.add_argument("--baidupcs-bin", help="BaiduPCS-Go 可执行文件路径")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="执行一轮增量同步")
    sync_parser.add_argument("--dry-run", action="store_true", help="只识别，不复制")
    sync_parser.add_argument("--limit", type=int, help="本轮最多处理的新照片数")

    subparsers.add_parser("daemon", help="按配置间隔持续同步")

    status_parser = subparsers.add_parser("status", help="查看同步状态")
    status_parser.add_argument("--status", dest="filter_status")
    status_parser.add_argument("--limit", type=int, default=100)

    approve_parser = subparsers.add_parser("approve", help="复制一条待确认照片")
    approve_parser.add_argument("fs_id")

    reject_parser = subparsers.add_parser("reject", help="跳过一条待确认照片")
    reject_parser.add_argument("fs_id")

    subparsers.add_parser("doctor", help="检查授权、参考照片和来源目录")
    args = parser.parse_args(argv)

    try:
        config = _config_from_args(
            args, require_source=args.command in {"sync", "daemon", "doctor"}
        )
        service = PhotoSyncService(config)
        if args.command == "sync":
            _print_results(service.sync(limit=args.limit, dry_run=args.dry_run))
        elif args.command == "daemon":
            while True:
                try:
                    _print_results(service.sync())
                except (RuntimeError, requests.RequestException) as exc:
                    print(f"本轮同步失败：{exc}", file=sys.stderr)
                time.sleep(config.interval)
        elif args.command == "status":
            print("状态统计：", service.store.counts())
            for item in service.store.list_items(args.filter_status, args.limit):
                score = (
                    f"{item['face_score']:.3f}"
                    if item["face_score"] is not None
                    else "无人脸"
                )
                print(f"{item['fs_id']}\t{score}\t{item['source_path']}")
        elif args.command == "approve":
            print("已复制到：", service.approve(args.fs_id))
        elif args.command == "reject":
            service.reject(args.fs_id)
            print("已标记为跳过")
        elif args.command == "doctor":
            result = service.doctor()
            print(f"来源目录读取成功，本页返回 {result['photos_visible']} 张照片")
            print(f"可用女儿参考人脸：{result['reference_count']} 个")
            print("BaiduPCS-Go：", result["account"])
        return 0
    except (ValueError, RuntimeError, requests.RequestException) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
