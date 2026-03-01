from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db

from app.services.analystics_service import AnalyticsService
from app.schemas import *

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/airport-delays/{airport}", response_model=AirportDelaysResponse)
def get_airport_delays(airport: str, db: Session = Depends(get_db)):
    return AnalyticsService(db).get_airport_delays(airport)


@router.get("/disruption-score/{airport}", response_model=DisruptionScoreResponse)
def get_disruption_score(airport: str, db: Session = Depends(get_db)):
    return AnalyticsService(db).get_disruption_score(airport)


@router.get("/year-over-year/{airport}", response_model=YearOverYearResponse)
def get_year_over_year(airport: str, db: Session = Depends(get_db)):
    return AnalyticsService(db).get_year_over_year(airport)


@router.get("/compare-airports", response_model=AirportComparisonResponse)
def compare_airports(airports: str, year: int = Query(2024), db: Session = Depends(get_db)):
    return AnalyticsService(db).compare_airports(airports, year)


@router.get("/daily-pattern", response_model=DailyPatternResponse)
def daily_pattern(airport: str, year: int = Query(2024), db: Session = Depends(get_db)):
    return AnalyticsService(db).daily_pattern(airport, year)


@router.get("/weekly-pattern", response_model=WeeklyPatternResponse)
def weekly_pattern(airport: str, year: int = Query(2024), db: Session = Depends(get_db)):
    return AnalyticsService(db).weekly_pattern(airport, year)


@router.get("/leaderboard/punctuality", response_model=PunctualityLeaderboardResponse)
def punctuality_leaderboard(year: int = Query(2024), limit: int = Query(10),
                            min_flights: int = Query(1000), db: Session = Depends(get_db)):
    return AnalyticsService(db).punctuality_leaderboard(year, limit, min_flights)


@router.get("/best-time/{airport}", response_model=BestTimeResponse)
def best_time_to_fly(airport: str, year: int = Query(2024), top_n: int = Query(3), db: Session = Depends(get_db)):
    return AnalyticsService(db).best_time_to_fly(airport, year, top_n)


@router.get("/route-risk", response_model=RouteRiskResponse)
def route_risk_score(origin: str, destinations: str, year: int = Query(2024), db: Session = Depends(get_db)):
    return AnalyticsService(db).route_risk_score(origin, destinations, year)


@router.get("/system-overview")
def system_overview(db: Session = Depends(get_db)):
    return AnalyticsService(db).system_overview()


@router.get("/carrier-performance")
def carrier_performance(year: int = Query(2024), db: Session = Depends(get_db)):
    return AnalyticsService(db).carrier_performance(year)


@router.get("/monthly-trends")
def monthly_trends(year: int = Query(2024), db: Session = Depends(get_db)):
    return AnalyticsService(db).monthly_trends(year)


@router.get("/chaos-score/{airport}")
def chaos_score(airport: str, lookback_days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    """CHAOS SCORE: Real-time airport disruption severity (0-100)"""
    try:
        return AnalyticsService(db).chaos_score(airport, lookback_days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

