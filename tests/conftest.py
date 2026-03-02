import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import SessionLocal  # Keep for dependency override
from app.main import app
from app.models import Base


@pytest.fixture(scope="function")
def test_db(tmp_path):
    test_db_path = tmp_path / "test_aviation.db"
    test_db_url = f"sqlite:///{test_db_path}"

    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)

    # COMPLETE: All required columns based on error pattern
    conn = sqlite3.connect(test_db_path)
    conn.execute("""
        INSERT INTO flights 
        (flight_date, origin, dest, arr_delay_minutes, cancelled, 
         reporting_airline, flight_num_reporting_airline, crs_dep_time, crs_arr_time) 
        VALUES 
        ('2023-01-01', 'LAX', 'JFK', 25, 0, 'AA', 1234, 1000, 1500),
        ('2023-01-02', 'LAX', 'SFO', 0, 0, 'UA', 5678, 2000, 2300),
        ('2023-01-03', 'LAX', 'JFK', 45, 0, 'DL', 9012, 1900, 2100)
    """)
    conn.commit()
    conn.close()

    yield test_db_url

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


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        test_engine = create_engine(test_db, connect_args={"check_same_thread": False})
        TestSessionLocal = sessionmaker(bind=test_engine)
        test_session = TestSessionLocal()
        try:
            yield test_session
        finally:
            test_session.close()

    app.dependency_overrides[SessionLocal] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
