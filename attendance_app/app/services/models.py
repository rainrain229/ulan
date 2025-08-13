from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime
from .db import Base

class PersonRole(PyEnum):
    STUDENT = "student"
    TEACHER = "teacher"

class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(Enum(PersonRole), nullable=False)
    # stored path to the enrolled face image
    image_path = Column(String, nullable=False)

    attendance = relationship("Attendance", back_populates="person")

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    is_check_in = Column(Boolean, default=True)

    person = relationship("Person", back_populates="attendance")