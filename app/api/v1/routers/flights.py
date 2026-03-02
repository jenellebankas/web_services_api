from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.schemas import FlightRead, FlightCreate, FlightUpdate
from app.services.flight_service import FlightService

router = APIRouter(prefix="/flights", tags=["flights"])  # Add prefix for consistency


# 1. CREATE FLIGHT (POST)
@router.post("/", response_model=FlightRead, status_code=201)
def create_flight(
        flight: FlightCreate,
        db: Session = Depends(get_db)
):
    """Create new flight record"""
    service = FlightService(db)
    try:
        return service.create_flight(flight)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Flight creation failed: {str(e)}")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


# 2. GET SINGLE FLIGHT
@router.get("/{flight_id}", response_model=FlightRead)
def get_flight(
        flight_id: int = Query(..., gt=0),  # Must be positive integer
        db: Session = Depends(get_db)
):
    """Get flight by ID"""
    service = FlightService(db)
    try:
        return service.get_flight(flight_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Flight not found")


# 3. UPDATE FLIGHT
@router.put("/{flight_id}", response_model=FlightRead)
def update_flight(
        flight_id: int = Query(..., gt=0),
        flight_update: FlightUpdate,
        db: Session = Depends(get_db)
):
    """Update existing flight"""
    service = FlightService(db)
    try:
        return service.update_flight(flight_id, flight_update)
    except ValueError:
        raise HTTPException(status_code=404, detail="Flight not found")
    except Exception:
        raise HTTPException(status_code=500, detail="Update failed")


# 4. DELETE FLIGHT
@router.delete("/{flight_id}", status_code=204)
def delete_flight(
        flight_id: int = Query(..., gt=0),
        db: Session = Depends(get_db)
):
    """Delete flight by ID"""
    service = FlightService(db)
    try:
        service.delete_flight(flight_id)
        return None
    except ValueError:
        raise HTTPException(status_code=404, detail="Flight not found")


# 5. LIST FLIGHTS (with filtering/pagination)
@router.get("/", response_model=List[FlightRead])
def read_flights(
        origin: Optional[str] = Query(None, min_length=3, max_length=3),
        dest: Optional[str] = Query(None, min_length=3, max_length=3),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db)
):
    """Filter flights by origin, destination, with pagination"""
    service = FlightService(db)
    try:
        return service.get_flights(origin=origin.strip().upper() if origin else None,
                                   dest=dest.strip().upper() if dest else None,
                                   limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# 6. AIRPORT STATS
@router.get("/stats/{airport}")
def airport_stats(
        airport: str = Query(..., min_length=3, max_length=3),
        db: Session = Depends(get_db)
):
    """Airport performance statistics"""
    airport = airport.strip().upper()
    service = FlightService(db)
    try:
        return service.get_airport_stats(airport)
    except ValueError:
        raise HTTPException(status_code=404, detail="No data for airport")
