from datetime import datetime, timedelta
from typing import List, Dict, Any
from .db import get_session
from .models import Attendance, Person, PersonRole

DUP_WINDOW_MINUTES = 10

class AttendanceService:
    def _recent_event_exists(self, session, person_id: int, window_minutes: int = DUP_WINDOW_MINUTES) -> bool:
        since = datetime.utcnow() - timedelta(minutes=window_minutes)
        exists = (
            session.query(Attendance)
            .filter(Attendance.person_id == person_id, Attendance.timestamp >= since)
            .first()
            is not None
        )
        return exists

    def record_attendance(self, person_id: int, is_check_in: bool = True) -> None:
        with get_session() as session:
            person = session.query(Person).filter(Person.id == person_id).first()
            if person is None:
                raise ValueError("Person not found")
            if self._recent_event_exists(session, person_id):
                return
            entry = Attendance(person_id=person_id, timestamp=datetime.utcnow(), is_check_in=is_check_in)
            session.add(entry)
            session.commit()

    def student_presence(self, student_id: int) -> None:
        with get_session() as session:
            student = (
                session.query(Person)
                .filter(Person.id == student_id, Person.role == PersonRole.STUDENT)
                .first()
            )
            if student is None:
                raise ValueError("Student not found")
            if self._recent_event_exists(session, student_id):
                return
            entry = Attendance(person_id=student_id, timestamp=datetime.utcnow(), is_check_in=True)
            session.add(entry)
            session.commit()

    def teacher_check_in(self, teacher_id: int) -> None:
        with get_session() as session:
            teacher = session.query(Person).filter(Person.id == teacher_id, Person.role == PersonRole.TEACHER).first()
            if teacher is None:
                raise ValueError("Teacher not found")
            entry = Attendance(person_id=teacher_id, timestamp=datetime.utcnow(), is_check_in=True)
            session.add(entry)
            session.commit()

    def teacher_check_out(self, teacher_id: int) -> None:
        with get_session() as session:
            teacher = session.query(Person).filter(Person.id == teacher_id, Person.role == PersonRole.TEACHER).first()
            if teacher is None:
                raise ValueError("Teacher not found")
            entry = Attendance(person_id=teacher_id, timestamp=datetime.utcnow(), is_check_in=False)
            session.add(entry)
            session.commit()

    def list_attendance(self) -> List[Dict[str, Any]]:
        with get_session() as session:
            rows = (
                session.query(Attendance, Person)
                .join(Person, Attendance.person_id == Person.id)
                .order_by(Attendance.timestamp.desc())
                .limit(200)
                .all()
            )
            return [
                {
                    "id": a.id,
                    "timestamp": a.timestamp.isoformat(),
                    "is_check_in": a.is_check_in,
                    "person_id": p.id,
                    "name": p.name,
                    "role": p.role.value,
                }
                for a, p in rows
            ]