from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import os
from .services.db import init_db, get_session
from .services.models import PersonRole
from .services.face_service import FaceService
from .services.attendance_service import AttendanceService

app = FastAPI(title="School Face Attendance")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
STATIC_DIR = os.path.join(PARENT_DIR, "static")
TEMPLATES_DIR = os.path.join(PARENT_DIR, "templates")
DATA_DIR = os.path.join(PARENT_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

init_db()
face_service = FaceService(data_dir=DATA_DIR)
attendance_service = AttendanceService()

class RegisterPersonRequest(BaseModel):
    name: str
    role: PersonRole

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.post("/api/register")
async def register_person(name: str = Form(...), role: PersonRole = Form(...), image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        person_id = face_service.register_person(name=name, role=role, image_bytes=image_bytes)
        return {"ok": True, "person_id": person_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/recognize")
async def recognize(image: UploadFile = File(...)):
    image_bytes = await image.read()
    result = face_service.recognize(image_bytes=image_bytes)
    if result is None:
        return {"ok": True, "recognized": False}
    person, confidence, liveness_ok = result
    if not liveness_ok:
        return {"ok": True, "recognized": False, "reason": "liveness_failed"}
    # Auto record student presence (deduped). For teachers, use IN/OUT buttons.
    if person.role == PersonRole.STUDENT:
        attendance_service.student_presence(student_id=person.id)
    return {
        "ok": True,
        "recognized": True,
        "person_id": person.id,
        "name": person.name,
        "role": person.role.value,
        "confidence": confidence,
    }

@app.post("/api/teacher/in")
async def teacher_in(teacher_id: int = Form(...)):
    attendance_service.teacher_check_in(teacher_id=teacher_id)
    return {"ok": True}

@app.post("/api/teacher/out")
async def teacher_out(teacher_id: int = Form(...)):
    attendance_service.teacher_check_out(teacher_id=teacher_id)
    return {"ok": True}

@app.get("/api/attendance")
async def get_attendance():
    return attendance_service.list_attendance()