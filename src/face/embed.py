from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np


class FaceError(RuntimeError):
    pass


@dataclass
class FaceResult:
    bbox: tuple[int, int, int, int] | None
    embedding: np.ndarray
    model: str
    detector: str


class FaceEngine:
    def __init__(self, model_name="Facenet512", detector_backend="retinaface"):
        self.model_name = model_name
        self.detector_backend = detector_backend
        try:
            from deepface import DeepFace
        except ImportError as exc:
            raise FaceError("DeepFace is required for face processing; install requirements.txt") from exc
        self._deepface = DeepFace

    def _embed(self, image):
        try:
            reps = self._deepface.represent(
                img_path=image,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                normalization="base",
            )
        except Exception as exc:
            raise FaceError(f"No usable face detected: {exc}") from exc
        if not reps:
            raise FaceError("No face detected")
        rep = reps[0]
        vector = np.asarray(rep["embedding"], dtype=np.float32)
        norm = np.linalg.norm(vector)
        if not norm:
            raise FaceError("Face model returned a zero embedding")
        return vector / norm, tuple(rep.get("facial_area", {}).get(k, 0) for k in ("y", "x", "h", "w"))

    def detect_and_embed(self, path: str | Path) -> FaceResult:
        embedding, area = self._embed(str(path))
        y, x, h, w = area
        return FaceResult((y, x + w, y + h, x), embedding, self.model_name, self.detector_backend)

    def embed_bytes(self, image_bytes: bytes) -> np.ndarray:
        # DeepFace accepts a decoded image array, avoiding temporary files.
        try:
            from PIL import Image
            image = np.asarray(Image.open(BytesIO(image_bytes)).convert("RGB"))
        except Exception as exc:
            raise FaceError(f"Invalid candidate image: {exc}") from exc
        return self._embed(image)[0]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
