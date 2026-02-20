# app/api/v1/routers/flights.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.v1.deps import get_db
from app import models
from app.schemas import FlightRead, FlightCreate, FlightUpdate, FlightBase

router = APIRouter()

# CRUD


@router.post("/", response_model=FlightRead, status_code=201)
def create_flight(
    flight: FlightCreate,
    db: Session = Depends(get_db),
):
    db_flight = models.Flight(**flight.model_dump())
    db.add(db_flight)
    db.commit()
    db.refresh(db_flight)
    return db_flight


@router.get("/{flight_id}", response_model=FlightRead)
def get_flight(
    flight_id: int,
    db: Session = Depends(get_db),
):
    flight = db.query(models.Flight).get(flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight

@router.put("/{flight_id}", response_model=FlightRead)
def update_flight(
    flight_id: int,
    flight_update: FlightUpdate,
    db: Session = Depends(get_db),
):
    flight = db.query(models.Flight).get(flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    update_data = flight_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flight, field, value)

    db.commit()
    db.refresh(flight)
    return flight


@router.delete("/{flight_id}", status_code=204)
def delete_flight(
    flight_id: int,
    db: Session = Depends(get_db),
):
    flight = db.query(models.Flight).get(flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    db.delete(flight)
    db.commit()
    return None


@router.get("/", response_model=List[FlightRead])
def read_flights(
        origin: str = Query(None),
        dest: str = Query(None),
        limit: int = Query(100, le=1000),
        offset: int = Query(0),
        db: Session = Depends(get_db)
):
    """Filter flights by origin, destination, with pagination"""

    query = db.query(models.Flight)

    if origin:
        query = query.filter(models.Flight.origin == origin)
    if dest:
        query = query.filter(models.Flight.dest == dest)

    return query.offset(offset).limit(limit).all()


@router.get("/stats/{airport}")
def airport_stats(airport: str, db: Session = Depends(get_db)):
    """Quick airport stats"""
    stats = db.query(
        func.count().label("total"),
        func.avg(models.Flight.arr_delay_minutes).label("avg_delay"),
        func.sum(models.Flight.cancelled).label("cancellations")
    ).filter(models.Flight.origin == airport).first()

    return {
        "airport": airport,
        "total_flights": stats.total,
        "avg_arrival_delay": round(float(stats.avg_delay or 0), 1),
        "cancellation_count": stats.cancellations
    }
