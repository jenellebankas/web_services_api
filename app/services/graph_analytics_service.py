# app/services/graph_analytics_service.py
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import (
    ContagionResponse,
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

        schedule = [
            {
                "flight_num": str(r.flight_num),
                "origin":     r.origin,
                "dest":       r.dest,
                "crs_dep_time": r.crs_dep_time,
                "crs_arr_time": r.crs_arr_time,
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
# Thin wrapper to avoid importing networkx at the top of the service
# ---------------------------------------------------------------------------

def nx_single_source(G, source, cutoff):
    import networkx as nx
    return nx.single_source_shortest_path_length(G, source, cutoff=cutoff)