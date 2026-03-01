from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from app import models
from app.schemas import FlightRead, FlightCreate, FlightUpdate


class FlightService:
    def __init__(self, db: Session):
        self.db = db

    # CRUD Operations
    def create_flight(self, flight_data: FlightCreate) -> FlightRead:
        """Create new flight record"""
        db_flight = models.Flight(**flight_data.model_dump())
        self.db.add(db_flight)
        self.db.commit()
        self.db.refresh(db_flight)
        return db_flight

    def get_flight(self, flight_id: int) -> FlightRead:
        """Get single flight by ID"""
        flight = self.db.query(models.Flight).get(flight_id)
        if not flight:
            raise ValueError(f"Flight {flight_id} not found")
        return flight

    def update_flight(self, flight_id: int, flight_update: FlightUpdate) -> FlightRead:
        """Update existing flight"""
        flight = self.db.query(models.Flight).get(flight_id)
        if not flight:
            raise ValueError(f"Flight {flight_id} not found")

        update_data = flight_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(flight, field, value)

        self.db.commit()
        self.db.refresh(flight)
        return flight

    def delete_flight(self, flight_id: int) -> None:
        """Delete flight by ID"""
        flight = self.db.query(models.Flight).get(flight_id)
        if not flight:
            raise ValueError(f"Flight {flight_id} not found")

        self.db.delete(flight)
        self.db.commit()

    # Query Operations
    def get_flights(self, origin: str = None, dest: str = None, limit: int = 100, offset: int = 0) -> List[FlightRead]:
        """Filter flights with pagination"""
        query = self.db.query(models.Flight)

        if origin:
            query = query.filter(models.Flight.origin == origin)
        if dest:
            query = query.filter(models.Flight.dest == dest)

        return query.offset(offset).limit(limit).all()

    def get_airport_stats(self, airport: str) -> Dict[str, Any]:
        """Airport performance statistics"""
        stats = self.db.query(
            func.count().label("total"),
            func.avg(models.Flight.arr_delay_minutes).label("avg_delay"),
            func.sum(models.Flight.cancelled).label("cancellations")
        ).filter(models.Flight.origin == airport).first()

        if not stats or stats.total == 0:
            raise ValueError("No data for airport")

        return {
            "airport": airport,
            "total_flights": int(stats.total),
            "avg_arrival_delay": round(float(stats.avg_delay or 0), 1),
            "cancellation_count": int(stats.cancellations or 0)
        }
