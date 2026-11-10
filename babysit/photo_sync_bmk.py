import argparse
import json
from pathlib import Path

from .baidu_sync import BaiduPCSClient
from .config import DATA_DIR
from .face_matcher import CROP_AUTO_THRESHOLD, InsightFaceMatcher
from .video_frames import VIDEO_EXTENSIONS, VideoFrameExtractor


def evaluate(args):
    bmk_dir = Path(args.bmk_dir)
    manifest = json.loads((bmk_dir / "manifest.json").read_text())
    matcher = InsightFaceMatcher(args.references, model_dir=args.model_dir)
    extractor = VideoFrameExtractor(BaiduPCSClient(), bmk_dir / "video_work")
    rows = []
    for item in manifest["items"]:
        fs_id = str(item["fs_id"])
        filename = item["filename"]
        print(f"评估 {fs_id} {filename}", flush=True)
        is_video = Path(filename).suffix.lower() in VIDEO_EXTENSIONS
        if is_video:
            cached_frames = sorted(
                (bmk_dir / "frames" / Path(filename).stem).glob("frame-*.jpg")
            )
            if cached_frames:
                frames = cached_frames
            else:
                photo = {"fs_id": fs_id, "path": f"/来自：iPhone/{filename}"}
                frames = extractor.extract(photo)
            match = matcher.match_frames(frames)
            thumbnail_path = match.best_frame_path
        else:
            thumbnail_path = str(DATA_DIR / "photo_sync" / "thumbnails" / f"{fs_id}.jpg")
            match = matcher.match_with_crops(thumbnail_path)
        is_crop_match = match.best_frame_path != thumbnail_path
        if match.score is None:
            prediction = "rejected"
        elif match.score >= args.auto_threshold or (
            is_crop_match and match.score >= CROP_AUTO_THRESHOLD
        ):
            prediction = "copied"
        elif match.score >= args.review_threshold:
            prediction = "review"
        else:
            prediction = "rejected"
        rows.append(
            {
                **item,
                "label": item["label"],
                "prediction": prediction,
                "score": match.score,
                "face_count": match.face_count,
                "frame_count": getattr(match, "frame_count", 1),
                "supporting_frames": getattr(match, "supporting_frames", 0),
                "best_frame_path": thumbnail_path,
            }
        )
    positives = [row for row in rows if row["label"] == 1]
    negatives = [row for row in rows if row["label"] == 0]
    metrics = {
        "positive_total": len(positives),
        "negative_total": len(negatives),
        "auto_recall": _ratio(positives, {"copied"}),
        "review_recall": _ratio(positives, {"copied", "review"}),
        "auto_false_positive": sum(row["prediction"] == "copied" for row in negatives),
        "review_false_positive": sum(
            row["prediction"] in {"copied", "review"} for row in negatives
        ),
        "auto_threshold": args.auto_threshold,
        "review_threshold": args.review_threshold,
        "references": str(args.references),
    }
    return metrics, rows


def _ratio(rows, predictions):
    if not rows:
        return 0
    return sum(row["prediction"] in predictions for row in rows) / len(rows)


def main():
    parser = argparse.ArgumentParser(description="宝宝照片视频识别回归 benchmark")
    parser.add_argument("--bmk-dir", default=str(DATA_DIR / "photo_sync_bmk"))
    parser.add_argument("--references", required=True)
    parser.add_argument("--model-dir", default=str(DATA_DIR / "photo_sync" / "models"))
    parser.add_argument("--auto-threshold", type=float, default=0.54)
    parser.add_argument("--review-threshold", type=float, default=0.35)
    parser.add_argument("--output")
    args = parser.parse_args()
    metrics, rows = evaluate(args)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    for row in rows:
        label = "正例" if row["label"] else "负例"
        score = "—" if row["score"] is None else f"{row['score']:.3f}"
        print(
            f"{label}\t{row['prediction']}\t{score}\t"
            f"帧 {row['supporting_frames']}/{row['frame_count']}\t{row['filename']}"
        )
    if args.output:
        Path(args.output).write_text(
            json.dumps({"metrics": metrics, "items": rows}, ensure_ascii=False, indent=2)
        )


if __name__ == "__main__":
    main()
