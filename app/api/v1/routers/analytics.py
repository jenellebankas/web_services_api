# app/api/v1/routers/analytics.py
from app.schemas import DisruptionScoreResponse, YearOverYearResponse
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


@router.get("/disruption-score/{airport}", response_model=DisruptionScoreResponse)
def get_disruption_score(airport: str, db: Session = Depends(get_db)):
    # Reuse same structure but compute extra fields
    result = db.execute(
        text("""
            SELECT 
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(cancelled) AS cancelled,
                COUNT(*) AS total
            FROM flights
            WHERE origin = :airport
        """),
        {"airport": airport}
    ).fetchone()

    if not result or result.total == 0:
        raise HTTPException(status_code=404, detail="No data")

    total = result.total
    avg_delay = float(result.avg_delay or 0)
    delay_freq = float(result.delayed or 0) / total
    cancel_freq = float(result.cancelled or 0) / total

    # Simple disruption formula (explain this in your report)
    disruption_score = max(
        0.0,
        100.0 - (avg_delay * 1.5 + delay_freq * 50.0 + cancel_freq * 80.0)
    )

    # For now, keep top_delay_cause simple; you can improve later
    top_delay_cause = "Carrier"

    return DisruptionScoreResponse(
        airport=airport,
        disruption_score=round(disruption_score, 1),
        delay_frequency=round(delay_freq, 3),
        cancel_frequency=round(cancel_freq, 3),
        top_delay_cause=top_delay_cause,
    )


@router.get("/year-over-year/{airport}", response_model=YearOverYearResponse)
def get_year_over_year(airport: str, db: Session = Depends(get_db)):
    # 2023 stats
    res_2023 = db.execute(
        text("""
            SELECT 
                COUNT(*) AS total,
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(cancelled) AS cancelled
            FROM flights
            WHERE origin = :airport
              AND strftime('%Y', flight_date) = '2023'
        """),
        {"airport": airport}
    ).fetchone()

    # 2024 stats
    res_2024 = db.execute(
        text("""
            SELECT 
                COUNT(*) AS total,
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(cancelled) AS cancelled
            FROM flights
            WHERE origin = :airport
              AND strftime('%Y', flight_date) = '2024'
        """),
        {"airport": airport}
    ).fetchone()

    if (not res_2023 or res_2023.total == 0) and (not res_2024 or res_2024.total == 0):
        raise HTTPException(status_code=404, detail="No year-over-year data")

    def build_year_dict(row):
        if not row or row.total == 0:
            return {
                "total_flights": 0,
                "avg_arrival_delay": 0.0,
                "delay_rate": 0.0,
                "cancel_rate": 0.0,
            }
        total = row.total
        avg_delay = float(row.avg_delay or 0)
        delay_rate = float(row.delayed or 0) / total
        cancel_rate = float(row.cancelled or 0) / total
        return {
            "total_flights": int(total),
            "avg_arrival_delay": round(avg_delay, 1),
            "delay_rate": round(delay_rate, 3),
            "cancel_rate": round(cancel_rate, 3),
        }

    year_2023 = build_year_dict(res_2023)
    year_2024 = build_year_dict(res_2024)

    # Improvement defined as reduction in delay_rate (%)
    if year_2023["delay_rate"] > 0:
        improvement_pct = (
            (year_2023["delay_rate"] - year_2024["delay_rate"])
            / year_2023["delay_rate"]
            * 100.0
        )
    else:
        improvement_pct = 0.0

    return YearOverYearResponse(
        airport=airport,
        year_2023=year_2023,
        year_2024=year_2024,
        improvement_pct=round(improvement_pct, 1),
    )

