import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_PATH = os.getenv("ATTENDANCE_DB_PATH", "sqlite:////workspace/attendance_app/data/attendance.db")
# Ensure DB directory exists for sqlite path
try:
    if DB_PATH.startswith("sqlite:///"):
        fs_path = DB_PATH.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(fs_path), exist_ok=True)
except Exception:
    pass

engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_session():
    return SessionLocal()


def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(engine)