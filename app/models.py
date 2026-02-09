# code generated 09/02/2026 using perplexity.ai

# app/models.py
from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    # add whatever fields you need

    daily_wellbeing = relationship("DailyWellbeing", back_populates="user")


class DailyWellbeing(Base):
    __tablename__ = "daily_wellbeing"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    stress_level = Column(Integer, nullable=False)
    sleep_hours = Column(Float)
    study_hours = Column(Float)
    mood_score = Column(Integer)
    energy_level = Column(Integer)

    user = relationship("User", back_populates="daily_wellbeing")
