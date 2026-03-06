# app/services/graph_analytics_service.py
from __future__ import annotations

from datetime import date
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import (
    CancellationReasonItem,
    CancellationReasonsResponse,
    ContagionResponse,
    DelayCauseBreakdownResponse,
    DelayCauseItem,
    NetworkNeighborItem,
    NetworkNeighborsResponse,
    RippleHop,
    RippleResponse,
)
from app.services.graph_service import (
    _score_label,
    compute_contagion_scores,
    compute_ripple_chain,
    get_cached_graph,
)


class GraphAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Contagion score
    # ------------------------------------------------------------------

    def get_contagion_score(self, airport: str) -> ContagionResponse:
        G = get_cached_graph(self.db)

        if airport not in G:
            raise ValueError(f"{airport} not found in flight network")

        scores = compute_contagion_scores(G)
        s = scores[airport]

        return ContagionResponse(
            airport_code=airport,
            composite_score=s["composite_score"],
            betweenness_score=s["betweenness_score"],
            degree_score=s["degree_score"],
            closeness_score=s["closeness_score"],
            interpretation=_score_label(s["composite_score"]),
        )

    # ------------------------------------------------------------------
    # Contagion leaderboard  (top / bottom N airports by composite score)
    # ------------------------------------------------------------------

    def get_contagion_leaderboard(
        self, limit: int = 10
    ) -> Dict[str, Any]:
        G = get_cached_graph(self.db)
        scores = compute_contagion_scores(G)

        ranked = sorted(
            [{"airport_code": k, **v} for k, v in scores.items()],
            key=lambda x: x["composite_score"],
            reverse=True,
        )

        return {
            "most_influential": ranked[:limit],
            "least_influential": ranked[-limit:][::-1],
            "total_airports": len(ranked),
        }

    # ------------------------------------------------------------------
    # Network neighbours  (airports reachable within N hops)
    # ------------------------------------------------------------------

    def get_network_neighbors(
        self, airport: str, depth: int = 1
    ) -> NetworkNeighborsResponse:
        G = get_cached_graph(self.db)

        if airport not in G:
            raise ValueError(f"{airport} not found in flight network")

        reachable = nx_single_source(G, airport, depth)
        reachable.pop(airport, None)

        neighbors = [
            NetworkNeighborItem(airport=node, hops=hops)
            for node, hops in sorted(reachable.items(), key=lambda x: x[1])
        ]

        return NetworkNeighborsResponse(
            airport=airport,
            depth=depth,
            total_reachable=len(neighbors),
            neighbors=neighbors,
        )

    # ------------------------------------------------------------------
    # Ripple effect
    # ------------------------------------------------------------------

    def get_ripple_effect(
        self, reporting_airline: str, flight_num: int, flight_date: date, initial_delay: float
    ) -> RippleResponse:
        """
        Look up all legs flown by the same aircraft on `flight_date`
        (identified by carrier + flight_num as a proxy when tail is absent),
        then propagate the initial delay forward through the day.
        """
        rows = self.db.execute(
            text("""
                SELECT
                    flight_num_reporting_airline  AS flight_num,
                    origin,
                    dest,
                    crs_dep_time,
                    crs_arr_time,
                    reporting_airline
                FROM flights
                WHERE reporting_airline = :carrier
                  AND flight_num_reporting_airline = :flight_num
                  AND flight_date = :fdate
                ORDER BY crs_dep_time ASC
            """),
            {
                "carrier":    reporting_airline.upper(),
                "flight_num": flight_num,
                "fdate":      str(flight_date),
            },
        ).fetchall()

        if not rows:
            raise ValueError(
                f"No flights found for {reporting_airline.upper()} "
                f"flight {flight_num} on {flight_date}"
            )

        from datetime import datetime

        def _parse_dt(val):
            """SQLite returns datetimes as strings — normalise to datetime."""
            if isinstance(val, datetime):
                return val
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
                try:
                    return datetime.strptime(val, fmt)
                except (ValueError, TypeError):
                    continue
            raise ValueError(f"Cannot parse datetime: {val!r}")

        schedule = [
            {
                "flight_num":   str(r.flight_num),
                "origin":       r.origin,
                "dest":         r.dest,
                "crs_dep_time": _parse_dt(r.crs_dep_time),
                "crs_arr_time": _parse_dt(r.crs_arr_time),
            }
            for r in rows
        ]

        chain_dicts = compute_ripple_chain(schedule, initial_delay)

        hops = [RippleHop(**h) for h in chain_dicts]
        affected = sum(1 for h in hops if h.estimated_delay_mins > 0)
        final_carried = hops[-1].estimated_delay_mins if hops else 0.0

        return RippleResponse(
            reporting_airline=reporting_airline.upper(),
            flight_num=flight_num,
            flight_date=str(flight_date),
            initial_delay_mins=initial_delay,
            chain=hops,
            total_flights_affected=affected,
            final_carried_delay=final_carried,
        )


# ---------------------------------------------------------------------------
# Delay cause breakdown
# ---------------------------------------------------------------------------

    def get_delay_cause_breakdown(
        self, airport: str, year: int = 2024
    ) -> DelayCauseBreakdownResponse:
        CAUSE_COLS = {
            "Carrier":      "carrier_delay",
            "Weather":      "weather_delay",
            "NAS":          "nas_delay",
            "Security":     "security_delay",
            "Late Aircraft":"late_aircraft_delay",
        }

        # One query: sum each cause column + count flights where each is > 0
        row = self.db.execute(text("""
            SELECT
                COUNT(*)                                        AS total_delayed,
                SUM(COALESCE(carrier_delay,      0))            AS carrier_mins,
                SUM(COALESCE(weather_delay,      0))            AS weather_mins,
                SUM(COALESCE(nas_delay,          0))            AS nas_mins,
                SUM(COALESCE(security_delay,     0))            AS security_mins,
                SUM(COALESCE(late_aircraft_delay,0))            AS late_aircraft_mins,
                SUM(CASE WHEN carrier_delay       > 0 THEN 1 ELSE 0 END) AS carrier_flights,
                SUM(CASE WHEN weather_delay       > 0 THEN 1 ELSE 0 END) AS weather_flights,
                SUM(CASE WHEN nas_delay           > 0 THEN 1 ELSE 0 END) AS nas_flights,
                SUM(CASE WHEN security_delay      > 0 THEN 1 ELSE 0 END) AS security_flights,
                SUM(CASE WHEN late_aircraft_delay > 0 THEN 1 ELSE 0 END) AS late_aircraft_flights
            FROM flights
            WHERE origin = :airport
              AND arr_del_15 = 1
              AND strftime('%Y', flight_date) = :year
        """), {"airport": airport, "year": str(year)}).fetchone()

        if not row or not row.total_delayed:
            raise ValueError(f"No delay data for {airport} in {year}")

        raw = {
            "Carrier":       (int(row.carrier_mins or 0),      int(row.carrier_flights or 0)),
            "Weather":       (int(row.weather_mins or 0),      int(row.weather_flights or 0)),
            "NAS":           (int(row.nas_mins or 0),          int(row.nas_flights or 0)),
            "Security":      (int(row.security_mins or 0),     int(row.security_flights or 0)),
            "Late Aircraft": (int(row.late_aircraft_mins or 0),int(row.late_aircraft_flights or 0)),
        }

        total_mins = sum(v[0] for v in raw.values()) or 1  # avoid div/0

        causes = sorted(
            [
                DelayCauseItem(
                    cause=name,
                    total_minutes=mins,
                    pct_of_total=round(mins / total_mins * 100, 1),
                    flights_affected=flights,
                )
                for name, (mins, flights) in raw.items()
            ],
            key=lambda x: x.total_minutes,
            reverse=True,
        )

        return DelayCauseBreakdownResponse(
            airport=airport,
            year=year,
            total_delayed_flights=int(row.total_delayed),
            total_delay_minutes=total_mins,
            causes=causes,
        )

    # ------------------------------------------------------------------
    # Cancellation reasons
    # ------------------------------------------------------------------

    CANCEL_LABELS = {
        "A": "Carrier",
        "B": "Weather",
        "C": "National Air System",
        "D": "Security",
    }

    def get_cancellation_reasons(
        self, airport: str, year: int = 2024
    ) -> CancellationReasonsResponse:
        rows = self.db.execute(text("""
            SELECT
                UPPER(COALESCE(cancellation_code, '?')) AS code,
                COUNT(*) AS cnt
            FROM flights
            WHERE origin  = :airport
              AND cancelled = 1
              AND strftime('%Y', flight_date) = :year
            GROUP BY code
            ORDER BY cnt DESC
        """), {"airport": airport, "year": str(year)}).fetchall()

        if not rows:
            raise ValueError(f"No cancellation data for {airport} in {year}")

        total = sum(r.cnt for r in rows) or 1

        reasons = [
            CancellationReasonItem(
                code=r.code,
                label=self.CANCEL_LABELS.get(r.code, "Unknown"),
                count=int(r.cnt),
                pct_of_cancelled=round(r.cnt / total * 100, 1),
            )
            for r in rows
        ]

        return CancellationReasonsResponse(
            airport=airport,
            year=year,
            total_cancellations=total,
            reasons=reasons,
        )


# ---------------------------------------------------------------------------

def nx_single_source(G, source, cutoff):
    import networkx as nx
    return nx.single_source_shortest_path_length(G, source, cutoff=cutoff)