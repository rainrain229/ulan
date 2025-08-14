import os
import io
import cv2
import numpy as np
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from .db import get_session
from .models import Person, PersonRole
from PIL import Image


class FaceService:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.model_path = os.path.join(data_dir, "lbph_model.xml")
        self.faces_dir = os.path.join(data_dir, "faces")
        os.makedirs(self.faces_dir, exist_ok=True)
        self.face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.eye_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
        # Use LBPH Face Recognizer
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self._maybe_load_model()

    def _maybe_load_model(self) -> None:
        if os.path.exists(self.model_path):
            try:
                self.recognizer.read(self.model_path)
            except Exception:
                pass

    def _save_model(self) -> None:
        try:
            self.recognizer.write(self.model_path)
        except Exception:
            pass

    def _read_image_bytes(self, image_bytes: bytes) -> np.ndarray:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    def _detect_face(self, bgr: np.ndarray) -> Optional[np.ndarray]:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        faces = self.face_detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            return None
        # take the largest face
        x, y, w, h = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
        face_roi = gray[y : y + h, x : x + w]
        face_resized = cv2.resize(face_roi, (200, 200))
        return face_resized

    def _liveness_heuristic(self, face_gray_200: np.ndarray) -> bool:
        # Simple liveness: image sharpness + eye detection in upper half
        if face_gray_200 is None or face_gray_200.size == 0:
            return False
        lap_var = cv2.Laplacian(face_gray_200, cv2.CV_64F).var()
        if lap_var < 30.0:
            return False
        upper = face_gray_200[:100, :]
        eyes = self.eye_detector.detectMultiScale(upper, scaleFactor=1.2, minNeighbors=5, minSize=(15, 15))
        return len(eyes) >= 1

    def register_person(self, name: str, role: PersonRole, image_bytes: bytes) -> int:
        bgr = self._read_image_bytes(image_bytes)
        face_img = self._detect_face(bgr)
        if face_img is None:
            raise ValueError("No face detected")
        if not self._liveness_heuristic(face_img):
            raise ValueError("Liveness check failed")

        with get_session() as session:
            person = Person(name=name, role=role, image_path="")
            session.add(person)
            session.commit()
            session.refresh(person)

            # save face image
            face_path = os.path.join(self.faces_dir, f"person_{person.id}.png")
            cv2.imwrite(face_path, face_img)
            person.image_path = face_path
            session.commit()

            # retrain recognizer with all faces
            self._retrain(session)
            return person.id

    def _retrain(self, session: Session) -> None:
        persons = session.query(Person).all()
        images = []
        labels = []
        for p in persons:
            if p.image_path and os.path.exists(p.image_path):
                img = cv2.imread(p.image_path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                images.append(img)
                labels.append(p.id)
        if len(images) >= 1:
            try:
                self.recognizer.train(images, np.array(labels))
                self._save_model()
            except cv2.error:
                pass

    def recognize(self, image_bytes: bytes) -> Optional[Tuple[Person, float, bool]]:
        bgr = self._read_image_bytes(image_bytes)
        face_img = self._detect_face(bgr)
        if face_img is None:
            return None
        live_ok = self._liveness_heuristic(face_img)
        try:
            label, confidence = self.recognizer.predict(face_img)
        except cv2.error:
            return None
        with get_session() as session:
            person = session.query(Person).filter(Person.id == label).first()
        return (person, float(confidence), live_ok) if person else None