import subprocess
import zipfile
from pathlib import Path

VIDEO_EXTENSIONS = {".livp", ".mp4", ".mov"}


class VideoFrameExtractor:
    def __init__(self, copier, work_dir, max_frames=24):
        self.copier = copier
        self.work_dir = Path(work_dir)
        self.max_frames = max_frames

    def extract(self, photo):
        fs_id = str(photo["fs_id"])
        frame_dir = self.work_dir / fs_id
        existing = sorted(frame_dir.glob("frame-*.jpg"))
        if existing:
            return existing
        frame_dir.mkdir(parents=True, exist_ok=True)
        original = self.copier.download(photo["path"], self.work_dir)
        video_path = self._video_path(original, fs_id)
        duration = self._duration(video_path)
        interval = 0.5 if duration <= 4 else max(2.0, duration / self.max_frames)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(video_path),
                "-vf",
                f"fps=1/{interval},scale=640:-2",
                "-q:v",
                "3",
                str(frame_dir / "frame-%03d.jpg"),
            ],
            check=True,
            capture_output=True,
            timeout=max(60, int(duration * 2)),
        )
        video_path.unlink(missing_ok=True)
        if original.suffix.lower() == ".livp":
            original.unlink(missing_ok=True)
        frames = sorted(frame_dir.glob("frame-*.jpg"))
        if not frames:
            raise RuntimeError(f"视频未提取到帧：{photo['path']}")
        return frames

    @staticmethod
    def _video_path(original, fs_id):
        if original.suffix.lower() != ".livp":
            return original
        video_path = original.with_name(f"{fs_id}.mov")
        with zipfile.ZipFile(original) as archive:
            videos = [
                name for name in archive.namelist() if name.lower().endswith(".mov")
            ]
            if not videos:
                raise RuntimeError(f"Live Photo 中没有视频：{original}")
            video_path.write_bytes(archive.read(videos[0]))
        return video_path

    @staticmethod
    def _duration(video_path):
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float(result.stdout.strip())
