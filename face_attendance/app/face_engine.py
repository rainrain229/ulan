from __future__ import annotations

import base64
import io
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover - allows partial feature use without OpenCV
    cv2 = None  # type: ignore

try:
    from insightface.app import FaceAnalysis
except Exception:
    FaceAnalysis = None  # type: ignore

try:
    import mediapipe as mp
except Exception:
    mp = None  # type: ignore


@dataclass
class FrameMetrics:
    timestamp: float
    ear_left: Optional[float]
    ear_right: Optional[float]
    mar: Optional[float]


@dataclass
class ClientState:
    metrics: List[FrameMetrics] = field(default_factory=list)
    last_seen: float = field(default_factory=lambda: time.time())


class FaceEngine:
    def __init__(self) -> None:
        self._insightface: Optional[FaceAnalysis] = None
        self._mp_face_mesh = None
        self._mp_drawing = None
        self._cache_lock = threading.Lock()
        self._client_cache: Dict[str, ClientState] = {}

    def startup(self) -> None:
        if FaceAnalysis is not None:
            self._insightface = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])  # type: ignore
            self._insightface.prepare(ctx_id=0, det_size=(640, 640))
        if mp is not None:
            self._mp_face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=False, refine_landmarks=True)
            self._mp_drawing = mp.solutions.drawing_utils

    def shutdown(self) -> None:
        if self._mp_face_mesh:
            self._mp_face_mesh.close()

    def decode_base64_image(self, image_base64: str) -> Optional[np.ndarray]:
        try:
            binary = base64.b64decode(image_base64.split(",")[-1])
            img_array = np.frombuffer(binary, dtype=np.uint8)
            if cv2 is None:
                return None
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return image
        except Exception:
            return None

    def extract_face_embedding(self, image_bgr: np.ndarray) -> Optional[np.ndarray]:
        if self._insightface is None:
            return None
        faces = self._insightface.get(image_bgr)
        if not faces:
            return None
        faces.sort(key=lambda f: f.bbox[2] * f.bbox[3] if hasattr(f, "bbox") else 0, reverse=True)
        face = faces[0]
        embedding = getattr(face, "normed_embedding", None)
        if embedding is None:
            return None
        return np.asarray(embedding, dtype=np.float32)

    def _compute_eye_aspect_ratio(self, landmarks: List[Tuple[float, float]]) -> Optional[float]:
        if cv2 is None or len(landmarks) < 6:
            return None
        p2_p6 = np.linalg.norm(np.array(landmarks[1]) - np.array(landmarks[5]))
        p3_p5 = np.linalg.norm(np.array(landmarks[2]) - np.array(landmarks[4]))
        p1_p4 = np.linalg.norm(np.array(landmarks[0]) - np.array(landmarks[3]))
        if p1_p4 == 0:
            return None
        return (p2_p6 + p3_p5) / (2.0 * p1_p4)

    def _compute_mouth_aspect_ratio(self, landmarks: List[Tuple[float, float]]) -> Optional[float]:
        if cv2 is None or len(landmarks) < 8:
            return None
        vertical = np.linalg.norm(np.array(landmarks[2]) - np.array(landmarks[6]))
        horizontal = np.linalg.norm(np.array(landmarks[0]) - np.array(landmarks[4]))
        if horizontal == 0:
            return None
        return vertical / horizontal

    def _update_client_metrics(self, client_id: str, frame_metrics: FrameMetrics) -> None:
        with self._cache_lock:
            state = self._client_cache.get(client_id, ClientState())
            state.metrics.append(frame_metrics)
            state.metrics = [m for m in state.metrics if time.time() - m.timestamp <= 8.0]
            state.last_seen = time.time()
            self._client_cache[client_id] = state

    def _estimate_liveness(self, client_id: str) -> bool:
        with self._cache_lock:
            state = self._client_cache.get(client_id)
            if state is None:
                return False
            series = state.metrics
        if len(series) < 5:
            return False
        ear_left_values = [m.ear_left for m in series if m.ear_left is not None]
        ear_right_values = [m.ear_right for m in series if m.ear_right is not None]
        mar_values = [m.mar for m in series if m.mar is not None]
        def variation(values: List[float]) -> float:
            if not values:
                return 0.0
            return float(np.percentile(values, 90) - np.percentile(values, 10))
        ear_var = max(variation(ear_left_values), variation(ear_right_values))
        mar_var = variation(mar_values)
        return ear_var > 0.055 or mar_var > 0.08

    def analyze_frame_and_get_embedding(self, client_id: str, image_bgr: np.ndarray) -> Tuple[Optional[np.ndarray], bool]:
        ear_left = None
        ear_right = None
        mar = None
        if self._mp_face_mesh is not None and cv2 is not None:
            rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            result = self._mp_face_mesh.process(rgb)
            if result.multi_face_landmarks:
                face_landmarks = result.multi_face_landmarks[0]
                h, w = image_bgr.shape[:2]
                def to_xy(idx: int) -> Tuple[float, float]:
                    lm = face_landmarks.landmark[idx]
                    return lm.x * w, lm.y * h
                left_ids = [33, 160, 158, 133, 153, 144]
                right_ids = [362, 385, 387, 263, 373, 380]
                mouth_ids = [78, 308, 13, 14, 81, 178, 311, 402]
                left_eye = [to_xy(i) for i in left_ids]
                right_eye = [to_xy(i) for i in right_ids]
                mouth = [to_xy(i) for i in mouth_ids]
                ear_left = self._compute_eye_aspect_ratio(left_eye)
                ear_right = self._compute_eye_aspect_ratio(right_eye)
                mar = self._compute_mouth_aspect_ratio(mouth)
        self._update_client_metrics(client_id, FrameMetrics(timestamp=time.time(), ear_left=ear_left, ear_right=ear_right, mar=mar))
        liveness_ok = self._estimate_liveness(client_id)
        embedding = self.extract_face_embedding(image_bgr)
        return embedding, liveness_ok

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)
        if a_norm == 0 or b_norm == 0:
            return 0.0
        return float(np.dot(a, b) / (a_norm * b_norm))