from __future__ import annotations

import base64
import io
from datetime import datetime
from typing import List, Optional

import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from pathlib import Path

from .db import Base, engine, get_db
from .face_engine import FaceEngine
from .models import AttendanceRecord, AttendanceSession, FaceEmbedding, Student
from .schemas import FramePayload, RecognizeResult, SessionCreate, SessionOut, StudentCreate, StudentOut

app = FastAPI(title="Face Attendance System", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

face_engine = FaceEngine()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    face_engine.startup()


@app.on_event("shutdown")
def on_shutdown() -> None:
    face_engine.shutdown()


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/api/sessions", response_model=SessionOut)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)) -> SessionOut:
    exists = db.scalar(select(AttendanceSession).where(AttendanceSession.session_code == payload.session_code))
    if exists is not None:
        raise HTTPException(status_code=400, detail="Session code already exists")
    session = AttendanceSession(session_code=payload.session_code, title=payload.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@app.post("/api/register_student", response_model=StudentOut)
async def register_student(
    student_code: str = Form(...),
    full_name: str = Form(...),
    class_name: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> StudentOut:
    existing = db.scalar(select(Student).where(Student.student_code == student_code))
    if existing is not None:
        raise HTTPException(status_code=400, detail="Student code already exists")
    student = Student(student_code=student_code, full_name=full_name, class_name=class_name)
    db.add(student)
    db.commit()
    db.refresh(student)

    imported = 0
    for f in files:
        content = await f.read()
        try:
            import cv2  # local import to avoid hard dependency when unavailable
            img_array = np.frombuffer(content, dtype=np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception:
            image = None
        if image is None:
            continue
        embedding = face_engine.extract_face_embedding(image)
        if embedding is None:
            continue
        vec_bytes = np.asarray(embedding, dtype=np.float32).tobytes()
        emb = FaceEmbedding(student_id=student.id, vector=vec_bytes)
        db.add(emb)
        imported += 1
    if imported == 0:
        db.rollback()
        raise HTTPException(status_code=400, detail="No faces detected in uploaded images")
    db.commit()
    db.refresh(student)
    return student


@app.post("/api/recognize_frame", response_model=RecognizeResult)
async def recognize_frame(payload: FramePayload, db: Session = Depends(get_db)) -> RecognizeResult:
    image = face_engine.decode_base64_image(payload.image_base64)
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image data")
    embedding, liveness_ok = face_engine.analyze_frame_and_get_embedding(payload.client_id, image)
    if embedding is None:
        return RecognizeResult(recognized=False, liveness_ok=liveness_ok, student=None, similarity=None, message="No face detected")

    embeddings = db.execute(select(FaceEmbedding.student_id, FaceEmbedding.vector)).all()
    if not embeddings:
        return RecognizeResult(recognized=False, liveness_ok=liveness_ok, student=None, similarity=None, message="No enrolled students")

    best_student_id = None
    best_similarity = -1.0
    for student_id, vec_bytes in embeddings:
        vec = np.frombuffer(vec_bytes, dtype=np.float32)
        sim = face_engine.cosine_similarity(embedding, vec)
        if sim > best_similarity:
            best_similarity = sim
            best_student_id = student_id

    threshold = 0.45
    if best_student_id is None or best_similarity < threshold:
        return RecognizeResult(recognized=False, liveness_ok=liveness_ok, student=None, similarity=float(best_similarity), message="Face not recognized")

    student = db.get(Student, best_student_id)
    if student is None:
        return RecognizeResult(recognized=False, liveness_ok=liveness_ok, student=None, similarity=float(best_similarity), message="Student not found")

    session: Optional[AttendanceSession] = None
    if payload.session_code:
        session = db.scalar(select(AttendanceSession).where(AttendanceSession.session_code == payload.session_code))
        if session is None:
            session = AttendanceSession(session_code=payload.session_code, title=f"Session {payload.session_code}")
            db.add(session)
            db.commit()
            db.refresh(session)
    else:
        session = db.scalar(select(AttendanceSession).order_by(AttendanceSession.id.desc()))
        if session is None:
            session = AttendanceSession(session_code="default", title="Default Session")
            db.add(session)
            db.commit()
            db.refresh(session)

    exists = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.student_id == student.id,
        )
    )
    if exists is None and liveness_ok:
        record = AttendanceRecord(student_id=student.id, session_id=session.id, similarity=float(best_similarity))
        db.add(record)
        db.commit()

    return RecognizeResult(
        recognized=True,
        liveness_ok=liveness_ok,
        student=StudentOut.model_validate(student),
        similarity=float(best_similarity),
        message=None,
    )


@app.get("/api/students", response_model=List[StudentOut])
def list_students(db: Session = Depends(get_db)) -> List[StudentOut]:
    rows = db.scalars(select(Student).order_by(Student.created_at.desc())).all()
    return [StudentOut.model_validate(s) for s in rows]