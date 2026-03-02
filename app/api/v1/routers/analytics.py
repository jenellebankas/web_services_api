from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.schemas import *
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


# 1. AIRPORT DELAYS
@router.get("/airport-delays/{airport}", response_model=AirportDelaysResponse)
def get_airport_delays(
        airport: str,
        db: Session = Depends(get_db)
):
    airport = airport.strip().upper()
    try:
        return AnalyticsService(db).get_airport_delays(airport)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 2. DISRUPTION SCORE
@router.get("/disruption-score/{airport}", response_model=DisruptionScoreResponse)
def get_disruption_score(
        airport: str,
        year: int,
        db: Session = Depends(get_db)
):
    airport = airport.strip().upper()
    try:
        return AnalyticsService(db).get_disruption_score(airport, year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 3. YEAR OVER YEAR
@router.get("/year-over-year/{airport}", response_model=YearOverYearResponse)
def get_year_over_year(
        airport: str,
        db: Session = Depends(get_db)
):
    airport = airport.strip().upper()
    try:
        return AnalyticsService(db).get_year_over_year(airport)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 4. COMPARE AIRPORTS
@router.get("/compare-airports", response_model=AirportComparisonResponse)
def compare_airports(
        airports: str = Query(..., min_length=1),
        year: int = Query(2024, ge=2023, le=2024),
        db: Session = Depends(get_db)
):
    if not airports or ',' not in airports and len(airports.strip()) < 3:
        raise HTTPException(status_code=400, detail="Provide airports as comma-separated list (min 1)")
    try:
        return AnalyticsService(db).compare_airports(airports.strip(), year)
    except ValueError as e:
        raise HTTPException(status_code=400 if "invalid" in str(e).lower() else 404, detail=str(e))


# 5. DAILY PATTERN
@router.get("/daily-pattern", response_model=DailyPatternResponse)
def daily_pattern(
        airport: str = Query(..., min_length=3, max_length=3),
        year: int = Query(2024, ge=2023, le=2024),
        db: Session = Depends(get_db)
):
    airport = airport.strip().upper()
    try:
        return AnalyticsService(db).daily_pattern(airport, year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 6. WEEKLY PATTERN
@router.get("/weekly-pattern", response_model=WeeklyPatternResponse)
def weekly_pattern(
        airport: str = Query(..., min_length=3, max_length=3),
        year: int = Query(2024, ge=2023, le=2024),
        db: Session = Depends(get_db)
):
    airport = airport.strip().upper()
    try:
        return AnalyticsService(db).weekly_pattern(airport, year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 7. LEADERBOARD
@router.get("/leaderboard/punctuality", response_model=PunctualityLeaderboardResponse)
def punctuality_leaderboard(
        year: int = Query(2024, ge=2023, le=2024),
        limit: int = Query(10, ge=1, le=50),
        min_flights: int = Query(100, ge=10, le=10000),
        db: Session = Depends(get_db)
):
    try:
        return AnalyticsService(db).punctuality_leaderboard(year, limit, min_flights)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 8. BEST TIME
@router.get("/best-time/{airport}", response_model=BestTimeResponse)
def best_time_to_fly(
        airport: str,
        year: int,
        top_n: Optional[int],
        db: Session = Depends(get_db)
):
    airport = airport.strip().upper()
    try:
        return AnalyticsService(db).best_time_to_fly(airport, year, top_n)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 9. ROUTE RISK
@router.get("/route-risk", response_model=RouteRiskResponse)
def route_risk_score(
        origin: str = Query(..., min_length=3, max_length=3),
        destinations: str = Query(..., min_length=1),
        year: int = Query(2024, ge=2023, le=2024),
        db: Session = Depends(get_db)
):
    origin = origin.strip().upper()
    if len(destinations.strip().split(',')) == 0:
        raise HTTPException(status_code=400, detail="Provide at least 1 destination (comma-separated)")
    try:
        return AnalyticsService(db).route_risk_score(origin, destinations.strip(), year)
    except ValueError as e:
        raise HTTPException(status_code=400 if "cannot" in str(e).lower() or "maximum" in str(e).lower() else 404,
                            detail=str(e))


# 10. SYSTEM OVERVIEW
@router.get("/system-overview")
def system_overview(db: Session = Depends(get_db)):
    try:
        return AnalyticsService(db).system_overview()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"System error:{str(e)}")


# 11. CARRIER PERFORMANCE
@router.get("/carrier-performance")
def carrier_performance(
        year: int = Query(2024, ge=2023, le=2024),
        db: Session = Depends(get_db)
):
    try:
        return AnalyticsService(db).carrier_performance(year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 12. MONTHLY TRENDS
@router.get("/monthly-trends")
def monthly_trends(
        year: int = Query(2024, ge=2023, le=2024),
        db: Session = Depends(get_db)
):
    try:
        return AnalyticsService(db).monthly_trends(year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
