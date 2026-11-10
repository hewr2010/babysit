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


if __name__ == "__main__":
    unittest.main()
