# app/api/v1/deps.py
from typing import Generator

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import APIKey


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


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(
        api_key: str = Security(api_key_header),
        db: Session = Depends(get_db),
) -> APIKey:
    """
    Validate the X-API-Key header against the api_keys table.
    Raises 401 if missing, 403 if invalid or inactive.
    Used as a dependency on write endpoints (POST, PUT, DELETE).
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Pass your key in the X-API-Key header.",
        )
    record = db.query(APIKey).filter_by(key=api_key, is_active=True).first()
    if not record:
        raise HTTPException(
            status_code=403,
            detail="Invalid or inactive API key.",
        )
    return record
