from fastapi import FastAPI
from .database import engine
from .routers import wellbeing
from .import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(wellbeing.router, prefix="/wellbeing", tags=["wellbeing"])
