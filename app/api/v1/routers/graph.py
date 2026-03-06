# app/api/v1/routers/graph.py
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.schemas import (
    CancellationReasonsResponse,
    ContagionResponse,
    DelayCauseBreakdownResponse,
    FlightLookupItem,
    NetworkNeighborsResponse,
    RippleResponse,
)
from app.services.graph_analytics_service import GraphAnalyticsService

router = APIRouter(prefix="/graph", tags=["graph"])


# 0a. LIST CARRIERS
@router.get("/flights/carriers", response_model=List[str])
def list_carriers(db: Session = Depends(get_db)):
    """All carrier codes present in the dataset, sorted."""
    rows = db.execute(text("""
        SELECT DISTINCT reporting_airline
        FROM flights
        ORDER BY reporting_airline
    """)).fetchall()
    return [r[0] for r in rows]


# 0b. LIST FLIGHT NUMBERS FOR A CARRIER
@router.get("/flights/numbers", response_model=List[int])
def list_flight_numbers(
    carrier: str = Query(..., min_length=2, max_length=3),
    db: Session = Depends(get_db),
):
    """All flight numbers operated by a carrier, sorted."""
    rows = db.execute(text("""
        SELECT DISTINCT flight_num_reporting_airline
        FROM flights
        WHERE reporting_airline = :carrier
        ORDER BY flight_num_reporting_airline
    """), {"carrier": carrier.upper()}).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No flights found for carrier {carrier.upper()}")
    return [r[0] for r in rows]


# 0c. LIST DATES A SPECIFIC FLIGHT OPERATED
@router.get("/flights/dates", response_model=List[str])
def list_flight_dates(
    carrier: str = Query(..., min_length=2, max_length=3),
    flight_num: int = Query(...),
    db: Session = Depends(get_db),
):
    """All dates a specific carrier+flight_num combination operated."""
    rows = db.execute(text("""
        SELECT DISTINCT flight_date
        FROM flights
        WHERE reporting_airline = :carrier
          AND flight_num_reporting_airline = :flight_num
        ORDER BY flight_date
    """), {"carrier": carrier.upper(), "flight_num": flight_num}).fetchall()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No dates found for {carrier.upper()} flight {flight_num}"
        )
    return [str(r[0]) for r in rows]


# 0d. SEARCH FLIGHTS (free-text, for autocomplete)
@router.get("/flights/search", response_model=List[FlightLookupItem])
def search_flights(
    carrier: str = Query(..., min_length=2, max_length=3),
    flight_num: int = Query(...),
    db: Session = Depends(get_db),
):
    """
    Returns all origin→dest legs for a carrier+flight_num across all dates,
    giving enough context to pick a meaningful date to simulate.
    """
    rows = db.execute(text("""
        SELECT
            reporting_airline,
            flight_num_reporting_airline AS flight_num,
            flight_date,
            origin,
            dest,
            crs_dep_time,
            COUNT(*) OVER (
                PARTITION BY reporting_airline, flight_num_reporting_airline, origin, dest
            ) AS times_operated
        FROM flights
        WHERE reporting_airline = :carrier
          AND flight_num_reporting_airline = :flight_num
        ORDER BY flight_date DESC
        LIMIT 100
    """), {"carrier": carrier.upper(), "flight_num": flight_num}).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No flights found for {carrier.upper()} {flight_num}"
        )
    return [
        FlightLookupItem(
            reporting_airline=r.reporting_airline,
            flight_num=r.flight_num,
            flight_date=str(r.flight_date),
            origin=r.origin,
            dest=r.dest,
            times_operated=r.times_operated,
        )
        for r in rows
    ]


# 1. RIPPLE EFFECT
@router.get("/ripple-effect", response_model=RippleResponse)
def ripple_effect(
    carrier: str = Query(..., min_length=2, max_length=3,
                         description="Reporting airline code e.g. AA, DL, UA"),
    flight_num: int = Query(..., description="Flight number e.g. 1234"),
    flight_date: date = Query(..., description="Date in YYYY-MM-DD format"),
    initial_delay: float = Query(..., ge=1, le=1440,
                                 description="Seed delay in minutes (1–1440)"),
    db: Session = Depends(get_db),
):
    """
    Simulate how an initial departure delay propagates through every subsequent
    leg flown by the same aircraft on a given date.

    The chain terminates early if the delay is fully absorbed by ground-time
    buffers between legs.
    """
    try:
        return GraphAnalyticsService(db).get_ripple_effect(
            carrier, flight_num, flight_date, initial_delay
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 2. CONTAGION SCORE  (single airport)
@router.get("/contagion-score/{airport}", response_model=ContagionResponse)
def contagion_score(
    airport: str,
    db: Session = Depends(get_db),
):
    """
    Returns a composite network-centrality score (0–1) for an airport,
    indicating how likely a disruption there is to spread across the US
    flight network.

    Components:
    - **betweenness** (50 %) — how often this airport sits on shortest paths
    - **degree**      (30 %) — number of direct connections
    - **closeness**   (20 %) — how quickly disruption can reach other airports
    """
    airport = airport.strip().upper()
    try:
        return GraphAnalyticsService(db).get_contagion_score(airport)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 3. CONTAGION LEADERBOARD
@router.get("/contagion-leaderboard")
def contagion_leaderboard(
    limit: int = Query(10, ge=1, le=50,
                       description="Number of airports to return at each end"),
    db: Session = Depends(get_db),
):
    """
    Returns the most and least network-influential airports ranked by
    composite contagion score.
    """
    try:
        return GraphAnalyticsService(db).get_contagion_leaderboard(limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 4. NETWORK NEIGHBOURS
@router.get("/network-neighbors/{airport}", response_model=NetworkNeighborsResponse)
def network_neighbors(
    airport: str,
    depth: int = Query(
        default=1, ge=1, le=3,
        description="How many hops out to explore (max 3 to keep response size sane)"
    ),
    db: Session = Depends(get_db),
):
    """
    Returns all airports reachable from `airport` within `depth` connecting
    flights.  Useful for visualising how far a disruption could spread and
    for powering a network graph on the dashboard.
    """
    airport = airport.strip().upper()
    try:
        return GraphAnalyticsService(db).get_network_neighbors(airport, depth)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 5. DELAY CAUSE BREAKDOWN
@router.get("/delay-causes/{airport}", response_model=DelayCauseBreakdownResponse)
def delay_cause_breakdown(
    airport: str,
    year: int = Query(2024, ge=2023, le=2024),
    db: Session = Depends(get_db),
):
    """
    Breaks down total delay minutes at an airport by cause:
    Carrier, Weather, NAS, Security, Late Aircraft.
    Only counts flights where arr_del_15 = 1 (delayed >15 min).
    Results are sorted by most impactful cause first.
    """
    airport = airport.strip().upper()
    try:
        return GraphAnalyticsService(db).get_delay_cause_breakdown(airport, year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 6. CANCELLATION REASONS
@router.get("/cancellation-reasons/{airport}", response_model=CancellationReasonsResponse)
def cancellation_reasons(
    airport: str,
    year: int = Query(2024, ge=2023, le=2024),
    db: Session = Depends(get_db),
):
    """
    Decodes BTS cancellation codes into human-readable reasons:
    A = Carrier, B = Weather, C = National Air System, D = Security.
    """
    airport = airport.strip().upper()
    try:
        return GraphAnalyticsService(db).get_cancellation_reasons(airport, year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))