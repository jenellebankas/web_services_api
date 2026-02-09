# code generated 09/02/2026 using perplexity.ai

# scripts/import_daily_wellbeing.py

from app.database import SessionLocal
from app import models

from sqlalchemy.orm import Session
from datetime import date
from pathlib import Path


import csv

# Allow imports like "from app.database import SessionLocal, engine"
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

DATASET_PATH = Path("datasets/raw/StressLevelDataset.csv")


def parse_date(raw: str) -> date:
    # Adjust this to match your CSV format, or fix date elsewhere.
    # If your CSV has no date, you can synthesize one (e.g. a sequence of days).
    # For now, assume YYYY-MM-DD:
    return date.fromisoformat(raw)


def main() -> None:
    # Create DB tables if they don't exist (optional if you do this elsewhere)
    models.Base.metadata.create_all(bind=SessionLocal.kw['bind'])  # adapt if needed

    db: Session = SessionLocal()

    try:
        with DATASET_PATH.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader, start=1):
                user_id = i

                # Ensure user exists (very simple example)
                user = db.query(models.User).filter_by(id=user_id).first()
                if user is None:
                    user = models.User(id=user_id)
                    db.add(user)
                    db.flush()

                wellbeing = models.DailyWellbeing(
                    user_id=user_id,
                    anxiety_level=int(row["anxiety_level"]),
                    self_esteem=int(row["self_esteem"]),
                    mental_health_history=int(row["mental_health_history"]),
                    depression=int(row["depression"]),
                    headache=int(row["headache"]),
                    blood_pressure=int(row["blood_pressure"]),
                    sleep_quality=int(row["sleep_quality"]),
                    breathing_problem=int(row["breathing_problem"]),
                    noise_level=int(row["noise_level"]),
                    living_conditions=int(row["living_conditions"]),
                    safety=int(row["safety"]),
                    basic_needs=int(row["basic_needs"]),
                    academic_performance=int(row["academic_performance"]),
                    study_load=int(row["study_load"]),
                    teacher_student_relationship=int(row["teacher_student_relationship"]),
                    future_career_concerns=int(row["future_career_concerns"]),
                    social_support=int(row["social_support"]),
                    peer_pressure=int(row["peer_pressure"]),
                    extracurricular_activities=int(row["extracurricular_activities"]),
                    bullying=int(row["bullying"]),
                    stress_level=int(row["stress_level"]),
                )

                db.add(wellbeing)

            db.commit()
            print(f"Imported {i} rows into daily_wellbeing")

    except Exception as e:
        db.rollback()
        print("Error during import:", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
