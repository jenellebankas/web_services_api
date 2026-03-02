def test_get_flights_basic(client):
    response = client.get("/api/v1/flights/?origin=LAX&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5
    assert all("origin" in flight for flight in data)


def test_get_flights_no_params(client):
    response = client.get("/api/v1/flights/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_flights_nonexistent_airport(client):
    response = client.get("/api/v1/flights/?origin=ZZZ")
    assert response.status_code == 200  # Should return empty list, not 404
    data = response.json()
    assert len(data) == 0
