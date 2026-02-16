# US Flight Disruption

## File Tree
```
.
├── README.md
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   └── v1
│   │       ├── __init__.py
│   │       ├── deps.py
│   │       └── routers
│   │           ├── __init__.py
│   │           ├── airports.py
│   │           ├── analytics.py
│   │           └── flights.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── services
│       ├── __init__.py
│       ├── analystics_service.py
│       └── flight_service.py
├── data
│   ├── airports_2023.csv
│   ├── airports_2024.csv
│   ├── flights_2023.csv
│   └── flights_2024.csv
├── deployment
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── pythonanywhere.sh
├── docs
│   ├── ERD.png
│   ├── api.html
│   └── architecture.png
├── pyproject.toml
├── requirements.txt
├── scripts
│   ├── reset_db.py
│   └── seed_db.py
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── test_api
    │   ├── test_analytics.py
    │   └── test_flights.py
    └── test_services
        └── test_analytics.py
```