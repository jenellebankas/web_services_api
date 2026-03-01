def test_airport_delays_lax(client):
    response = client.get("/api/v1/analytics/airport-delays/LAX")
    assert response.status_code == 200
    data = response.json()
    assert data["airport"] == "LAX"
    assert isinstance(data["total_flights"], int)
    assert isinstance(data["avg_arrival_delay"], (int, float))
    assert 0 <= data["delay_rate"] <= 1


def test_disruption_score(client):
    response = client.get("/api/v1/analytics/disruption-score/LAX")
    assert response.status_code == 200
    data = response.json()
    assert "disruption_score" in data
    assert isinstance(data["disruption_score"], (int, float))


def test_year_over_year(client):
    response = client.get("/api/v1/analytics/year-over-year/LAX")
    assert response.status_code == 200
    data = response.json()
    assert "airport" in data
    assert "current_year_delay_rate" in data
