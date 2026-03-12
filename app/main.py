# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app import models
from app.api.v1.routers import flights, analytics, graph, keys
from app.database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="US Aviation Disruption API",
    description="REST API for US aviation disruption analytics",
    version="1.0.0"
)

# adding cors middleware to connect streamlit dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.streamlit.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# health endpoint for render
@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


# available endpoints
@app.get("/")
async def root():
    return {
        "message": "US Aviation Disruption API",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "flights": "/api/v1/flights",
        "analytics": "/api/v1/analytics",
        "graph": "/api/v1/graph",
    }


# dashboard redirect pointing to streamlit
@app.get("/dashboard")
async def dashboard_redirect():
    return RedirectResponse(url="https://webservicesapi-dashboard.streamlit.app")


app.include_router(flights.router, prefix="/api/v1", tags=["flights"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(graph.router, prefix="/api/v1", tags=["graph"])
app.include_router(keys.router,      prefix="/api/v1", tags=["authentication"])
