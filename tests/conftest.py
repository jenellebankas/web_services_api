# tests/conftest.py
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import SessionLocal
from app.main import app
from app.models import Base
from app.services.graph_service import invalidate_graph_cache


# ---------------------------------------------------------------------------
# Seed rows — shared by all fixtures
# ---------------------------------------------------------------------------
# Enough data to exercise:
#   - analytics endpoints  (LAX, JFK, ORD)
#   - graph / contagion    (3-node network LAX→JFK→ORD)
#   - ripple effect        (AA flight 100, two legs on 2024-01-15)
#   - delay causes         (all five cause columns populated)
#   - cancellation reasons (codes A and B)

SEED_SQL = """
INSERT INTO flights
  (flight_date, reporting_airline, flight_num_reporting_airline,
   origin, dest,
   crs_dep_time, dep_time, crs_arr_time, arr_time,
   dep_delay_minutes, arr_delay_minutes,
   dep_del_15, arr_del_15,
   cancelled, cancellation_code, diverted,
   carrier_delay, weather_delay, nas_delay, security_delay, late_aircraft_delay,
   distance)
VALUES
  -- AA 100: leg 1  LAX→JFK  (delayed, carrier cause)
  ('2024-01-15', 'AA', 100, 'LAX', 'JFK',
   '2024-01-15 08:00:00', '2024-01-15 08:25:00', '2024-01-15 16:00:00', '2024-01-15 16:30:00',
   25, 30, 1, 1, 0, NULL, 0,
   30, 0, 0, 0, 0, 2475),

  -- AA 100: leg 2  JFK→ORD  (same flight number, same date — ripple chain)
  -- dep 18:00, prev arr 16:00 → ground = 120 min, buffer = 90 min
  ('2024-01-15', 'AA', 100, 'JFK', 'ORD',
   '2024-01-15 18:00:00', '2024-01-15 18:20:00', '2024-01-15 20:00:00', '2024-01-15 20:25:00',
   20, 25, 1, 1, 0, NULL, 0,
   0, 0, 25, 0, 0, 740),

  -- Normal LAX flight (on-time)
  ('2024-01-16', 'UA', 200, 'LAX', 'SFO',
   '2024-01-16 09:00:00', '2024-01-16 09:02:00', '2024-01-16 10:30:00', '2024-01-16 10:28:00',
   2, -2, 0, 0, 0, NULL, 0,
   0, 0, 0, 0, 0, 337),

  -- LAX cancellation — carrier (A)
  ('2024-01-17', 'AA', 300, 'LAX', 'DFW',
   '2024-01-17 07:00:00', NULL, '2024-01-17 12:00:00', NULL,
   NULL, NULL, NULL, NULL, 1, 'A', 0,
   NULL, NULL, NULL, NULL, NULL, 1235),

  -- LAX cancellation — weather (B)
  ('2024-01-18', 'DL', 400, 'LAX', 'SEA',
   '2024-01-18 06:00:00', NULL, '2024-01-18 08:30:00', NULL,
   NULL, NULL, NULL, NULL, 1, 'B', 0,
   NULL, NULL, NULL, NULL, NULL, 954),

  -- 2023 row for year-over-year tests
  ('2023-06-01', 'AA', 500, 'LAX', 'JFK',
   '2023-06-01 10:00:00', '2023-06-01 10:35:00', '2023-06-01 18:00:00', '2023-06-01 18:40:00',
   35, 40, 1, 1, 0, NULL, 0,
   20, 10, 10, 0, 0, 2475),

  -- JFK delayed flight (late aircraft cause)
  ('2024-02-01', 'DL', 600, 'JFK', 'MIA',
   '2024-02-01 11:00:00', '2024-02-01 11:50:00', '2024-02-01 14:00:00', '2024-02-01 14:55:00',
   50, 55, 1, 1, 0, NULL, 0,
   0, 0, 0, 0, 55, 1090),

  -- ORD on-time flight
  ('2024-02-02', 'UA', 700, 'ORD', 'DEN',
   '2024-02-02 13:00:00', '2024-02-02 13:05:00', '2024-02-02 15:00:00', '2024-02-02 14:58:00',
   5, -2, 0, 0, 0, NULL, 0,
   0, 0, 0, 0, 0, 920)
;
"""


@pytest.fixture(scope="function")
def test_db(tmp_path):
    test_db_path = tmp_path / "test_aviation.db"
    test_db_url  = f"sqlite:///{test_db_path}"

    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)

    conn = sqlite3.connect(test_db_path)
    conn.execute(SEED_SQL)
    conn.commit()
    conn.close()

    yield test_db_url

    invalidate_graph_cache()          # clear in-process graph after each test
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_db):
    test_engine = create_engine(test_db, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        invalidate_graph_cache()


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        test_engine = create_engine(test_db, connect_args={"check_same_thread": False})
        TestSessionLocal = sessionmaker(bind=test_engine)
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[SessionLocal] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    invalidate_graph_cache()