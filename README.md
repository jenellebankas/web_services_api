# web_services_api

## File Tree
```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, startup, router includes
│   ├── config.py            # settings (DB URL, env config)
│   ├── models.py            # SQLAlchemy models (or split further)
│   ├── schemas.py           # Pydantic schemas (request/response)
│   ├── database.py          # DB engine, SessionLocal, Base
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── sessions.py      # work sessions
│   │   ├── wellbeing.py     # burnout/score endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analytics.py     # burnout score, balance score logic
│   │   └── auth.py          # auth helpers
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── dependencies.py  # get_current_user, etc.
│   │   └── security.py      # hashing, token utils
│   └── core/
│       ├── __init__.py
│       ├── logging.py       # optional: log config
│       └── exceptions.py    # custom exception classes/handlers
│
├── tests/
│   ├── __init__.py
│   ├── test_users.py
│   ├── test_sessions.py
│   └── test_wellbeing.py
│
├── docs/
│   ├── api_openapi_export.pdf   # exported Swagger/OpenAPI
│   ├── erd.png                  # DB diagram
│   └── architecture.png
│
├── .gitignore
├── requirements.txt or pyproject.toml
├── README.md
├── run_local.sh (optional helper)
└── REPORT_LINKS.md (optional: links to slides, deployed URL, etc.)

```