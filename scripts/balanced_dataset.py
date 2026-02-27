# scripts/seed_balanced_db.py
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
        time_str = str(int(hhmm_value)).zfill(4)
        hour = int(time_str[:2])
        minute = int(time_str[2:])

        if hour == 24:
            hour = 0
            flight_date += timedelta(days=1)

        hour = max(0, min(23, hour))
        minute = max(0, min(59, minute))

        return datetime.combine(flight_date, time(hour, minute))

    except (ValueError, TypeError):
        return None


def stratified_sample_by_origin_airline(df: pd.DataFrame, n_target: int, random_state: int = 42) -> pd.DataFrame:
    """
    Take a sample of size n_target from df while preserving the joint distribution
    of (origin, reporting_airline) as much as possible.
    """
    if len(df) <= n_target:
        return df.copy()

    # Work out how many rows to keep per (origin, reporting_airline) group
    counts = df.groupby(["origin", "reporting_airline"]).size().reset_index(name="count")
    counts["frac"] = counts["count"] / counts["count"].sum()
    counts["n_keep"] = (counts["frac"] * n_target).round().astype(int)

    # Ensure we do not ask more than the group size and at least 1 when group is present
    counts["n_keep"] = counts.apply(
        lambda r: min(r["count"], max(1, r["n_keep"])) if r["count"] > 0 else 0,
        axis=1,
    )

    # Fix rounding so total == n_target
    diff = n_target - counts["n_keep"].sum()
    if diff != 0:
        # Adjust the largest groups by +1 or -1 until total matches
        sign = 1 if diff > 0 else -1
        for idx in counts.sort_values("count", ascending=False).index:
            if diff == 0:
                break
            new_val = counts.at[idx, "n_keep"] + sign
            if 0 < new_val <= counts.at[idx, "count"]:
                counts.at[idx, "n_keep"] = new_val
                diff -= sign

    # Now sample per group
    pieces = []
    for (origin, carrier), row_info in counts.set_index(["origin", "reporting_airline"]).iterrows():
        k = int(row_info["n_keep"])
        group = df[(df["origin"] == origin) & (df["reporting_airline"] == carrier)]
        if k > 0 and len(group) > 0:
            if len(group) <= k:
                pieces.append(group)
            else:
                pieces.append(group.sample(n=k, random_state=random_state))
    sampled = pd.concat(pieces, ignore_index=True)
    # Shuffle once more
    sampled = sampled.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    return sampled


def load_balanced_flights(parquet_2023: str, parquet_2024: str,
                          target_total: int = 350_000) -> pd.DataFrame:
    """
    Build a balanced DataFrame:
      - 50% from 2023, 50% from 2024
      - within each year, preserve origin+airline mix
    """
    target_per_year = target_total // 2

    df23 = pd.read_parquet(parquet_2023)
    df24 = pd.read_parquet(parquet_2024)

    df23_sample = stratified_sample_by_origin_airline(df23, target_per_year, random_state=42)
    df24_sample = stratified_sample_by_origin_airline(df24, target_per_year, random_state=43)

    balanced = pd.concat([df23_sample, df24_sample], ignore_index=True)
    balanced = balanced.sample(frac=1.0, random_state=99).reset_index(drop=True)

    print(
        f"Balanced dataset: {len(df23_sample):,} from 2023, "
        f"{len(df24_sample):,} from 2024, total {len(balanced):,} rows."
    )

    # Quick sanity checks
    print("\nTop origins (balanced):")
    print(balanced["origin"].value_counts().head(10))
    print("\nTop airlines (balanced):")
    print(balanced["reporting_airline"].value_counts().head(10))

    return balanced


def seed_balanced_flight_data(parquet_2023: str, parquet_2024: str,
                              target_total: int = 350_000):
    df = load_balanced_flights(parquet_2023, parquet_2024, target_total)

    db: Session = SessionLocal()
    try:
        for _, row in df.iterrows():
            flight_date = pd.to_datetime(row["flight_date"]).date()

            flight = models.Flight(
                flight_date=flight_date,
                reporting_airline=row["reporting_airline"],
                flight_num_reporting_airline=int(row["flight_num_reporting_airline"]),
                origin=row["origin"],
                dest=row["dest"],
                crs_dep_time=hhmm_to_datetime(flight_date, row["crs_dep_time"]),
                dep_time=hhmm_to_datetime(flight_date, row["dep_time"]) if not pd.isna(row["dep_time"]) else None,
                crs_arr_time=hhmm_to_datetime(flight_date, row["crs_arr_time"]),
                arr_time=hhmm_to_datetime(flight_date, row["arr_time"]) if not pd.isna(row["arr_time"]) else None,
                dep_delay_minutes=int(row["dep_delay_minutes"]) if not pd.isna(row["dep_delay_minutes"]) else None,
                arr_delay_minutes=int(row["arr_delay_minutes"]) if not pd.isna(row["arr_delay_minutes"]) else None,
                dep_del_15=int(row["dep_del_15"]) if not pd.isna(row["dep_del_15"]) else None,
                arr_del_15=int(row["arr_del_15"]) if not pd.isna(row["arr_del_15"]) else None,
                cancelled=int(row["cancelled"]),
                cancellation_code=row["cancellation_code"] if row["cancellation_code"] != "NA" else None,
                diverted=int(row["diverted"]),
                carrier_delay=int(row["carrier_delay"]) if not pd.isna(row["carrier_delay"]) else None,
                weather_delay=int(row["weather_delay"]) if not pd.isna(row["weather_delay"]) else None,
                nas_delay=int(row["nas_delay"]) if not pd.isna(row["nas_delay"]) else None,
                security_delay=int(row["security_delay"]) if not pd.isna(row["security_delay"]) else None,
                late_aircraft_delay=int(row["late_aircraft_delay"]) if not pd.isna(row["late_aircraft_delay"]) else None,
                distance=int(row["distance"]) if not pd.isna(row["distance"]) else None,
            )
            db.add(flight)

        db.commit()
        print(f"Seeded balanced dataset with {len(df):,} flights (≈{len(df)//2:,} per year)")
    finally:
        db.close()


if __name__ == "__main__":
    seed_balanced_flight_data(
        "datasets/flights_2023.parquet",
        "datasets/flights_2024.parquet",
        target_total=350_000,
    )
