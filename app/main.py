from fastapi import FastAPI
from app.database import engine
from app import models
from app.api.v1.routers import flights, analytics

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Aviation Disruption API")

app.include_router(flights.router, prefix="/api/v1/flights", tags=["flights"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
