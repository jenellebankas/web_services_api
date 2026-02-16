# app/schemas.py
from pydantic import BaseModel


# ---------- User ----------

class UserBase(BaseModel):
    # You can add more user fields later (e.g. email, name)
    pass


class UserCreate(UserBase):
    # For now, nothing required beyond defaults; adjust if you add fields
    pass


class UserRead(UserBase):
    id: int

    class Config:
        orm_mode = True


# ---------- DailyWellbeing ----------

class DailyWellbeingBase(BaseModel):
    anxiety_level: int | None = None
    self_esteem: int | None = None
    mental_health_history: int | None = None
    depression: int | None = None
    headache: int | None = None
    blood_pressure: int | None = None
    sleep_quality: int | None = None
    breathing_problem: int | None = None
    noise_level: int | None = None
    living_conditions: int | None = None
    safety: int | None = None
    basic_needs: int | None = None
    academic_performance: int | None = None
    study_load: int | None = None
    teacher_student_relationship: int | None = None
    future_career_concerns: int | None = None
    social_support: int | None = None
    peer_pressure: int | None = None
    extracurricular_activities: int | None = None
    bullying: int | None = None
    stress_level: int | None = None


class DailyWellbeingCreate(DailyWellbeingBase):
    user_id: int


class DailyWellbeingUpdate(DailyWellbeingBase):
    # All fields optional for partial updates
    pass


class DailyWellbeingRead(DailyWellbeingBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True
