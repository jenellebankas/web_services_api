from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.auth.dependencies import get_db
from .. import models, schemas

router = APIRouter()


@router.get("/user/{user_id}/daily", response_model=list[schemas.DailyWellbeingRead])
def list_daily_wellbeing(user_id: int, db: Session = Depends(get_db)):
    records = (
        db.query(models.DailyWellbeing)
        .filter(models.DailyWellbeing.user_id == user_id)
        .order_by(models.DailyWellbeing.date.desc())
        .all()
    )
    return records
