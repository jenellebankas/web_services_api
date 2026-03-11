# tests/test_services/test_services_graph.py
import pytest

from app.services.graph_analytics_service import GraphAnalyticsService
from app.services.graph_service import (
    compute_contagion_scores,
    compute_ripple_chain,
)


class TestRippleChainLogic:
    """Unit tests for compute_ripple_chain — no DB, just Python."""

    def _make_schedule(self, dep_times, arr_times, origin_dest):
        """Helper: build a minimal schedule list."""
        from datetime import datetime
        legs = []
        for i, ((dep, arr), (orig, dest)) in enumerate(zip(zip(dep_times, arr_times), origin_dest)):
            legs.append({
                "flight_num": str(100 + i),
                "origin": orig,
                "dest": dest,
                "crs_dep_time": datetime.fromisoformat(dep),
                "crs_arr_time": datetime.fromisoformat(arr),
            })
        return legs

    def test_single_leg_carries_full_delay(self):
        schedule = self._make_schedule(
            ["2024-01-15 08:00", "2024-01-15 18:00"],
            ["2024-01-15 16:00", "2024-01-15 20:00"],
            [("LAX", "JFK"), ("JFK", "ORD")],
        )
        chain = compute_ripple_chain(schedule, initial_delay=60)
        assert chain[0]["source"] == "origin"
        assert chain[0]["estimated_delay_mins"] == 60

    def test_delay_absorbed_when_buffer_sufficient(self):
        # 4-hour ground time → 60 min delay easily absorbed
        schedule = self._make_schedule(
            ["2024-01-15 06:00", "2024-01-15 14:00"],
            ["2024-01-15 08:00", "2024-01-15 16:00"],
            [("LAX", "JFK"), ("JFK", "ORD")],
        )
        chain = compute_ripple_chain(schedule, initial_delay=60)
        assert chain[1]["estimated_delay_mins"] == 0
        assert chain[1]["source"] == "recovered"

    def test_delay_partially_absorbed(self):
        # Ground time = 45 min, MIN_TURNAROUND = 30 → buffer = 15 min
        # leg 1: dep 06:00, arr 08:00
        # leg 2: dep 08:45, arr 10:00  → ground = 45 min, buffer = 15 min
        schedule = self._make_schedule(
            ["2024-01-15 06:00", "2024-01-15 08:45"],
            ["2024-01-15 08:00", "2024-01-15 10:00"],
            [("LAX", "JFK"), ("JFK", "ORD")],
        )
        chain = compute_ripple_chain(schedule, initial_delay=60)
        assert chain[1]["delay_absorbed_mins"] == 15
        assert chain[1]["estimated_delay_mins"] == 45

    def test_chain_terminates_after_recovery(self):
        # Three legs; delay absorbed on leg 2 — leg 3 should not appear
        from datetime import datetime
        schedule = [
            {"flight_num": "1", "origin": "LAX", "dest": "JFK",
             "crs_dep_time": datetime(2024, 1, 15, 6, 0), "crs_arr_time": datetime(2024, 1, 15, 14, 0)},
            {"flight_num": "2", "origin": "JFK", "dest": "ORD",
             "crs_dep_time": datetime(2024, 1, 15, 18, 0), "crs_arr_time": datetime(2024, 1, 15, 20, 0)},
            {"flight_num": "3", "origin": "ORD", "dest": "DEN",
             "crs_dep_time": datetime(2024, 1, 15, 22, 0), "crs_arr_time": datetime(2024, 1, 16, 0, 0)},
        ]
        chain = compute_ripple_chain(schedule, initial_delay=30)
        # Delay absorbed between leg 1→2 (4hr buffer), chain ends
        assert chain[-1]["source"] == "recovered"
        assert len(chain) == 2  # terminates after recovery

    def test_zero_delay_raises_no_error(self):
        schedule = self._make_schedule(
            ["2024-01-15 08:00", "2024-01-15 18:00"],
            ["2024-01-15 16:00", "2024-01-15 20:00"],
            [("LAX", "JFK"), ("JFK", "ORD")],
        )
        chain = compute_ripple_chain(schedule, initial_delay=0)
        assert isinstance(chain, list)


class TestContagionScoreLogic:
    """Unit tests for compute_contagion_scores using a tiny hand-crafted graph."""

    def _make_graph(self):
        import networkx as nx
        G = nx.DiGraph()
        # Hub: ORD connects to many spokes
        for spoke in ["LAX", "JFK", "MIA", "DEN", "SEA"]:
            G.add_edge("ORD", spoke, frequency=100, avg_arr_delay=10,
                       avg_dep_delay=8, delay_std=5, late_aircraft_rate=0.1)
            G.add_edge(spoke, "ORD", frequency=100, avg_arr_delay=10,
                       avg_dep_delay=8, delay_std=5, late_aircraft_rate=0.1)
        # Spoke-to-spoke (less frequent)
        G.add_edge("LAX", "JFK", frequency=50, avg_arr_delay=15,
                   avg_dep_delay=12, delay_std=8, late_aircraft_rate=0.2)
        return G

    def test_hub_scores_higher_than_spoke(self):
        G = self._make_graph()
        scores = compute_contagion_scores(G)
        assert scores["ORD"]["composite_score"] > scores["LAX"]["composite_score"]

    def test_all_scores_between_zero_and_one(self):
        G = self._make_graph()
        scores = compute_contagion_scores(G)
        for airport, s in scores.items():
            assert 0.0 <= s["composite_score"] <= 1.0, f"{airport} score out of range"

    def test_scores_contain_all_components(self):
        G = self._make_graph()
        scores = compute_contagion_scores(G)
        for airport in G.nodes():
            assert "betweenness_score" in scores[airport]
            assert "degree_score" in scores[airport]
            assert "closeness_score" in scores[airport]
            assert "composite_score" in scores[airport]


# ════════════════════════════════════════════════════════════════════════════
# GraphAnalyticsService (DB-backed)
# ════════════════════════════════════════════════════════════════════════════

class TestGraphAnalyticsService:

    # ── contagion ────────────────────────────────────────────────────────────

    def test_contagion_score_known_airport(self, db_session):
        svc = GraphAnalyticsService(db_session)
        result = svc.get_contagion_score("LAX")
        assert result.airport_code == "LAX"
        assert 0.0 <= result.composite_score <= 1.0
        assert isinstance(result.interpretation, str)
        assert len(result.interpretation) > 0

    def test_contagion_score_unknown_airport_raises(self, db_session):
        svc = GraphAnalyticsService(db_session)
        with pytest.raises(ValueError, match="not found"):
            svc.get_contagion_score("ZZZ")

    def test_contagion_leaderboard_structure(self, db_session):
        svc = GraphAnalyticsService(db_session)
        result = svc.get_contagion_leaderboard(limit=3)
        assert "most_influential" in result
        assert "least_influential" in result
        assert "total_airports" in result
        assert isinstance(result["most_influential"], list)

    def test_contagion_leaderboard_limit_respected(self, db_session):
        svc = GraphAnalyticsService(db_session)
        result = svc.get_contagion_leaderboard(limit=2)
        assert len(result["most_influential"]) <= 2
        assert len(result["least_influential"]) <= 2

    # ── network neighbours ───────────────────────────────────────────────────

    def test_network_neighbors_depth_1(self, db_session):
        svc = GraphAnalyticsService(db_session)
        result = svc.get_network_neighbors("LAX", depth=1)
        assert result.airport == "LAX"
        assert result.depth == 1
        assert result.total_reachable >= 1
        codes = [n.airport for n in result.neighbors]
        assert "JFK" in codes  # LAX→JFK in seed data

    def test_network_neighbors_depth_2_reaches_further(self, db_session):
        svc = GraphAnalyticsService(db_session)
        d1 = svc.get_network_neighbors("LAX", depth=1)
        d2 = svc.get_network_neighbors("LAX", depth=2)
        assert d2.total_reachable >= d1.total_reachable

    def test_network_neighbors_unknown_airport_raises(self, db_session):
        svc = GraphAnalyticsService(db_session)
        with pytest.raises(ValueError, match="not found"):
            svc.get_network_neighbors("ZZZ", depth=1)

    # ── ripple effect ────────────────────────────────────────────────────────

    def test_ripple_effect_returns_chain(self, db_session):
        from datetime import date
        svc = GraphAnalyticsService(db_session)
        result = svc.get_ripple_effect("AA", 100, date(2024, 1, 15), 60.0)
        assert result.reporting_airline == "AA"
        assert result.flight_num == 100
        assert len(result.chain) >= 1
        assert result.initial_delay_mins == 60.0

    def test_ripple_effect_first_hop_is_origin(self, db_session):
        from datetime import date
        svc = GraphAnalyticsService(db_session)
        result = svc.get_ripple_effect("AA", 100, date(2024, 1, 15), 60.0)
        assert result.chain[0].source == "origin"

    def test_ripple_effect_affected_count_correct(self, db_session):
        from datetime import date
        svc = GraphAnalyticsService(db_session)
        result = svc.get_ripple_effect("AA", 100, date(2024, 1, 15), 60.0)
        affected = sum(1 for h in result.chain if h.estimated_delay_mins > 0)
        assert result.total_flights_affected == affected

    def test_ripple_effect_unknown_flight_raises(self, db_session):
        from datetime import date
        svc = GraphAnalyticsService(db_session)
        with pytest.raises(ValueError):
            svc.get_ripple_effect("ZZ", 9999, date(2024, 1, 15), 30.0)

    # ── delay cause breakdown ────────────────────────────────────────────────

    def test_delay_cause_breakdown_structure(self, db_session):
        svc = GraphAnalyticsService(db_session)
        result = svc.get_delay_cause_breakdown("LAX", year=2024)
        assert result.airport == "LAX"
        assert result.year == 2024
        assert len(result.causes) == 5  # always all 5 causes returned
        cause_names = {c.cause for c in result.causes}
        assert cause_names == {"Carrier", "Weather", "NAS", "Security", "Late Aircraft"}

    def test_delay_cause_breakdown_pct_sums_to_100(self, db_session):
        svc = GraphAnalyticsService(db_session)
        result = svc.get_delay_cause_breakdown("LAX", year=2024)
        total_pct = sum(c.pct_of_total for c in result.causes)
        assert abs(total_pct - 100.0) < 1.0  # allow rounding error

    def test_delay_cause_breakdown_sorted_descending(self, db_session):
        svc = GraphAnalyticsService(db_session)
        result = svc.get_delay_cause_breakdown("LAX", year=2024)
        mins = [c.total_minutes for c in result.causes]
        assert mins == sorted(mins, reverse=True)

    def test_delay_cause_breakdown_no_data_raises(self, db_session):
        svc = GraphAnalyticsService(db_session)
        with pytest.raises(ValueError):
            svc.get_delay_cause_breakdown("ZZZ", year=2024)

    # ── cancellation reasons ─────────────────────────────────────────────────

    def test_cancellation_reasons_structure(self, db_session):
        svc = GraphAnalyticsService(db_session)
        result = svc.get_cancellation_reasons("LAX", year=2024)
        assert result.airport == "LAX"
        assert result.total_cancellations >= 1
        assert len(result.reasons) >= 1

    def test_cancellation_reasons_labels_decoded(self, db_session):
        svc = GraphAnalyticsService(db_session)
        result = svc.get_cancellation_reasons("LAX", year=2024)
        labels = {r.label for r in result.reasons}
        assert "Carrier" in labels
        assert "Weather" in labels

    def test_cancellation_reasons_pct_sums_to_100(self, db_session):
        svc = GraphAnalyticsService(db_session)
        result = svc.get_cancellation_reasons("LAX", year=2024)
        total_pct = sum(r.pct_of_cancelled for r in result.reasons)
        assert abs(total_pct - 100.0) < 1.0

    def test_cancellation_reasons_no_data_raises(self, db_session):
        svc = GraphAnalyticsService(db_session)
        with pytest.raises(ValueError):
            svc.get_cancellation_reasons("ZZZ", year=2024)
