# app/schemas.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime


# ========== FLIGHT SCHEMAS ==========

class FlightBase(BaseModel):
    flight_date: date
    reporting_airline: str
    flight_num_reporting_airline: int
    origin: str
    dest: str
    crs_dep_time: datetime
    dep_time: Optional[datetime] = None
    crs_arr_time: datetime
    arr_time: Optional[datetime] = None
    dep_delay_minutes: Optional[int] = None
    arr_delay_minutes: Optional[int] = None
    dep_del_15: Optional[int] = None
    arr_del_15: Optional[int] = None
    cancelled: int = 0
    cancellation_code: Optional[str] = None
    diverted: int = 0
    carrier_delay: Optional[int] = None
    weather_delay: Optional[int] = None
    nas_delay: Optional[int] = None
    security_delay: Optional[int] = None
    late_aircraft_delay: Optional[int] = None
    distance: Optional[int] = None


# -------- For POST / create --------
class FlightCreate(FlightBase):
    """Used when creating a new flight."""
    pass

# -------- For PUT/PATCH / update --------


class FlightUpdate(BaseModel):
    """Used when updating an existing flight (all fields optional)."""
    flight_date: Optional[date] = None
    reporting_airline: Optional[str] = None
    flight_num_reporting_airline: Optional[int] = None
    origin: Optional[str] = None
    dest: Optional[str] = None
    crs_dep_time: Optional[datetime] = None
    dep_time: Optional[datetime] = None
    crs_arr_time: Optional[datetime] = None
    arr_time: Optional[datetime] = None
    dep_delay_minutes: Optional[float] = None
    arr_delay_minutes: Optional[float] = None
    dep_del_15: Optional[int] = None
    arr_del_15: Optional[int] = None
    cancelled: Optional[int] = None
    cancellation_code: Optional[str] = None
    diverted: Optional[int] = None
    carrier_delay: Optional[float] = None
    weather_delay: Optional[float] = None
    nas_delay: Optional[float] = None
    security_delay: Optional[float] = None
    late_aircraft_delay: Optional[float] = None
    distance: Optional[float] = None


class FlightRead(FlightBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ========== ANALYTICS RESPONSE SCHEMAS ==========

class AirportDelaysResponse(BaseModel):
    airport: str
    total_flights: int
    avg_arrival_delay: float
    delay_rate: float
    cancel_rate: float
    worst_day: str

    model_config = ConfigDict(from_attributes=True)


class DisruptionScoreResponse(BaseModel):
    airport: str
    disruption_score: float
    delay_frequency: float
    cancel_frequency: float
    top_delay_cause: str

    model_config = ConfigDict(from_attributes=True)


class YearOverYearResponse(BaseModel):
    airport: str
    year_2023: dict
    year_2024: dict
    improvement_pct: float

    model_config = ConfigDict(from_attributes=True)


class AirportComparisonItem(BaseModel):
    airport: str
    total_flights: int
    avg_arrival_delay: float
    delay_rate: float
    cancel_rate: float


class AirportComparisonResponse(BaseModel):
    year: int
    airports: List[AirportComparisonItem]


class HourlyPatternItem(BaseModel):
    hour: int  # 0–23
    avg_dep_delay: float
    delay_rate: float


class DailyPatternResponse(BaseModel):
    airport: str
    year: int
    hours: List[HourlyPatternItem]


class WeeklyPatternItem(BaseModel):
    dow: str  # "Mon", "Tue", etc.
    avg_arr_delay: float
    delay_rate: float
    cancel_rate: float


class WeeklyPatternResponse(BaseModel):
    airport: str
    year: int
    days: List[WeeklyPatternItem]


class DelayCauseItem(BaseModel):
    cause: str
    delay_minutes: int
    pct_of_total: float


class DelayCauseBreakdownResponse(BaseModel):
    airport: str
    year: int
    total_delayed_flights: int
    total_delay_minutes: int
    causes: List[DelayCauseItem]


class LeaderboardItem(BaseModel):
    airport: str
    otp_pct: float
    delay_rate: float
    total_flights: int


class PunctualityLeaderboardResponse(BaseModel):
    year: int
    top_airports: List[LeaderboardItem]
    bottom_airports: List[LeaderboardItem]


class BestTimeItem(BaseModel):
    hour: int  # 0-23 (military time)
    avg_dep_delay: float
    delay_rate: float
    total_flights: int


class BestTimeResponse(BaseModel):
    airport: str
    year: int
    best_hours: List[BestTimeItem]
    worst_hours: List[BestTimeItem]
    insight: str


class RouteRiskItem(BaseModel):
    dest: str
    risk_score: float
    delay_rate: float
    avg_arr_delay: float
    cancel_rate: float
    total_flights: int


class RouteRiskResponse(BaseModel):
    origin: str
    year: int
    safest_route: str
    riskiest_route: str
    routes: List[RouteRiskItem]
