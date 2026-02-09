# code generated 09/02/2026 using perplexity.ai

# scripts/import_daily_wellbeing.py

import csv
from datetime import date
from pathlib import Path

import sqlalchemy
from sqlalchemy.orm import Session

# Allow imports like "from app.database import SessionLocal, engine"
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app import models

DATASET_PATH = Path("../datasets/StressLevelDataset.csv")

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
                # Map CSV fields -> model fields
                # Adjust these keys to match your actual CSV header names.
                # Example assumptions:
                #   row["StudentID"], row["Date"], row["StressLevel"],
                #   row["SleepHours"], row["StudyHours"], row["Mood"], row["Energy"]
                user_id = int(row.get("StudentID", i))  # fallback: synthetic ID
                # If you don't have real users yet, you can
                #   1) create them here, or
                #   2) map all rows to a small set of synthetic users.

                # Example: map every 100 rows to one of 10 users
                user_id = (i % 10) + 1

                # Ensure user exists (very simple example)
                user = db.query(models.User).filter_by(id=user_id).first()
                if user is None:
                    user = models.User(id=user_id, email=f"user{user_id}@example.com")
                    db.add(user)
                    db.flush()

                wellbeing = models.DailyWellbeing(
                    user_id=user_id,
                    date=parse_date(row.get("Date", "2025-01-01")),
                    stress_level=int(row["StressLevel"]),
                    sleep_hours=float(row.get("SleepHours") or 0.0),
                    study_hours=float(row.get("StudyHours") or 0.0),
                    mood_score=int(row.get("Mood") or 3),
                    energy_level=int(row.get("Energy") or 3),
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