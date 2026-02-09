# code generated 09/02/2026 using perplexity.ai

# app/models.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    daily_wellbeing = relationship("DailyWellbeing", back_populates="user")


class DailyWellbeing(Base):
    __tablename__ = "daily_wellbeing"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="daily_wellbeing")

    anxiety_level = Column(Integer, nullable=True)
    self_esteem = Column(Integer, nullable=True)
    mental_health_history = Column(Integer, nullable=True)
    depression = Column(Integer, nullable=True)
    headache = Column(Integer, nullable=True)
    blood_pressure = Column(Integer, nullable=True)
    sleep_quality = Column(Integer, nullable=True)
    breathing_problem = Column(Integer, nullable=True)
    noise_level = Column(Integer, nullable=True)
    living_conditions = Column(Integer, nullable=True)
    safety = Column(Integer, nullable=True)
    basic_needs = Column(Integer, nullable=True)
    academic_performance = Column(Integer, nullable=True)
    study_load = Column(Integer, nullable=True)
    teacher_student_relationship = Column(Integer, nullable=True)
    future_career_concerns = Column(Integer, nullable=True)
    social_support = Column(Integer, nullable=True)
    peer_pressure = Column(Integer, nullable=True)
    extracurricular_activities = Column(Integer, nullable=True)
    bullying = Column(Integer, nullable=True)
    stress_level = Column(Integer, nullable=True)
