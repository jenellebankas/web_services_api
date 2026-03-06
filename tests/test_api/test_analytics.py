# tests/test_api/test_analytics.py
def test_airport_delays_lax(client):
    response = client.get("/api/v1/analytics/airport-delays/LAX")
    assert response.status_code == 200
    data = response.json()
    assert data["airport"] == "LAX"
    assert isinstance(data["total_flights"], int)
    assert isinstance(data["avg_arrival_delay"], (int, float))
    assert 0 <= data["delay_rate"] <= 1


def test_disruption_score(client):

    response = client.get("api/v1/analytics/disruption-score/JFK?year=2023")

    assert response.status_code == 200
    data = response.json()
    assert "disruption_score" in data
    assert isinstance(data["disruption_score"], (int, float))


def test_year_over_year(client):
    response = client.get("/api/v1/analytics/year-over-year/LAX")
    assert response.status_code == 200
    data = response.json()
    assert "airport" in data
    assert "year_2023" in data
    assert "year_2024" in data
