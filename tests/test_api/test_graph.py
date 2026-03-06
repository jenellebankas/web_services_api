# tests/test_api/test_graph.py


# ════════════════════════════════════════════════════════════════════════════
# Flight lookup endpoints
# ════════════════════════════════════════════════════════════════════════════

class TestFlightLookup:

    def test_list_carriers(self, client):
        response = client.get("/api/v1/graph/flights/carriers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "AA" in data
        assert data == sorted(data)         # should be alphabetically sorted

    def test_list_flight_numbers_known_carrier(self, client):
        response = client.get("/api/v1/graph/flights/numbers?carrier=AA")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert 100 in data

    def test_list_flight_numbers_unknown_carrier(self, client):
        response = client.get("/api/v1/graph/flights/numbers?carrier=ZZ")
        assert response.status_code == 404

    def test_list_flight_dates_known_flight(self, client):
        response = client.get("/api/v1/graph/flights/dates?carrier=AA&flight_num=100")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "2024-01-15" in data

    def test_list_flight_dates_unknown_flight(self, client):
        response = client.get("/api/v1/graph/flights/dates?carrier=AA&flight_num=9999")
        assert response.status_code == 404

    def test_search_flights_returns_legs(self, client):
        response = client.get("/api/v1/graph/flights/search?carrier=AA&flight_num=100")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        first = data[0]
        assert first["reporting_airline"] == "AA"
        assert first["flight_num"] == 100
        assert "origin" in first
        assert "dest"   in first
        assert "times_operated" in first

    def test_search_flights_unknown_returns_404(self, client):
        response = client.get("/api/v1/graph/flights/search?carrier=ZZ&flight_num=1")
        assert response.status_code == 404


# ════════════════════════════════════════════════════════════════════════════
# Ripple effect
# ════════════════════════════════════════════════════════════════════════════

class TestRippleEffect:

    def test_ripple_effect_happy_path(self, client):
        response = client.get(
            "/api/v1/graph/ripple-effect",
            params={"carrier": "AA", "flight_num": 100,
                    "flight_date": "2024-01-15", "initial_delay": 60}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["reporting_airline"] == "AA"
        assert data["flight_num"] == 100
        assert data["initial_delay_mins"] == 60
        assert isinstance(data["chain"], list)
        assert len(data["chain"]) >= 1

    def test_ripple_effect_chain_structure(self, client):
        response = client.get(
            "/api/v1/graph/ripple-effect",
            params={"carrier": "AA", "flight_num": 100,
                    "flight_date": "2024-01-15", "initial_delay": 30}
        )
        assert response.status_code == 200
        chain = response.json()["chain"]
        for hop in chain:
            assert "flight_num"           in hop
            assert "origin"               in hop
            assert "dest"                 in hop
            assert "estimated_delay_mins" in hop
            assert "delay_absorbed_mins"  in hop
            assert "source"               in hop
            assert hop["source"] in ("origin", "propagated", "recovered")

    def test_ripple_effect_first_hop_is_origin(self, client):
        response = client.get(
            "/api/v1/graph/ripple-effect",
            params={"carrier": "AA", "flight_num": 100,
                    "flight_date": "2024-01-15", "initial_delay": 45}
        )
        assert response.status_code == 200
        assert response.json()["chain"][0]["source"] == "origin"

    def test_ripple_effect_unknown_flight_404(self, client):
        response = client.get(
            "/api/v1/graph/ripple-effect",
            params={"carrier": "ZZ", "flight_num": 9999,
                    "flight_date": "2024-01-15", "initial_delay": 60}
        )
        assert response.status_code == 404

    def test_ripple_effect_delay_below_minimum_422(self, client):
        # initial_delay ge=1 — sending 0 should fail validation
        response = client.get(
            "/api/v1/graph/ripple-effect",
            params={"carrier": "AA", "flight_num": 100,
                    "flight_date": "2024-01-15", "initial_delay": 0}
        )
        assert response.status_code == 422

    def test_ripple_effect_missing_params_422(self, client):
        response = client.get("/api/v1/graph/ripple-effect")
        assert response.status_code == 422


# ════════════════════════════════════════════════════════════════════════════
# Contagion score
# ════════════════════════════════════════════════════════════════════════════

class TestContagionScore:

    def test_contagion_score_known_airport(self, client):
        response = client.get("/api/v1/graph/contagion-score/LAX")
        assert response.status_code == 200
        data = response.json()
        assert data["airport_code"] == "LAX"
        assert 0.0 <= data["composite_score"]   <= 1.0
        assert 0.0 <= data["betweenness_score"] <= 1.0
        assert 0.0 <= data["degree_score"]      <= 1.0
        assert 0.0 <= data["closeness_score"]   <= 1.0
        assert isinstance(data["interpretation"], str)

    def test_contagion_score_lowercase_normalised(self, client):
        # router should upper-case the code
        response = client.get("/api/v1/graph/contagion-score/lax")
        assert response.status_code == 200
        assert response.json()["airport_code"] == "LAX"

    def test_contagion_score_unknown_airport_404(self, client):
        response = client.get("/api/v1/graph/contagion-score/ZZZ")
        assert response.status_code == 404

    def test_contagion_leaderboard_default(self, client):
        response = client.get("/api/v1/graph/contagion-leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "most_influential"  in data
        assert "least_influential" in data
        assert "total_airports"    in data

    def test_contagion_leaderboard_limit_param(self, client):
        response = client.get("/api/v1/graph/contagion-leaderboard?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["most_influential"])  <= 2
        assert len(data["least_influential"]) <= 2

    def test_contagion_leaderboard_limit_above_max_422(self, client):
        response = client.get("/api/v1/graph/contagion-leaderboard?limit=999")
        assert response.status_code == 422


# ════════════════════════════════════════════════════════════════════════════
# Network neighbours
# ════════════════════════════════════════════════════════════════════════════

class TestNetworkNeighbors:

    def test_neighbors_depth_1(self, client):
        response = client.get("/api/v1/graph/network-neighbors/LAX?depth=1")
        assert response.status_code == 200
        data = response.json()
        assert data["airport"] == "LAX"
        assert data["depth"]   == 1
        assert isinstance(data["neighbors"], list)
        assert data["total_reachable"] == len(data["neighbors"])

    def test_neighbors_depth_2_gte_depth_1(self, client):
        d1 = client.get("/api/v1/graph/network-neighbors/LAX?depth=1").json()
        d2 = client.get("/api/v1/graph/network-neighbors/LAX?depth=2").json()
        assert d2["total_reachable"] >= d1["total_reachable"]

    def test_neighbors_depth_above_max_422(self, client):
        response = client.get("/api/v1/graph/network-neighbors/LAX?depth=10")
        assert response.status_code == 422

    def test_neighbors_unknown_airport_404(self, client):
        response = client.get("/api/v1/graph/network-neighbors/ZZZ")
        assert response.status_code == 404

    def test_neighbors_each_item_has_hops(self, client):
        response = client.get("/api/v1/graph/network-neighbors/LAX?depth=2")
        assert response.status_code == 200
        for neighbor in response.json()["neighbors"]:
            assert "airport" in neighbor
            assert "hops"    in neighbor
            assert neighbor["hops"] >= 1


# ════════════════════════════════════════════════════════════════════════════
# Delay cause breakdown
# ════════════════════════════════════════════════════════════════════════════

class TestDelayCauses:

    def test_delay_causes_happy_path(self, client):
        response = client.get("/api/v1/graph/delay-causes/LAX?year=2024")
        assert response.status_code == 200
        data = response.json()
        assert data["airport"] == "LAX"
        assert data["year"]    == 2024
        assert isinstance(data["total_delayed_flights"], int)
        assert isinstance(data["total_delay_minutes"],   int)
        assert len(data["causes"]) == 5

    def test_delay_causes_all_five_present(self, client):
        response = client.get("/api/v1/graph/delay-causes/LAX?year=2024")
        cause_names = {c["cause"] for c in response.json()["causes"]}
        assert cause_names == {"Carrier", "Weather", "NAS", "Security", "Late Aircraft"}

    def test_delay_causes_pct_sums_to_100(self, client):
        response = client.get("/api/v1/graph/delay-causes/LAX?year=2024")
        total = sum(c["pct_of_total"] for c in response.json()["causes"])
        assert abs(total - 100.0) < 1.0

    def test_delay_causes_sorted_descending(self, client):
        response = client.get("/api/v1/graph/delay-causes/LAX?year=2024")
        mins = [c["total_minutes"] for c in response.json()["causes"]]
        assert mins == sorted(mins, reverse=True)

    def test_delay_causes_unknown_airport_404(self, client):
        response = client.get("/api/v1/graph/delay-causes/ZZZ?year=2024")
        assert response.status_code == 404

    def test_delay_causes_invalid_year_422(self, client):
        response = client.get("/api/v1/graph/delay-causes/LAX?year=2020")
        assert response.status_code == 422


# ════════════════════════════════════════════════════════════════════════════
# Cancellation reasons
# ════════════════════════════════════════════════════════════════════════════

class TestCancellationReasons:

    def test_cancellation_reasons_happy_path(self, client):
        response = client.get("/api/v1/graph/cancellation-reasons/LAX?year=2024")
        assert response.status_code == 200
        data = response.json()
        assert data["airport"] == "LAX"
        assert data["year"]    == 2024
        assert data["total_cancellations"] >= 1
        assert isinstance(data["reasons"], list)
        assert len(data["reasons"]) >= 1

    def test_cancellation_reasons_labels_human_readable(self, client):
        response = client.get("/api/v1/graph/cancellation-reasons/LAX?year=2024")
        labels = {r["label"] for r in response.json()["reasons"]}
        # seed data has A (Carrier) and B (Weather)
        assert "Carrier" in labels
        assert "Weather" in labels

    def test_cancellation_reasons_pct_sums_to_100(self, client):
        response = client.get("/api/v1/graph/cancellation-reasons/LAX?year=2024")
        total = sum(r["pct_of_cancelled"] for r in response.json()["reasons"])
        assert abs(total - 100.0) < 1.0

    def test_cancellation_reasons_counts_are_positive(self, client):
        response = client.get("/api/v1/graph/cancellation-reasons/LAX?year=2024")
        for reason in response.json()["reasons"]:
            assert reason["count"] >= 1

    def test_cancellation_reasons_no_data_404(self, client):
        # 2023 has no cancellations in seed data for ORD
        response = client.get("/api/v1/graph/cancellation-reasons/ORD?year=2023")
        assert response.status_code == 404

    def test_cancellation_reasons_unknown_airport_404(self, client):
        response = client.get("/api/v1/graph/cancellation-reasons/ZZZ?year=2024")
        assert response.status_code == 404