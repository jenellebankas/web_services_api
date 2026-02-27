# scripts/seed_db.py
import pandas as pd
from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from pathlib import Path
import sys


sys.path.append(str(Path(__file__).parent.parent))
from app.database import SessionLocal, engine
from app import models

models.Base.metadata.create_all(bind=engine)


def hhmm_to_datetime(flight_date, hhmm_value):
    """Convert HHMM to datetime, handling edge cases"""
    if pd.isna(hhmm_value) or hhmm_value == '':
        return None

    try:
        # Convert to string, handle weird values
        time_str = str(int(hhmm_value)).zfill(4)
        hour = int(time_str[:2])
        minute = int(time_str[2:])

        # Fix invalid hours (24:00 → 00:00 next day)
        if hour == 24:
            hour = 0
            flight_date += timedelta(days=1)

        # Clamp invalid values
        hour = max(0, min(23, hour))
        minute = max(0, min(59, minute))

        return datetime.combine(flight_date, time(hour, minute))

    except (ValueError, TypeError):
        return None


def seed_flight_data(parquet_path: str, year: int):
    df = pd.read_parquet(parquet_path, nrows=50000)  # Sample for dev (remove nrows for full)

    db: Session = SessionLocal()
    try:
        for _, row in df.iterrows():
            flight = models.Flight(
                flight_date=pd.to_datetime(row['flight_date']).date(),
                reporting_airline=row['reporting_airline'],
                flight_num_reporting_airline=int(row['flight_num_reporting_airline']),
                origin=row['origin'],
                dest=row['dest'],
                crs_dep_time=hhmm_to_datetime(pd.to_datetime(row['flight_date']).date(), row['crs_dep_time']),
                dep_time=hhmm_to_datetime(pd.to_datetime(row['flight_date']).date(), row['dep_time']) if not pd.isna(
                    row['dep_time']) else None,
                crs_arr_time=hhmm_to_datetime(pd.to_datetime(row['flight_date']).date(), row['crs_arr_time']),
                arr_time=hhmm_to_datetime(pd.to_datetime(row['flight_date']).date(), row['arr_time']) if not pd.isna(
                    row['arr_time']) else None,
                dep_delay_minutes=int(row['dep_delay_minutes']) if not pd.isna(row['dep_delay_minutes']) else None,
                arr_delay_minutes=int(row['arr_delay_minutes']) if not pd.isna(row['arr_delay_minutes']) else None,
                dep_del_15=int(row['dep_del_15']) if not pd.isna(row['dep_del_15']) else None,
                arr_del_15=int(row['arr_del_15']) if not pd.isna(row['arr_del_15']) else None,
                cancelled=int(row['cancelled']),
                cancellation_code=row['cancellation_code'] if row['cancellation_code'] != 'NA' else None,
                diverted=int(row['diverted']),
                carrier_delay=int(row['carrier_delay']) if not pd.isna(row['carrier_delay']) else None,
                weather_delay=int(row['weather_delay']) if not pd.isna(row['weather_delay']) else None,
                nas_delay=int(row['nas_delay']) if not pd.isna(row['nas_delay']) else None,
                security_delay=int(row['security_delay']) if not pd.isna(row['security_delay']) else None,
                late_aircraft_delay=int(row['late_aircraft_delay']) if not pd.isna(
                    row['late_aircraft_delay']) else None,
                distance=int(row['distance']) if not pd.isna(row['distance']) else None,
            )
            db.add(flight)
        db.commit()
        print(f"Seeded {len(df)} flights from {year}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_flight_data("datasets/flights_2023.parquet", 2023)
    seed_flight_data("datasets/flights_2024.parquet", 2024)
