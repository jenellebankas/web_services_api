# app/api/v1/deps.py
from app.database import SessionLocal
from sqlalchemy.orm import Session
from typing import Generator


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.
    Auto-closes after request (industry standard).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
