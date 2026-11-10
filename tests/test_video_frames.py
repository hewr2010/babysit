import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from babysit.face_matcher import FaceMatch, InsightFaceMatcher
from babysit.video_frames import VideoFrameExtractor


class MatchFramesTests(unittest.TestCase):
    def test_best_frame_and_supporting_frames(self):
        matcher = InsightFaceMatcher.__new__(InsightFaceMatcher)
        scores = {"a": 0.2, "b": 0.7, "c": 0.4, "d": None}
        matcher.match = lambda image: FaceMatch(scores[image.decode()], 1)
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name in scores:
                path = Path(directory) / f"{name}.jpg"
                path.write_bytes(name.encode())
                paths.append(path)
            result = matcher.match_frames(paths)

        self.assertEqual(result.score, 0.7)
        self.assertEqual(result.supporting_frames, 2)
        self.assertEqual(result.frame_count, 4)
        self.assertEqual(result.best_frame_path, str(paths[1]))

    def test_no_faces_returns_empty_score(self):
        matcher = InsightFaceMatcher.__new__(InsightFaceMatcher)
        matcher.match = lambda image: FaceMatch(None, 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "a.jpg"
            path.write_bytes(b"a")
            result = matcher.match_frames([path])
        self.assertIsNone(result.score)
        self.assertIsNone(result.best_frame_path)
        self.assertEqual(result.supporting_frames, 0)


class VideoFrameExtractorTests(unittest.TestCase):
    def test_livp_is_unpacked_sampled_and_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mov"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=duration=1:size=64x64:rate=4",
                    "-pix_fmt",
                    "yuv420p",
                    str(source),
                ],
                check=True,
                capture_output=True,
            )
            livp = root / "sample.livp"
            with zipfile.ZipFile(livp, "w") as archive:
                archive.write(source, "sample.mov")

            class Copier:
                def __init__(self):
                    self.calls = 0

                def download(self, source_path, destination_dir):
                    self.calls += 1
                    return livp

            copier = Copier()
            extractor = VideoFrameExtractor(copier, root / "work", max_frames=4)
            photo = {"fs_id": "123", "path": "/来自：iPhone/sample.livp"}
            frames = extractor.extract(photo)
            self.assertGreater(len(frames), 0)
            self.assertEqual(copier.calls, 1)
            self.assertFalse(livp.exists())
            self.assertEqual(extractor.extract(photo), frames)
            self.assertEqual(copier.calls, 1)
    def test_corrupt_video_is_retryable_and_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            livp = root / "broken.livp"
            livp.write_bytes(b"not a zip")

            class Copier:
                def download(self, source_path, destination_dir):
                    return livp

            extractor = VideoFrameExtractor(Copier(), root / "work")
            photo = {"fs_id": "456", "path": "/来自：iPhone/broken.livp"}
            with self.assertRaisesRegex(RuntimeError, "视频抽帧失败"):
                extractor.extract(photo)
            self.assertFalse(livp.exists())


if __name__ == "__main__":
    unittest.main()
