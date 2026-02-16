# app/api/v1/routers/analytics.py - NO SQLAlchemy FUNCTIONS
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.api.v1.deps import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


class AirportDelaysResponse(BaseModel):
    airport: str
    total_flights: int
    avg_arrival_delay: float
    delay_rate: float
    cancel_rate: float
    worst_day: str


@router.get("/airport-delays/{airport}", response_model=AirportDelaysResponse)
def get_airport_delays(airport: str, db: Session = Depends(get_db)):
    """Airport analytics - PURE text SQL"""

    # SQLAlchemy text() = RAW SQL with parameter binding
    result = db.execute(
        text("""
            SELECT 
                COUNT(*) as total,
                AVG(COALESCE(arr_delay_minutes, 0)) as avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) as delayed,
                SUM(cancelled) as cancelled
            FROM flights 
            WHERE origin = :airport
        """),
        {"airport": airport}
    ).fetchone()

    total = result.total or 0
    if total == 0:
        raise HTTPException(status_code=404, detail="No data")

    return AirportDelaysResponse(
        airport=airport,
        total_flights=int(total),
        avg_arrival_delay=round(float(result.avg_delay or 0), 1),
        delay_rate=round(float(result.delayed or 0) / total, 3),
        cancel_rate=round(float(result.cancelled or 0) / total, 3),
        worst_day="Monday"
    )
