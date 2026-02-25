# app/api/v1/routers/analytics.py
from app.schemas import DisruptionScoreResponse
from app.schemas import YearOverYearResponse
from app.schemas import AirportComparisonResponse
from app.schemas import AirportComparisonItem
from app.schemas import AirportDelaysResponse
from app.schemas import HourlyPatternItem
from app.schemas import DailyPatternResponse
from app.schemas import WeeklyPatternItem
from app.schemas import WeeklyPatternResponse
from app.schemas import LeaderboardItem
from app.schemas import PunctualityLeaderboardResponse
from app.schemas import BestTimeItem
from app.schemas import BestTimeResponse
from app.schemas import RouteRiskItem
from app.schemas import RouteRiskResponse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from typing import List
from app.api.v1.deps import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/airport-delays/{airport}", response_model=AirportDelaysResponse)
def get_airport_delays(airport: str, db: Session = Depends(get_db)):

    result = db.execute(
        text("""
            SELECT 
                COUNT(*) as total,
                AVG(COALESCE(arr_delay_minutes, 0)) as avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) as delayed,
                SUM(cancelled) as cancelled
            FROM flights 
            WHERE origin = :airport
        """),
        {"airport": airport}
    ).fetchone()

    total = result.total or 0
    if total == 0:
        raise HTTPException(status_code=404, detail="No data")

    return AirportDelaysResponse(
        airport=airport,
        total_flights=int(total),
        avg_arrival_delay=round(float(result.avg_delay or 0), 1),
        delay_rate=round(float(result.delayed or 0) / total, 3),
        cancel_rate=round(float(result.cancelled or 0) / total, 3),
        worst_day="Monday"
    )


@router.get("/disruption-score/{airport}", response_model=DisruptionScoreResponse)
def get_disruption_score(airport: str, db: Session = Depends(get_db)):
    # Reuse same structure but compute extra fields
    result = db.execute(
        text("""
            SELECT 
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(cancelled) AS cancelled,
                COUNT(*) AS total
            FROM flights
            WHERE origin = :airport
        """),
        {"airport": airport}
    ).fetchone()

    if not result or result.total == 0:
        raise HTTPException(status_code=404, detail="No data")

    total = result.total
    avg_delay = float(result.avg_delay or 0)
    delay_freq = float(result.delayed or 0) / total
    cancel_freq = float(result.cancelled or 0) / total

    # Simple disruption formula (explain this in your report)
    disruption_score = max(
        0.0,
        100.0 - (avg_delay * 1.5 + delay_freq * 50.0 + cancel_freq * 80.0)
    )

    # For now, keep top_delay_cause simple; you can improve later
    top_delay_cause = "Carrier"

    return DisruptionScoreResponse(
        airport=airport,
        disruption_score=round(disruption_score, 1),
        delay_frequency=round(delay_freq, 3),
        cancel_frequency=round(cancel_freq, 3),
        top_delay_cause=top_delay_cause,
    )


@router.get("/year-over-year/{airport}", response_model=YearOverYearResponse)
def get_year_over_year(airport: str, db: Session = Depends(get_db)):
    # 2023 stats
    res_2023 = db.execute(
        text("""
            SELECT 
                COUNT(*) AS total,
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(cancelled) AS cancelled
            FROM flights
            WHERE origin = :airport
              AND strftime('%Y', flight_date) = '2023'
        """),
        {"airport": airport}
    ).fetchone()

    # 2024 stats
    res_2024 = db.execute(
        text("""
            SELECT 
                COUNT(*) AS total,
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(cancelled) AS cancelled
            FROM flights
            WHERE origin = :airport
              AND strftime('%Y', flight_date) = '2024'
        """),
        {"airport": airport}
    ).fetchone()

    if (not res_2023 or res_2023.total == 0) and (not res_2024 or res_2024.total == 0):
        raise HTTPException(status_code=404, detail="No year-over-year data")

    def build_year_dict(row):
        if not row or row.total == 0:
            return {
                "total_flights": 0,
                "avg_arrival_delay": 0.0,
                "delay_rate": 0.0,
                "cancel_rate": 0.0,
            }
        total = row.total
        avg_delay = float(row.avg_delay or 0)
        delay_rate = float(row.delayed or 0) / total
        cancel_rate = float(row.cancelled or 0) / total
        return {
            "total_flights": int(total),
            "avg_arrival_delay": round(avg_delay, 1),
            "delay_rate": round(delay_rate, 3),
            "cancel_rate": round(cancel_rate, 3),
        }

    year_2023 = build_year_dict(res_2023)
    year_2024 = build_year_dict(res_2024)

    # Improvement defined as reduction in delay_rate (%)
    if year_2023["delay_rate"] > 0:
        improvement_pct = (
            (year_2023["delay_rate"] - year_2024["delay_rate"])
            / year_2023["delay_rate"]
            * 100.0
        )
    else:
        improvement_pct = 0.0

    return YearOverYearResponse(
        airport=airport,
        year_2023=year_2023,
        year_2024=year_2024,
        improvement_pct=round(improvement_pct, 1),
    )


@router.get("/compare-airports", response_model=AirportComparisonResponse)
def compare_airports(
    airports: str,
    year: int = 2024,
    db: Session = Depends(get_db),
):
    airport_list = [a.strip().upper() for a in airports.split(",") if a.strip()]

    if not airport_list:
        raise HTTPException(status_code=400, detail="No airports provided")

    placeholders = ",".join([f":a{i}" for i in range(len(airport_list))])
    params = {f"a{i}": code for i, code in enumerate(airport_list)}
    params["year"] = str(year)

    result = db.execute(
        text(f"""
            SELECT 
                origin AS airport,
                COUNT(*) AS total,
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(cancelled) AS cancelled
            FROM flights
            WHERE origin IN ({placeholders})
              AND strftime('%Y', flight_date) = :year
            GROUP BY origin
        """),
        params
    ).fetchall()

    items: List[AirportComparisonItem] = []
    for row in result:
        total = row.total or 0
        if total == 0:
            continue
        delay_rate = float(row.delayed or 0) / total
        cancel_rate = float(row.cancelled or 0) / total
        items.append(
            AirportComparisonItem(
                airport=row.airport,
                total_flights=int(total),
                avg_arrival_delay=round(float(row.avg_delay or 0), 1),
                delay_rate=round(delay_rate, 3),
                cancel_rate=round(cancel_rate, 3),
            )
        )

    if not items:
        raise HTTPException(status_code=404, detail="No data for given airports/year")

    return AirportComparisonResponse(year=year, airports=items)


@router.get("/daily-pattern/{airport}", response_model=DailyPatternResponse)
def daily_pattern(
    airport: str,
    year: int = 2024,
    db: Session = Depends(get_db),
):
    result = db.execute(
        text("""
            SELECT 
                CAST(strftime('%H', dep_time) AS INTEGER) AS hour,
                COUNT(*) AS total,
                COALESCE(AVG(dep_delay_minutes), 0) AS avg_dep_delay,
                SUM(CASE WHEN dep_del_15 = 1 THEN 1 ELSE 0 END) AS delayed
            FROM flights
            WHERE origin = :airport
              AND dep_time IS NOT NULL
              AND strftime('%Y', flight_date) = :year
            GROUP BY hour
            ORDER BY hour
        """),
        {"airport": airport, "year": str(year)}
    ).fetchall()

    hours: List[HourlyPatternItem] = []
    for row in result:
        total = row.total or 0
        if total == 0 or row.hour is None:
            continue
        delay_rate = float(row.delayed or 0) / total
        hours.append(
            HourlyPatternItem(
                hour=int(row.hour),
                avg_dep_delay=round(float(row.avg_dep_delay or 0), 1),
                delay_rate=round(delay_rate, 3),
            )
        )

    if not hours:
        raise HTTPException(status_code=404, detail="No pattern data for this airport/year")

    return DailyPatternResponse(airport=airport.upper(), year=year, hours=hours)


DOW_MAP = {
    0: "Sun",
    1: "Mon",
    2: "Tue",
    3: "Wed",
    4: "Thu",
    5: "Fri",
    6: "Sat",
}


@router.get("/weekly-pattern/{airport}", response_model=WeeklyPatternResponse)
def weekly_pattern(
    airport: str,
    year: int = 2024,
    db: Session = Depends(get_db),
):
    result = db.execute(
        text("""
            SELECT 
                CAST(strftime('%w', flight_date) AS INTEGER) AS dow,
                COUNT(*) AS total,
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_arr_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(cancelled) AS cancelled
            FROM flights
            WHERE origin = :airport
              AND strftime('%Y', flight_date) = :year
            GROUP BY dow
            ORDER BY dow
        """),
        {"airport": airport, "year": str(year)}
    ).fetchall()

    days: List[WeeklyPatternItem] = []
    for row in result:
        total = row.total or 0
        if total == 0 or row.dow is None:
            continue
        delay_rate = float(row.delayed or 0) / total
        cancel_rate = float(row.cancelled or 0) / total
        label = DOW_MAP.get(int(row.dow), str(row.dow))
        days.append(
            WeeklyPatternItem(
                dow=label,
                avg_arr_delay=round(float(row.avg_arr_delay or 0), 1),
                delay_rate=round(delay_rate, 3),
                cancel_rate=round(cancel_rate, 3),
            )
        )

    if not days:
        raise HTTPException(status_code=404, detail="No weekly data for this airport/year")

    return WeeklyPatternResponse(airport=airport.upper(), year=year, days=days)


@router.get(
    "/leaderboard/punctuality",
    response_model=PunctualityLeaderboardResponse,
)
def punctuality_leaderboard(
    year: int = 2024,
    limit: int = 10,
    min_flights: int = 1000,
    db: Session = Depends(get_db),
):
    # aggregate per origin
    rows = db.execute(
        text("""
            SELECT
                origin AS airport,
                COUNT(*) AS total_flights,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed_flights
            FROM flights
            WHERE strftime('%Y', flight_date) = :year
            GROUP BY origin
        """),
        {"year": str(year)},
    ).mappings().all()

    items: List[LeaderboardItem] = []
    for row in rows:
        total = int(row["total_flights"] or 0)
        if total < min_flights:
            continue  # ignore tiny airports/noise
        delayed = int(row["delayed_flights"] or 0)
        delay_rate = delayed / total
        otp = 1.0 - delay_rate
        items.append(
            LeaderboardItem(
                airport=row["airport"],
                otp_pct=round(otp, 3),
                delay_rate=round(delay_rate, 3),
                total_flights=total,
            )
        )

    if not items:
        raise HTTPException(status_code=404, detail="No airports meet criteria for this year")

    items_sorted = sorted(items, key=lambda x: x.otp_pct, reverse=True)
    top = items_sorted[:limit]
    bottom = list(reversed(items_sorted))[:limit]

    return PunctualityLeaderboardResponse(
        year=year,
        top_airports=top,
        bottom_airports=bottom,
    )


@router.get("/best-time/{airport}", response_model=BestTimeResponse)
def best_time_to_fly(
        airport: str,
        year: int = 2024,
        top_n: int = 3,
        db: Session = Depends(get_db),
):
    # Get hourly patterns (same SQL as daily-pattern but with counts)
    result = db.execute(
        text("""
            SELECT 
                CAST(strftime('%H', dep_time) AS INTEGER) AS hour,
                COUNT(*) AS total_flights,
                COALESCE(AVG(dep_delay_minutes), 0) AS avg_dep_delay,
                SUM(CASE WHEN dep_del_15 = 1 THEN 1 ELSE 0 END)*1.0 / COUNT(*) AS delay_rate
            FROM flights
            WHERE origin = :airport
              AND dep_time IS NOT NULL
              AND strftime('%Y', flight_date) = :year
            GROUP BY hour
            HAVING total_flights >= 50  -- minimum sample size
            ORDER BY hour
        """),
        {"airport": airport, "year": str(year)}
    ).fetchall()

    if not result:
        raise HTTPException(status_code=404, detail="No sufficient data for this airport/year")

    # Convert to list and sort by delay_rate (best = lowest)
    hours: List[BestTimeItem] = []
    for row in result:
        if row.total_flights < 50:  # safety check
            continue
        hours.append(
            BestTimeItem(
                hour=int(row.hour),
                avg_dep_delay=round(float(row.avg_dep_delay), 1),
                delay_rate=round(float(row.delay_rate), 3),
                total_flights=int(row.total_flights),
            )
        )

    if len(hours) < 2:
        raise HTTPException(status_code=404, detail="Insufficient hourly data")

    # Sort by delay_rate (ascending = best)
    sorted_hours = sorted(hours, key=lambda x: x.delay_rate)

    best = sorted_hours[:top_n]
    worst = sorted_hours[-top_n:]

    # Generate insight
    best_rate = best[0].delay_rate if best else 0
    worst_rate = worst[0].delay_rate if worst else 0
    improvement = ((worst_rate - best_rate) / worst_rate * 100) if worst_rate > 0 else 0

    insight = f"Flying at {best[0].hour}:00 gives {best[0].delay_rate:.1%} delay risk vs {worst[0].delay_rate:.1%} at {worst[0].hour}:00 ({improvement:.0f}% better)."

    return BestTimeResponse(
        airport=airport.upper(),
        year=year,
        best_hours=best,
        worst_hours=worst,
        insight=insight,
    )


@router.get("/route-risk", response_model=RouteRiskResponse)
def route_risk_score(
        origin: str,
        destinations: str,  # comma-separated: "JFK,ORD,LAS"
        year: int = 2024,
        db: Session = Depends(get_db),
):
    dest_list = [d.strip().upper() for d in destinations.split(",") if d.strip()]

    if len(dest_list) < 2 or len(dest_list) > 10:
        raise HTTPException(status_code=400, detail="Provide 2-10 destinations (comma-separated)")

    placeholders = ",".join([f":d{i}" for i in range(len(dest_list))])
    params = {f"d{i}": dest for i, dest in enumerate(dest_list)}
    params.update({"origin": origin.upper(), "year": str(year)})

    result = db.execute(
        text(f"""
            SELECT 
                dest AS dest,
                COUNT(*) AS total_flights,
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_arr_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END)*1.0 / COUNT(*) AS delay_rate,
                SUM(cancelled)*1.0 / COUNT(*) AS cancel_rate
            FROM flights
            WHERE origin = :origin 
              AND dest IN ({placeholders})
              AND strftime('%Y', flight_date) = :year
            GROUP BY dest
            HAVING total_flights >= 10
        """),
        params
    ).fetchall()

    if not result:
        raise HTTPException(status_code=404, detail="No route data found")

    routes: List[RouteRiskItem] = []
    for row in result:
        # Risk formula: delay_rate (40%) + avg_delay (30%) + cancel_rate (30%)
        # Normalized to 0-100 scale
        delay_component = float(row.delay_rate or 0) * 40
        delay_minutes_component = min(float(row.avg_arr_delay or 0) / 30, 1) * 30  # cap at 30min
        cancel_component = float(row.cancel_rate or 0) * 3000  # cancellations hurt more
        risk_score = round(delay_component + delay_minutes_component + cancel_component, 1)

        routes.append(
            RouteRiskItem(
                dest=row.dest,
                risk_score=risk_score,
                delay_rate=round(float(row.delay_rate or 0), 3),
                avg_arr_delay=round(float(row.avg_arr_delay or 0), 1),
                cancel_rate=round(float(row.cancel_rate or 0), 3),
                total_flights=int(row.total_flights),
            )
        )

    routes.sort(key=lambda x: x.risk_score)

    return RouteRiskResponse(
        origin=origin.upper(),
        year=year,
        safest_route=f"{origin}→{routes[0].dest}",
        riskiest_route=f"{origin}→{routes[-1].dest}",
        routes=routes,
    )


@router.get("/system-overview")
def system_overview(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT 
            COUNT(*) as total_flights,
            ROUND(AVG(COALESCE(arr_delay_minutes, 0)), 1) as avg_delay,
            ROUND(AVG(CASE WHEN arr_del_15 = 1 THEN 1.0 ELSE 0 END), 3) as delay_rate,
            SUM(cancelled) as total_cancelled
        FROM flights
    """)).fetchone()

    return {
        "total_flights": int(result.total_flights),
        "avg_delay_minutes": float(result.avg_delay),
        "national_delay_rate": float(result.delay_rate),
        "total_cancellations": int(result.total_cancelled)
    }


@router.get("/carrier-performance")
def carrier_performance(year: int = 2024, db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT 
            DISTINCT reporting_airline,
            COUNT(*) as total_flights,
            ROUND((1.0 - AVG(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END)), 3) as otp_pct
        FROM flights 
        WHERE strftime('%Y', flight_date) = :year
        GROUP BY reporting_airline 
        HAVING total_flights >= 5000
        ORDER BY otp_pct DESC
        LIMIT 10
    """), {"year": str(year)}).fetchall()

    return [
        {
            "carrier": r.uniquecarrier,
            "otp_pct": float(r.otp_pct),
            "total_flights": int(r.total_flights),
            "delay_rate": round(1 - float(r.otp_pct), 3)
        }
        for r in result
    ]


@router.get("/monthly-trends")
def monthly_trends(year: int = 2024, db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT 
            strftime('%m-%Y', flight_date) as period,
            strftime('%m', flight_date) as month_num,
            COUNT(*) as flights,
            ROUND(AVG(COALESCE(arr_delay_minutes, 0)), 1) as avg_delay,
            ROUND(AVG(CASE WHEN arr_del_15 = 1 THEN 1.0 ELSE 0 END), 3) as delay_rate,
            ROUND(AVG(cancelled*1.0), 3) as cancel_rate
        FROM flights
        WHERE strftime('%Y', flight_date) = :year
        GROUP BY 1 ORDER BY month_num
    """), {"year": str(year)}).fetchall()

    return [{"period": r.period, "flights": int(r.flights), "avg_delay": float(r.avg_delay),
             "delay_rate": float(r.delay_rate), "cancel_rate": float(r.cancel_rate)} for r in result]
