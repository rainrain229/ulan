from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    student_code: str
    full_name: str
    class_name: Optional[str] = None


class StudentOut(BaseModel):
    id: int
    student_code: str
    full_name: str
    class_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    session_code: str = Field(description="Human-friendly code to identify the session")
    title: str


class SessionOut(BaseModel):
    id: int
    session_code: str
    title: str
    starts_at: datetime
    ends_at: Optional[datetime]

    class Config:
        from_attributes = True


class FramePayload(BaseModel):
    client_id: str
    session_code: Optional[str] = None
    image_base64: str


class RecognizeResult(BaseModel):
    recognized: bool
    liveness_ok: bool
    student: Optional[StudentOut]
    similarity: Optional[float]
    message: Optional[str] = None