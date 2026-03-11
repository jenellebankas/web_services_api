# app/models.py
from sqlalchemy import Column, Integer, String, Date, DateTime, Float

from .database import Base


# flight base model with all relevant fields
class Flight(Base):
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)
    flight_date = Column(Date, nullable=False, index=True)
    reporting_airline = Column(String(10), nullable=False, index=True)
    flight_num_reporting_airline = Column(Integer, nullable=False)
    origin = Column(String(3), nullable=False, index=True)
    dest = Column(String(3), nullable=False, index=True)

    # TIME VALUES
    crs_dep_time = Column(DateTime, nullable=False)
    dep_time = Column(DateTime, nullable=True)
    crs_arr_time = Column(DateTime, nullable=False)
    arr_time = Column(DateTime, nullable=True)

    # KEY DISRUPTION METRICS
    dep_delay_minutes = Column(Float, nullable=True, index=True)
    arr_delay_minutes = Column(Float, nullable=True, index=True)

    # binary indicator if delay is more than 15 minutes
    dep_del_15 = Column(Integer, nullable=True)
    arr_del_15 = Column(Integer, nullable=True)

    # binary indicator for cancelled
    cancelled = Column(Integer, default=0)

    cancellation_code = Column(String, nullable=True)

    # binary indicator for diversion
    diverted = Column(Integer, default=0)

    # DELAY CAUSES
    carrier_delay = Column(Integer, nullable=True)
    weather_delay = Column(Integer, nullable=True)
    nas_delay = Column(Integer, nullable=True)
    security_delay = Column(Integer, nullable=True)
    late_aircraft_delay = Column(Integer, nullable=True)

    distance = Column(Integer, nullable=True)
