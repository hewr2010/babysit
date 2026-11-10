from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class FaceMatch:
    score: float | None
    face_count: int


@dataclass(frozen=True)
class VideoFaceMatch(FaceMatch):
    supporting_frames: int
    frame_count: int
    best_frame_path: str | None


class InsightFaceMatcher:
    def __init__(self, reference_dir, model_name="buffalo_l", model_dir=None):
        self.reference_dir = Path(reference_dir)
        self.model_name = model_name
        self.model_dir = Path(model_dir) if model_dir else None
        self._app = None
        self._reference_embeddings = []
        self._load()

    def _load(self):
        try:
            import numpy as np
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise RuntimeError(
                "缺少人脸识别依赖，请执行 uv pip install -e '.[photo-sync]'"
            ) from exc

        self._np = np
        reference_paths = sorted(
            path
            for path in self.reference_dir.iterdir()
            if path.is_file()
            and path.suffix.lower()
            in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
        ) if self.reference_dir.exists() else []
        if not reference_paths:
            raise RuntimeError(f"请在 {self.reference_dir} 放入女儿的参考照片")

        options = {"providers": ["CPUExecutionProvider"]}
        if self.model_dir:
            options["root"] = str(self.model_dir)
        self._app = FaceAnalysis(name=self.model_name, **options)
        self._app.prepare(ctx_id=-1, det_size=(640, 640))
        for path in reference_paths:
            image = self._read_image(path.read_bytes())
            faces = self._app.get(image)
            if len(faces) != 1:
                print(f"参考照片需且只需包含一张人脸，已跳过：{path}")
                continue
            face = faces[0]
            embedding = face.normed_embedding
            self._reference_embeddings.append(embedding / np.linalg.norm(embedding))
        if not self._reference_embeddings:
            raise RuntimeError("参考照片中没有检测到可用人脸，请更换清晰正脸照片")

    def _read_image(self, image_bytes):
        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb = image.convert("RGB")
            return self._np.array(rgb)[:, :, ::-1]

    def match(self, image_bytes):
        image = self._read_image(image_bytes)
        faces = self._app.get(image)
        if not faces:
            return FaceMatch(score=None, face_count=0)
        references = self._np.stack(self._reference_embeddings)
        best_score = -1.0
        for face in faces:
            embedding = face.normed_embedding
            embedding = embedding / self._np.linalg.norm(embedding)
            score = float(self._np.max(references @ embedding))
            best_score = max(best_score, score)
        return FaceMatch(score=best_score, face_count=len(faces))

    def match_frames(self, frame_paths, support_threshold=0.35):
        best_score = None
        best_frame_path = None
        max_faces = 0
        supporting_frames = 0
        frame_paths = list(frame_paths)
        for path in frame_paths:
            match = self.match(Path(path).read_bytes())
            max_faces = max(max_faces, match.face_count)
            if match.score is None:
                continue
            if match.score >= support_threshold:
                supporting_frames += 1
            if best_score is None or match.score > best_score:
                best_score = match.score
                best_frame_path = str(path)
        return VideoFaceMatch(
            score=best_score,
            face_count=max_faces,
            supporting_frames=supporting_frames,
            frame_count=len(frame_paths),
            best_frame_path=best_frame_path,
        )
