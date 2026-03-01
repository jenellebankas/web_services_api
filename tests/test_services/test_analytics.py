# tests/test_services/test_analytics.py
def test_analytics_service(db_session):  # your test DB fixture
    service = AnalyticsService(db_session)
    result = service.get_airport_delays("LAX")
    assert result.airport == "LAX"
    assert result.total_flights >= 0
