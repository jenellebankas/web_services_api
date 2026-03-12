# app/api/v1/routers/keys.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, verify_api_key
from app.models import APIKey

router = APIRouter(prefix="/keys", tags=["authentication"])


class APIKeyCreate(BaseModel):
    name: str


class APIKeyRead(BaseModel):
    id: int
    name: str
    key: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyRevoke(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=APIKeyRead, status_code=201)
def create_api_key(
        payload: APIKeyCreate,
        db: Session = Depends(get_db),
        _auth=Depends(verify_api_key),  # must already have a valid key to create one
):
    """
    Create a new API key. Requires an existing valid X-API-Key header.
    The generated key is only shown once — store it securely.
    """
    new_key = APIKey(
        key=APIKey.generate(),
        name=payload.name,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    return new_key


@router.get("/", response_model=list[APIKeyRevoke])
def list_api_keys(
        db: Session = Depends(get_db),
        _auth=Depends(verify_api_key),
):
    """List all API keys (key values hidden). Requires X-API-Key header."""
    return db.query(APIKey).all()


@router.delete("/{key_id}", status_code=204)
def revoke_api_key(
        key_id: int,
        db: Session = Depends(get_db),
        _auth=Depends(verify_api_key),
):
    """Deactivate an API key by ID. Requires X-API-Key header."""
    record = db.query(APIKey).filter_by(id=key_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="API key not found")
    record.is_active = False
    db.commit()
    return None
