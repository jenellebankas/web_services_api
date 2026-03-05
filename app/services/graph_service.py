# app/services/graph_service.py
from __future__ import annotations
from typing import Dict, List

import networkx as nx
from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_flight_graph(db: Session) -> nx.DiGraph:
    """
    Build a directed graph from aggregated route statistics.
    Each edge (origin → dest) carries:
      - avg_arr_delay     : mean arrival delay in minutes
      - delay_std         : std-dev of arrival delay
      - late_aircraft_rate: fraction of flights delayed due to late aircraft
      - frequency         : number of flights on this route (used as weight)
    """
    rows = db.execute(text("""
        SELECT
            origin,
            dest,
            COUNT(*)                                                  AS frequency,
            COALESCE(AVG(arr_delay_minutes), 0)                       AS avg_arr_delay,
            COALESCE(AVG(dep_delay_minutes), 0)                       AS avg_dep_delay,
            -- SQLite has no STDDEV; approximate with variance trick
            COALESCE(
                SQRT(AVG(arr_delay_minutes * arr_delay_minutes) -
                     AVG(arr_delay_minutes) * AVG(arr_delay_minutes)),
                0
            )                                                         AS delay_std,
            AVG(CASE WHEN late_aircraft_delay > 0 THEN 1.0 ELSE 0.0 END) AS late_aircraft_rate
        FROM flights
        GROUP BY origin, dest
    """)).fetchall()

    G = nx.DiGraph()
    for r in rows:
        G.add_edge(
            r.origin,
            r.dest,
            frequency=int(r.frequency),
            avg_arr_delay=float(r.avg_arr_delay),
            avg_dep_delay=float(r.avg_dep_delay),
            delay_std=float(r.delay_std),
            late_aircraft_rate=float(r.late_aircraft_rate),
        )
    return G


# ---------------------------------------------------------------------------
# In-process cache  (one graph per process; cleared on demand)
# ---------------------------------------------------------------------------

_cached_graph: nx.DiGraph | None = None


def get_cached_graph(db: Session) -> nx.DiGraph:
    global _cached_graph
    if _cached_graph is None:
        _cached_graph = build_flight_graph(db)
    return _cached_graph


def invalidate_graph_cache() -> None:
    global _cached_graph
    _cached_graph = None


# ---------------------------------------------------------------------------
# Centrality / contagion helpers
# ---------------------------------------------------------------------------

def compute_contagion_scores(G: nx.DiGraph) -> Dict[str, Dict[str, float]]:
    """
    Return a dict keyed by airport with normalised centrality components
    and a composite contagion score (0–1).
    """
    betweenness = nx.betweenness_centrality(G, weight="frequency", normalized=True)
    degree = nx.degree_centrality(G)
    closeness = nx.closeness_centrality(G)

    def _normalise(d: dict) -> dict:
        mx = max(d.values(), default=1) or 1
        return {k: v / mx for k, v in d.items()}

    b = _normalise(betweenness)
    d = _normalise(degree)
    c = _normalise(closeness)

    scores: Dict[str, Dict[str, float]] = {}
    for airport in G.nodes():
        composite = (
            0.50 * b.get(airport, 0.0) +
            0.30 * d.get(airport, 0.0) +
            0.20 * c.get(airport, 0.0)
        )
        scores[airport] = {
            "betweenness_score": round(b.get(airport, 0.0), 4),
            "degree_score":      round(d.get(airport, 0.0), 4),
            "closeness_score":   round(c.get(airport, 0.0), 4),
            "composite_score":   round(composite, 4),
        }
    return scores


def _score_label(score: float) -> str:
    if score >= 0.75:
        return "Critical hub — delays here spread widely across the network"
    if score >= 0.50:
        return "Major hub — significant network influence"
    if score >= 0.25:
        return "Regional hub — localised impact"
    return "Spoke airport — minimal network impact"


# ---------------------------------------------------------------------------
# Ripple-effect chain
# ---------------------------------------------------------------------------

MIN_TURNAROUND_MINUTES = 30  # below this ground time, delay cannot be absorbed


def compute_ripple_chain(
    schedule: List[dict],
    initial_delay: float,
) -> List[dict]:
    """
    Walk an aircraft's daily schedule and propagate delay forward.

    Each item in `schedule` must have:
        flight_num, origin, dest, crs_dep_time (datetime), crs_arr_time (datetime)

    Returns a list of hop dicts ready to be turned into RippleHop schema objects.
    """
    chain: List[dict] = []
    carried = initial_delay

    for i, flight in enumerate(schedule):
        if i == 0:
            chain.append({
                "flight_num":           flight["flight_num"],
                "origin":               flight["origin"],
                "dest":                 flight["dest"],
                "crs_dep_time":         flight["crs_dep_time"],
                "estimated_delay_mins": round(carried, 1),
                "delay_absorbed_mins":  0.0,
                "source":               "origin",
            })
            continue

        prev = schedule[i - 1]
        # Ground time in minutes between scheduled arrival of previous leg
        # and scheduled departure of this leg
        ground_minutes = (
            flight["crs_dep_time"] - prev["crs_arr_time"]
        ).total_seconds() / 60

        # Buffer = slack above the minimum viable turnaround
        buffer = max(0.0, ground_minutes - MIN_TURNAROUND_MINUTES)
        absorbed = min(carried, buffer)
        carried = max(0.0, carried - absorbed)

        chain.append({
            "flight_num":           flight["flight_num"],
            "origin":               flight["origin"],
            "dest":                 flight["dest"],
            "crs_dep_time":         flight["crs_dep_time"],
            "estimated_delay_mins": round(carried, 1),
            "delay_absorbed_mins":  round(absorbed, 1),
            "source":               "propagated" if carried > 0 else "recovered",
        })

        if carried == 0:
            break  # delay fully absorbed — chain ends early

    return chain
