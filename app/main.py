from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app import models
from app.api.v1.routers import flights, analytics

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Aviation Disruption API",
    description="REST API for aviation disruption analytics",
    version="1.0.0"
)

# ADD CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.streamlit.app"],  # Streamlit Cloud
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Aviation Disruption API",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "flights": "/api/v1/flights",
        "analytics": "/api/v1/analytics"
    }


@app.get("/dashboard")
async def dashboard_redirect():
    return RedirectResponse(url="https://webservicesapi-dashboard.streamlit.app")

app.include_router(flights.router, prefix="/api/v1/flights", tags=["flights"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
