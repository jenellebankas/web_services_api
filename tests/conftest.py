import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, engine
from app.main import app


@pytest.fixture(scope="function")
def test_db():
    # Create fresh test DB
    test_db_path = Path("test_aviation.db")
    test_db_url = f"sqlite:///{test_db_path}"

    # Create tables
    from app.models import Base
    Base.metadata.create_all(bind=engine)

    # Seed minimal test data
    conn = sqlite3.connect(test_db_path)
    conn.execute("INSERT INTO flights (flight_date, origin, dest, arr_delay_minutes, cancelled) VALUES "
                 "('2023-01-01', 'LAX', 'JFK', 25, 0), "
                 "('2023-01-02', 'LAX', 'SFO', 0, 0), "
                 "('2023-01-03', 'LAX', 'JFK', 45, 0)")
    conn.commit()
    conn.close()

    yield test_db_url

    # Cleanup
    test_db_path.unlink(missing_ok=True)


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        # Override DB dependency to use test DB
        from sqlalchemy.orm import sessionmaker
        TEST_SESSION = sessionmaker(bind=engine)
        test_session = TEST_SESSION()
        try:
            yield test_session
        finally:
            test_session.close()

    app.dependency_overrides[SessionLocal] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
