import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from babysit.face_matcher import InsightFaceMatcher


class FakeFace:
    normed_embedding = np.array([1.0, 0.0])


class FakeFaceAnalysis:
    def __init__(self, **kwargs):
        pass

    def prepare(self, **kwargs):
        pass

    def get(self, image):
        if image.mean() > 10:
            return [FakeFace(), FakeFace()]
        return [FakeFace()]


class ReferencePhotoTests(unittest.TestCase):
    @patch("insightface.app.FaceAnalysis", FakeFaceAnalysis)
    def test_reference_photos_require_exactly_one_face(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, value in [("single.jpg", 0), ("group.jpg", 255)]:
                Image.new("RGB", (2, 2), (value, 0, 0)).save(Path(directory) / name)
            matcher = InsightFaceMatcher(directory)

        self.assertEqual(len(matcher._reference_embeddings), 1)

    def test_grid_crop_can_find_smaller_face(self):
        from babysit.face_matcher import FaceMatch

        matcher = InsightFaceMatcher.__new__(InsightFaceMatcher)
        with tempfile.TemporaryDirectory() as directory:
            matcher.crop_dir = Path(directory) / "crops"
            image_path = Path(directory) / "source.jpg"
            Image.new("RGB", (100, 100), "white").save(image_path)
            scores = iter([None, None, 0.5007, None, None])

            def match(image_bytes):
                score = next(scores)
                return FaceMatch(score, 1 if score is not None else 0)

            matcher.match = match
            result = matcher.match_with_crops(image_path)

        self.assertEqual(result.score, 0.5007)
        self.assertIn("grid-1", result.best_frame_path)
        self.assertEqual(result.frame_count, 5)


if __name__ == "__main__":
    unittest.main()
