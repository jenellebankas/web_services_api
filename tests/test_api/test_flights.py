# tests/test_api/test_flights.py
from tests.conftest import AUTH_HEADERS
from app.main import app


# read endpoints
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
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_get_single_flight(client):
    # seed has flights — grab the first one
    flights = client.get("/api/v1/flights/").json()
    flight_id = flights[0]["id"]
    response = client.get(f"/api/v1/flights/{flight_id}")
    assert response.status_code == 200
    assert response.json()["id"] == flight_id


def test_get_single_flight_not_found(client):
    response = client.get("/api/v1/flights/999999")
    assert response.status_code == 404


# post requires auth

VALID_FLIGHT = {
    "flight_date": "2024-03-01",
    "reporting_airline": "AA",
    "flight_num_reporting_airline": 999,
    "origin": "LAX",
    "dest": "JFK",
    "crs_dep_time": "2024-03-01T08:00:00",
    "dep_time": "2024-03-01T08:10:00",
    "crs_arr_time": "2024-03-01T16:00:00",
    "arr_time": "2024-03-01T16:15:00",
    "dep_delay_minutes": 10.0,
    "arr_delay_minutes": 15.0,
    "dep_del_15": 0,
    "arr_del_15": 1,
    "cancelled": 0,
    "diverted": 0,
    "distance": 2475,
}


def test_create_flight_success(client):
    response = client.post("/api/v1/flights/", json=VALID_FLIGHT, headers=AUTH_HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert data["origin"] == "LAX"
    assert data["dest"] == "JFK"
    assert "id" in data


def test_create_flight_no_auth(client):
    """POST without API key should return 401."""
    from app.api.v1.deps import verify_api_key
    app.dependency_overrides.pop(verify_api_key, None)  # remove bypass
    response = client.post("/api/v1/flights/", json=VALID_FLIGHT)
    app.dependency_overrides[verify_api_key] = lambda: None  # restore
    assert response.status_code == 401


def test_create_flight_invalid_key(client):
    """POST with wrong API key should return 403."""
    from app.api.v1.deps import verify_api_key
    app.dependency_overrides.pop(verify_api_key, None)
    response = client.post(
        "/api/v1/flights/",
        json=VALID_FLIGHT,
        headers={"X-API-Key": "wrong-key"},
    )
    app.dependency_overrides[verify_api_key] = lambda: None
    assert response.status_code == 403


# update requires auth
def test_update_flight_success(client):
    # create a flight to update
    created = client.post("/api/v1/flights/", json=VALID_FLIGHT, headers=AUTH_HEADERS).json()
    flight_id = created["id"]

    response = client.put(
        f"/api/v1/flights/{flight_id}",
        json={"arr_delay_minutes": 45.0},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["arr_delay_minutes"] == 45.0


def test_update_flight_not_found(client):
    response = client.put(
        "/api/v1/flights/999999",
        json={"arr_delay_minutes": 10.0},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404


def test_update_flight_no_auth(client):
    from app.api.v1.deps import verify_api_key
    flights = client.get("/api/v1/flights/").json()
    flight_id = flights[0]["id"]
    app.dependency_overrides.pop(verify_api_key, None)
    response = client.put(f"/api/v1/flights/{flight_id}", json={"arr_delay_minutes": 10.0})
    app.dependency_overrides[verify_api_key] = lambda: None
    assert response.status_code == 401


# delete requires auth

def test_delete_flight_success(client):
    # create a flight then delete it
    created = client.post("/api/v1/flights/", json=VALID_FLIGHT, headers=AUTH_HEADERS).json()
    flight_id = created["id"]

    response = client.delete(f"/api/v1/flights/{flight_id}", headers=AUTH_HEADERS)
    assert response.status_code == 204

    # confirm it's gone
    response = client.get(f"/api/v1/flights/{flight_id}")
    assert response.status_code == 404


def test_delete_flight_not_found(client):
    response = client.delete("/api/v1/flights/999999", headers=AUTH_HEADERS)
    assert response.status_code == 404


def test_delete_flight_no_auth(client):
    from app.api.v1.deps import verify_api_key
    flights = client.get("/api/v1/flights/").json()
    flight_id = flights[0]["id"]
    app.dependency_overrides.pop(verify_api_key, None)
    response = client.delete(f"/api/v1/flights/{flight_id}")
    app.dependency_overrides[verify_api_key] = lambda: None
    assert response.status_code == 401
