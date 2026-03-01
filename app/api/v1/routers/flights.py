from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.api.v1.deps import get_db
from app.services.flight_service import FlightService
from app.schemas import FlightRead, FlightCreate, FlightUpdate

router = APIRouter()


@router.post("/", response_model=FlightRead, status_code=201)
def create_flight(flight: FlightCreate, db: Session = Depends(get_db)):
    service = FlightService(db)
    try:
        return service.create_flight(flight)
    except ValueError:
        raise HTTPException(status_code=404, detail="Flight creation failed")


@router.get("/{flight_id}", response_model=FlightRead)
def get_flight(flight_id: int, db: Session = Depends(get_db)):
    service = FlightService(db)
    try:
        return service.get_flight(flight_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Flight not found")


@router.put("/{flight_id}", response_model=FlightRead)
def update_flight(flight_id: int, flight_update: FlightUpdate, db: Session = Depends(get_db)):
    service = FlightService(db)
    try:
        return service.update_flight(flight_id, flight_update)
    except ValueError:
        raise HTTPException(status_code=404, detail="Flight not found")


@router.delete("/{flight_id}", status_code=204)
def delete_flight(flight_id: int, db: Session = Depends(get_db)):
    service = FlightService(db)
    try:
        service.delete_flight(flight_id)
        return None
    except ValueError:
        raise HTTPException(status_code=404, detail="Flight not found")


@router.get("/", response_model=List[FlightRead])
def read_flights(
    origin: str = Query(None),
    dest: str = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    service = FlightService(db)
    return service.get_flights(origin, dest, limit, offset)


@router.get("/stats/{airport}")
def airport_stats(airport: str, db: Session = Depends(get_db)):
    service = FlightService(db)
    try:
        return service.get_airport_stats(airport)
    except ValueError:
        raise HTTPException(status_code=404, detail="No data for airport")
