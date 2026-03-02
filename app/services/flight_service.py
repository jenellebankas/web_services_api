from typing import List, Dict, Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.schemas import FlightRead, FlightCreate, FlightUpdate


class FlightService:
    def __init__(self, db: Session):
        self.db = db

    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Helper: Safely convert to int with default"""
        try:
            return int(value or default)
        except (ValueError, TypeError):
            return default

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Helper: Safely convert to float with default"""
        try:
            return float(value or default)
        except (ValueError, TypeError):
            return default

    # CRUD Operations
    def create_flight(self, flight_data: FlightCreate) -> FlightRead:
        """Create new flight record"""
        try:
            db_flight = models.Flight(**flight_data.model_dump())
            self.db.add(db_flight)
            self.db.commit()
            self.db.refresh(db_flight)
            return FlightRead.from_orm(db_flight)  # Explicit Pydantic conversion
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Flight creation failed: {str(e)}")

    def get_flight(self, flight_id: int) -> FlightRead:
        """Get single flight by ID"""
        if flight_id <= 0:
            raise ValueError("Flight ID must be positive")

        flight = self.db.query(models.Flight).get(flight_id)
        if not flight:
            raise ValueError(f"Flight {flight_id} not found")
        return FlightRead.from_orm(flight)

    def update_flight(self, flight_id: int, flight_update: FlightUpdate) -> FlightRead:
        """Update existing flight"""
        if flight_id <= 0:
            raise ValueError("Flight ID must be positive")

        flight = self.db.query(models.Flight).get(flight_id)
        if not flight:
            raise ValueError(f"Flight {flight_id} not found")

        try:
            update_data = flight_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(flight, field, value)
            self.db.commit()
            self.db.refresh(flight)
            return FlightRead.from_orm(flight)
        except Exception:
            self.db.rollback()
            raise ValueError("Flight update failed")

    def delete_flight(self, flight_id: int) -> None:
        """Delete flight by ID"""
        if flight_id <= 0:
            raise ValueError("Flight ID must be positive")

        flight = self.db.query(models.Flight).get(flight_id)
        if not flight:
            raise ValueError(f"Flight {flight_id} not found")

        try:
            self.db.delete(flight)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise ValueError("Flight deletion failed")

    # Query Operations
    def get_flights(self, origin: Optional[str] = None, dest: Optional[str] = None,
                    limit: int = 100, offset: int = 0) -> List[FlightRead]:
        """Filter flights with pagination"""
        if limit < 1 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        if origin:
            origin = origin.strip().upper()
            if len(origin) != 3:
                raise ValueError("Origin must be 3-letter airport code")

        if dest:
            dest = dest.strip().upper()
            if len(dest) != 3:
                raise ValueError("Destination must be 3-letter airport code")

        query = self.db.query(models.Flight)

        if origin:
            query = query.filter(models.Flight.origin == origin)
        if dest:
            query = query.filter(models.Flight.dest == dest)

        flights = query.offset(offset).limit(limit).all()
        return [FlightRead.from_orm(f) for f in flights]

    def get_airport_stats(self, airport: str) -> Dict[str, Any]:
        """Airport performance statistics"""
        airport = airport.strip().upper()
        if len(airport) != 3:
            raise ValueError("Airport code must be 3 letters")

        stats = self.db.query(
            func.count().label("total_flights"),
            func.avg(func.coalesce(models.Flight.arr_delay_minutes, 0)).label("avg_delay"),
            func.sum(models.Flight.cancelled).label("cancellations"),
            func.sum(func.case((models.Flight.arr_del_15 == 1, 1), else_=0)).label("delayed_flights")
        ).filter(models.Flight.origin == airport).first()

        if not stats or stats.total_flights == 0:
            raise ValueError(f"No data for airport {airport}")

        return {
            "airport": airport,
            "total_flights": self._safe_int(stats.total_flights),
            "avg_arrival_delay": round(self._safe_float(stats.avg_delay), 1),
            "cancellation_count": self._safe_int(stats.cancellations),
            "delayed_flights": self._safe_int(stats.delayed_flights),
            "delay_rate": round(self._safe_float(stats.delayed_flights) / max(self._safe_int(stats.total_flights), 1),
                                3)
        }
