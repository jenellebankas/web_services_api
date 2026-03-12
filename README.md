# US Aviation Disruption API 

---

Data-driven REST API for US flight delay analytics, built on the Bureau of Transportation Statistics (BTS) data for 
2023-2024.

Live API: https://web-services-api.onrender.com
Swagger Docs: https://web-services-api.onrender.com/docs
Live Dashboard: https://webservicesapi-dashboard.streamlit.app

## Overview
 
The Aviation Disruption API transforms ~1 million BTS flight records into actionable analytics. It provides standard 
delay/cancellation metrics alongside a novel graph-based network analysis layer that models the US airport system as a 
directed graph, enabling delay propagation simulation and network influence scoring.
### Key Features
 
- **18+ REST endpoints** across analytics, graph analysis, and CRUD
- **Disruption scoring** — composite 0–100 score per airport/year
- **Route risk analysis** — compare up to 10 routes by historical reliability
- **Graph contagion scores** — NetworkX-based centrality scoring for network influence
- **Ripple effect simulation** — propagate a seed delay through an aircraft's daily schedule
- **Delay cause breakdown** — split delay minutes by carrier/weather/NAS/security/late aircraft
- **Interactive Streamlit dashboard** connected to the live API
 
---
 
## Tech Stack
 
| Component        | Technology           | Reason                                         |
|------------------|----------------------|------------------------------------------------|
| API Framework    | FastAPI              | Auto-docs, async, Pydantic validation          |
| Database         | SQLite + SQLAlchemy  | Zero-config, portable, read-heavy workload     |
| Graph Analysis   | NetworkX             | Centrality algorithms, in-process graph cache  |
| Dashboard        | Streamlit            | Rapid UI, direct API integration               |
| Deployment       | Render               | Auto-deploy from GitHub, free tier             |
| Testing          | pytest               | 70 tests — unit + integration                  |


## Authentication

Write endpoints (POST, PUT, DELETE) require an `X-API-Key` header. Read and analytics endpoints are public.

```bash
# Authenticated request
curl -X POST https://web-services-api.onrender.com/api/v1/flights/ \
  -H "X-API-Key: your-key-here" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Public request — no key needed
curl https://web-services-api.onrender.com/api/v1/analytics/disruption-score/JFK
```

API keys are managed via `/api/v1/keys` (requires an existing valid key). To generate the first admin key run 
`python scripts/create_admin_key.py` after deployment. If this does not work run 
`PYTHONPATH=. python scripts/create_admin_key.py` after deployment.


## Project Structure 

```
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
│   │           ├── analytics.py
│   │           ├── flights.py
│   │           ├── graph.py
│   │           └── keys.py
│   ├── core
│   │   ├── __init__.py
│   │   └── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── services
│       ├── __init__.py
│       ├── analytics_service.py
│       ├── flight_service.py
│       ├── graph_analytics_service.py
│       └── graph_service.py
├── aviation.db
├── dashboard
│   ├── __init__.py
│   ├── components
│   │   ├── __init__.py
│   │   ├── api.py
│   │   └── metrics.py
│   └── streamlit_app.py
├── datasets
│   ├── flights_2023.parquet
│   └── flights_2024.parquet
├── docs
│   ├── aviation_api_documentation.pdf
│   └── project-requirements.md
├── notebooks
│   └── 01_data_exploration.ipynb
├── requirements.txt
├── scripts
│   ├── balanced_dataset.py
│   ├── create_admin_key.py
│   ├── reset_db.py
│   └── seed_db.py
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── test_api
    │   ├── test_analytics.py
    │   ├── test_flights.py
    │   └── test_graph.py
    └── test_services
        ├── test_services_analytics.py
        └── test_services_graph.py

```

# Local Setup 

## *Prerequisites*

- Python 3.12+
- pip 

## 1. Clone the repo
```bash
git clone https://github.com/jenellebankas/web_services_api.git
cd web_services_api
```

## 2. Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
.venv\Scripts\activate
```

## 3. Install dependencies 
```bash
pip install -r requirements.txt
```

## 4. Seed the database
```bash
python scripts/balanced_dataset.py
```

- must note that using balanced_dataset.py ensures a stratified dataset if seed_db.py used, data is just split by 
- number.

## 5. Run the API
```bash
uvicorn app.main:app --reload
```

The API will be available at: http://localhost:8000
Interactive docs at: http://localhost:8000/docs

If you want to run the dashboard 
```bash
cd dashboard
streamlit run streamlit_app.py
```

## Running Tests 

```bash
pytest
```

The expected output is 70 passed.

For verbose output:
```bash
pytest -v
```
for API tests only:
```bash
pytest tests/test_api/
```
For Service tests only:

```bash
pytest tests/test_services/
```

## API Endpoints 

### Flights (CRUD)

| Method    | Endpoint                | Description                                              |
|-----------|-------------------------|----------------------------------------------------------|
| `GET`     | `/api/v1/flights/`      | List flights (filterable by origin, dest, airline, date) |
| `GET`     | `/api/v1/flights/{id}`  | Get flight by ID                                         |
| `POST`    | `/api/v1/flights/`      | Create new flight record                                 |
| `PUT`     | `/api/v1/flights/{id}`  | Update flight record                                     |
| `DELETE`  | `/api/v1/flights/{id}`  | Delete flight record                                     |


### Analytics
 
| Endpoint                                        | Description                               |
|-------------------------------------------------|-------------------------------------------|
| `/api/v1/analytics/airport-delays/{airport}`    | Delay stats for an airport                |
| `/api/v1/analytics/disruption-score/{airport}`  | Composite disruption score (0–100)        |
| `/api/v1/analytics/year-over-year/{airport}`    | 2023 vs 2024 comparison                   |
| `/api/v1/analytics/compare-airports`            | Side-by-side multi-airport comparison     |
| `/api/v1/analytics/route-risk`                  | Risk score for origin→destination routes  |
| `/api/v1/analytics/best-time/{airport}`         | Best/worst hours to depart                |
| `/api/v1/analytics/daily-pattern`               | Hourly delay pattern                      |
| `/api/v1/analytics/weekly-pattern`              | Day-of-week delay pattern                 |
| `/api/v1/analytics/leaderboard/punctuality`     | Best/worst airports by OTP                |
| `/api/v1/analytics/carrier-performance`         | Airline on-time performance ranking       |
| `/api/v1/analytics/monthly-trends`              | Monthly delay/cancellation trends         |
| `/api/v1/analytics/system-overview`             | National-level summary stats              |
 
### Graph / Network Analysis
 
| Endpoint                                        | Description                                                       |
|-------------------------------------------------|-------------------------------------------------------------------|
| `/api/v1/graph/contagion-score/{airport}`       | Network influence score (0–1)                                     |
| `/api/v1/graph/contagion-leaderboard`           | Most/least influential airports                                   |
| `/api/v1/graph/network-neighbors/{airport}`     | Airports reachable within N hops                                  |
| `/api/v1/graph/ripple-effect`                   | Simulate delay propagation through aircraft schedule              |
| `/api/v1/graph/delay-causes/{airport}`          | Delay minutes split by cause                                      |
| `/api/v1/graph/cancellation-reasons/{airport}`  | Cancellation breakdown by BTS code                                |
| `/api/v1/graph/flights/carriers`                | All carrier codes (for dropdowns)                                 |
| `/api/v1/graph/flights/numbers`                 | Flight numbers for a carrier                                      |
| `/api/v1/graph/flights/dates`                   | Dates a specific flight operated                                  |
 
### System
 
| Endpoint             | Description                                |
|----------------------|--------------------------------------------|
| `GET /health`        | Health check — returns `{"status": "ok"}`  |
| `GET /docs`          | Interactive Swagger UI                     |
| `GET /redoc`         | ReDoc documentation                        |
| `GET /openapi.json`  | OpenAPI schema                             |


## Data Source 

US Bureau of Transportation Statistics (BTS) - On-Time Performance Data: https://www.transtats.bts.gov
Dataset covers all domestic US flights for 2023 and 2024
Licensed for academic and research use 

## API Documentation 

API documentation (PDF) is available in the repository:
docs/aviation_api_docs.pdf

Interactive Swagger UI: https://web-services-api.onrender.com/docs

## Deployment 

The API is currently deployed on Render (free tier) with automatic deployments triggered by pushes to main
- Health check: GET /health
- CORS configured for *.streamlit.app
- Environment: Python 3.12, uvicorn

## GenAI Declaration

This project was developed with the assistance of Claude (Anthropic) Perplexit and ChatGPT, in accordance with COMP3011
Green Light assessment policy. For full declaration, usage breakdown and coversation log exports please see the 
technical report appendix.