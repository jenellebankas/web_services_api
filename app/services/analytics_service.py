from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.schemas import (
    AirportComparisonItem, AirportComparisonResponse, AirportDelaysResponse,
    BestTimeItem, BestTimeResponse, DailyPatternResponse, DisruptionScoreResponse,
    HourlyPatternItem, LeaderboardItem, PunctualityLeaderboardResponse,
    RouteRiskItem, RouteRiskResponse, WeeklyPatternItem, WeeklyPatternResponse,
    YearOverYearResponse
)

DOW_MAP = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_airport_delays(self, airport: str) -> AirportDelaysResponse:
        result = self.db.execute(
            text("""
                SELECT COUNT(*) as total, AVG(COALESCE(arr_delay_minutes, 0)) as avg_delay,
                       SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) as delayed,
                       SUM(cancelled) as cancelled
                FROM flights WHERE origin = :airport
            """), {"airport": airport}
        ).fetchone()

        total = result.total or 0
        if total == 0:
            raise ValueError("No data")

        return AirportDelaysResponse(
            airport=airport,
            total_flights=int(total),
            avg_arrival_delay=round(float(result.avg_delay or 0), 1),
            delay_rate=round(float(result.delayed or 0) / total, 3),
            cancel_rate=round(float(result.cancelled or 0) / total, 3),
            worst_day="Monday"
        )

    def get_disruption_score(self, airport: str, year: int = 2024) -> DisruptionScoreResponse:
        # Current year stats
        current = self.db.execute(text("""
            SELECT 
                COUNT(*) AS total,
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(cancelled) AS cancelled
            FROM flights
            WHERE origin = :airport
              AND strftime('%Y', flight_date) = :year
        """), {"airport": airport, "year": str(year)}).fetchone()

        # Previous year stats (if available)
        prev_year = year - 1
        previous = self.db.execute(text("""
            SELECT 
                COUNT(*) AS total,
                COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(cancelled) AS cancelled
            FROM flights
            WHERE origin = :airport
              AND strftime('%Y', flight_date) = :year
        """), {"airport": airport, "year": str(prev_year)}).fetchone()

        if not current or current.total == 0:
            raise ValueError("No data for this airport/year")

        total = current.total
        delay_freq = float(current.delayed or 0) / total
        cancel_freq = float(current.cancelled or 0) / total
        avg_delay = float(current.avg_delay or 0)

        # If previous year exists, compare; otherwise, just scale from this year
        if previous and previous.total and previous.total > 0:
            prev_delay_freq = float(previous.delayed or 0) / previous.total
            prev_cancel_freq = float(previous.cancelled or 0) / previous.total
            delay_change = delay_freq - prev_delay_freq
            cancel_change = cancel_freq - prev_cancel_freq
        else:
            delay_change = 0.0
            cancel_change = 0.0

        # Score 0–100 using this year + change vs last year
        base_score = (delay_freq * 60) + (cancel_freq * 200) + (avg_delay / 60 * 40)
        change_penalty = (max(delay_change, 0) * 40) + (max(cancel_change, 0) * 80)
        disruption_score = min(round(base_score + change_penalty, 1), 100)

        if disruption_score < 30:
            level = "Low"
        elif disruption_score < 70:
            level = "Medium"
        else:
            level = "High"

        # Simple cause heuristic
        top_delay_cause = "Cancellations" if cancel_freq > 0.02 else "Delays"

        return DisruptionScoreResponse(
            airport=airport,
            disruption_score=disruption_score,
            delay_frequency=round(delay_freq, 3),
            cancel_frequency=round(cancel_freq, 3),
            top_delay_cause=top_delay_cause,
            disruption_level=level,
            period_days=365,
            vs_baseline=f"{delay_change:+.1%} vs {prev_year}"
        )

    def get_year_over_year(self, airport: str) -> YearOverYearResponse:
        res_2023 = self.db.execute(text("""
            SELECT COUNT(*) AS total, COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                   SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                   SUM(cancelled) AS cancelled
            FROM flights WHERE origin = :airport AND strftime('%Y', flight_date) = '2023'
        """), {"airport": airport}).fetchone()

        res_2024 = self.db.execute(text("""
            SELECT COUNT(*) AS total, COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                   SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                   SUM(cancelled) AS cancelled
            FROM flights WHERE origin = :airport AND strftime('%Y', flight_date) = '2024'
        """), {"airport": airport}).fetchone()

        def build_year_dict(row):
            if not row or row.total == 0:
                return {"total_flights": 0, "avg_arrival_delay": 0.0, "delay_rate": 0.0, "cancel_rate": 0.0}
            total = row.total
            return {
                "total_flights": int(total),
                "avg_arrival_delay": round(float(row.avg_delay or 0), 1),
                "delay_rate": round(float(row.delayed or 0) / total, 3),
                "cancel_rate": round(float(row.cancelled or 0) / total, 3),
            }

        year_2023, year_2024 = build_year_dict(res_2023), build_year_dict(res_2024)
        improvement_pct = round(((year_2023["delay_rate"] - year_2024["delay_rate"]) /
                                 year_2023["delay_rate"] * 100.0) if year_2023["delay_rate"] > 0 else 0.0, 1)

        return YearOverYearResponse(airport=airport, year_2023=year_2023, year_2024=year_2024,
                                    improvement_pct=improvement_pct)

    def compare_airports(self, airports: str, year: int = 2024) -> AirportComparisonResponse:
        airport_list = list(set([a.strip().upper() for a in airports.split(",") if a.strip()]))

        if len(airport_list) == 0:
            raise ValueError("No airports provided")

        # single airport (including LAX,LAX → just LAX)
        if len(airport_list) == 1:
            airport = airport_list[0]
            result = self.db.execute(
                text("""
                    SELECT origin AS airport, COUNT(*) AS total, 
                           COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                           SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed, 
                           SUM(cancelled) AS cancelled
                    FROM flights 
                    WHERE origin = :airport AND strftime('%Y', flight_date) = :year
                """), {"airport": airport, "year": str(year)}
            ).fetchone()

            total = result.total or 0
            if total == 0:
                raise ValueError(f"No data for {airport}")

            item = AirportComparisonItem(
                airport=airport,
                total_flights=int(total),
                avg_arrival_delay=round(float(result.avg_delay or 0), 1),
                delay_rate=round(float(result.delayed or 0) / total, 3),
                cancel_rate=round(float(result.cancelled or 0) / total, 3),
            )
            return AirportComparisonResponse(year=year, airports=[item])

        # Multiple UNIQUE airports
        placeholders = ",".join([f":a{i}" for i in range(len(airport_list))])
        params = {f"a{i}": code for i, code in enumerate(airport_list)}
        params["year"] = str(year)

        result = self.db.execute(
            text(f"""
                SELECT origin AS airport, COUNT(*) AS total, COALESCE(AVG(arr_delay_minutes), 0) AS avg_delay,
                       SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed, SUM(cancelled) AS cancelled
                FROM flights WHERE origin IN ({placeholders}) AND strftime('%Y', flight_date) = :year
                GROUP BY origin
            """), params
        ).fetchall()

        items = []
        for row in result:
            total = row.total or 0
            if total == 0: continue
            items.append(AirportComparisonItem(
                airport=row.airport,
                total_flights=int(total),
                avg_arrival_delay=round(float(row.avg_delay or 0), 1),
                delay_rate=round(float(row.delayed or 0) / total, 3),
                cancel_rate=round(float(row.cancelled or 0) / total, 3),
            ))

        if not items:
            raise ValueError("No data for given airports/year")

        return AirportComparisonResponse(year=year, airports=items)

    def daily_pattern(self, airport: str, year: int = 2024) -> DailyPatternResponse:
        result = self.db.execute(
            text("""
                SELECT CAST(strftime('%H', dep_time) AS INTEGER) AS hour, COUNT(*) AS total,
                       COALESCE(AVG(dep_delay_minutes), 0) AS avg_dep_delay,
                       SUM(CASE WHEN dep_del_15 = 1 THEN 1 ELSE 0 END) AS delayed
                FROM flights WHERE origin = :airport AND dep_time IS NOT NULL 
                              AND strftime('%Y', flight_date) = :year
                GROUP BY hour ORDER BY hour
            """), {"airport": airport, "year": str(year)}
        ).fetchall()

        hours = []
        for row in result:
            total = row.total or 0
            if total == 0 or row.hour is None: continue
            hours.append(HourlyPatternItem(
                hour=int(row.hour),
                avg_dep_delay=round(float(row.avg_dep_delay or 0), 1),
                delay_rate=round(float(row.delayed or 0) / total, 3),
            ))

        if not hours:
            raise ValueError("No pattern data")

        return DailyPatternResponse(airport=airport.upper(), year=year, hours=hours)

    def weekly_pattern(self, airport: str, year: int = 2024) -> WeeklyPatternResponse:
        result = self.db.execute(
            text("""
                SELECT CAST(strftime('%w', flight_date) AS INTEGER) AS dow, COUNT(*) AS total,
                       COALESCE(AVG(arr_delay_minutes), 0) AS avg_arr_delay,
                       SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed,
                       SUM(cancelled) AS cancelled
                FROM flights WHERE origin = :airport AND strftime('%Y', flight_date) = :year
                GROUP BY dow ORDER BY dow
            """), {"airport": airport, "year": str(year)}
        ).fetchall()

        days = []
        for row in result:
            total = row.total or 0
            if total == 0 or row.dow is None: continue
            label = DOW_MAP.get(int(row.dow), str(row.dow))
            days.append(WeeklyPatternItem(
                dow=label,
                avg_arr_delay=round(float(row.avg_arr_delay or 0), 1),
                delay_rate=round(float(row.delayed or 0) / total, 3),
                cancel_rate=round(float(row.cancelled or 0) / total, 3),
            ))

        if not days:
            raise ValueError("No weekly data")

        return WeeklyPatternResponse(airport=airport.upper(), year=year, days=days)

    def punctuality_leaderboard(self, year: int = 2024, limit: int = 10,
                                min_flights: int = 1000) -> PunctualityLeaderboardResponse:
        rows = self.db.execute(
            text("""
                SELECT origin AS airport, COUNT(*) AS total_flights,
                       SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END) AS delayed_flights
                FROM flights WHERE strftime('%Y', flight_date) = :year
                GROUP BY origin
            """), {"year": str(year)}
        ).mappings().all()

        items = []
        for row in rows:
            total = int(row["total_flights"] or 0)
            if total < min_flights: continue
            delayed = int(row["delayed_flights"] or 0)
            delay_rate, otp = delayed / total, 1.0 - delayed / total
            items.append(LeaderboardItem(
                airport=row["airport"],
                otp_pct=round(otp, 3),
                delay_rate=round(delay_rate, 3),
                total_flights=total,
            ))

        if not items:
            raise ValueError("No airports meet criteria")

        items_sorted = sorted(items, key=lambda x: x.otp_pct, reverse=True)
        return PunctualityLeaderboardResponse(
            year=year,
            top_airports=items_sorted[:limit],
            bottom_airports=list(reversed(items_sorted))[:limit],
        )

    def best_time_to_fly(self, airport: str, year: int = 2024, top_n: int = 3) -> BestTimeResponse:
        result = self.db.execute(
            text("""
                SELECT CAST(strftime('%H', dep_time) AS INTEGER) AS hour, COUNT(*) AS total_flights,
                       COALESCE(AVG(dep_delay_minutes), 0) AS avg_dep_delay,
                       SUM(CASE WHEN dep_del_15 = 1 THEN 1 ELSE 0 END)*1.0 / COUNT(*) AS delay_rate
                FROM flights WHERE origin = :airport AND dep_time IS NOT NULL 
                              AND strftime('%Y', flight_date) = :year
                GROUP BY hour HAVING total_flights >= 50 ORDER BY hour
            """), {"airport": airport, "year": str(year)}
        ).fetchall()

        if not result:
            raise ValueError("No sufficient data")

        hours = [BestTimeItem(
            hour=int(row.hour),
            avg_dep_delay=round(float(row.avg_dep_delay), 1),
            delay_rate=round(float(row.delay_rate), 3),
            total_flights=int(row.total_flights),
        ) for row in result if row.total_flights >= 50]

        if len(hours) < 2:
            raise ValueError("Insufficient hourly data")

        sorted_hours = sorted(hours, key=lambda x: x.delay_rate)
        best, worst = sorted_hours[:top_n], sorted_hours[-top_n:]
        improvement = ((worst[0].delay_rate - best[0].delay_rate) / worst[0].delay_rate * 100) if worst[
                                                                                                      0].delay_rate > 0 else 0

        return BestTimeResponse(
            airport=airport.upper(),
            year=year,
            best_hours=best,
            worst_hours=worst,
            insight=f"Flying at {best[0].hour}:00 gives {best[0].delay_rate:.1%} delay risk vs {worst[0].delay_rate:.1%} at {worst[0].hour}:00 ({improvement:.0f}% better)."
        )

    def route_risk_score(self, origin: str, destinations: str, year: int = 2024) -> RouteRiskResponse:
        dest_list = [d.strip().upper() for d in destinations.split(",") if d.strip()]

        dest_list = list(set(dest_list))

        invalid_destinations = [dest for dest in dest_list if dest == origin]
        if invalid_destinations:
            raise ValueError(f"Cannot fly from {origin} to itself ({','.join(invalid_destinations)})")

        if len(dest_list) < 1:
            raise ValueError("Provide at least 1 destination")
        if len(dest_list) > 10:
            raise ValueError("Maximum 10 destinations")

        # Single destination case
        if len(dest_list) == 1:
            dest = dest_list[0]
            result = self.db.execute(
                text("""
                    SELECT dest AS dest, COUNT(*) AS total_flights, 
                           COALESCE(AVG(arr_delay_minutes), 0) AS avg_arr_delay,
                           SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END)*1.0 / COUNT(*) AS delay_rate,
                           SUM(cancelled)*1.0 / COUNT(*) AS cancel_rate
                    FROM flights 
                    WHERE origin = :origin AND dest = :dest 
                          AND strftime('%Y', flight_date) = :year
                    GROUP BY dest HAVING total_flights >= 10
                """), {"origin": origin.upper(), "dest": dest, "year": str(year)}
            ).fetchone()

            if not result:
                raise ValueError("No route data found")

            # Single route risk score
            risk_score = round(
                float(result.delay_rate or 0) * 40 +
                min(float(result.avg_arr_delay or 0) / 30, 1) * 30 +
                float(result.cancel_rate or 0) * 3000, 1
            )

            route_item = RouteRiskItem(
                dest=result.dest,
                risk_score=risk_score,
                delay_rate=round(float(result.delay_rate or 0), 3),
                avg_arr_delay=round(float(result.avg_arr_delay or 0), 1),
                cancel_rate=round(float(result.cancel_rate or 0), 3),
                total_flights=int(result.total_flights),
            )

            return RouteRiskResponse(
                origin=origin.upper(),
                year=year,
                safest_route=f"{origin}→{route_item.dest}",
                riskiest_route=f"{origin}→{route_item.dest}",
                routes=[route_item]
            )

        # Multiple destinations - original dynamic SQL
        placeholders = ",".join([f":d{i}" for i in range(len(dest_list))])
        params = {f"d{i}": dest for i, dest in enumerate(dest_list)}
        params.update({"origin": origin.upper(), "year": str(year)})

        result = self.db.execute(
            text(f"""
                SELECT dest AS dest, COUNT(*) AS total_flights, COALESCE(AVG(arr_delay_minutes), 0) AS avg_arr_delay,
                       SUM(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END)*1.0 / COUNT(*) AS delay_rate,
                       SUM(cancelled)*1.0 / COUNT(*) AS cancel_rate
                FROM flights WHERE origin = :origin AND dest IN ({placeholders}) 
                              AND strftime('%Y', flight_date) = :year
                GROUP BY dest HAVING total_flights >= 10
            """), params
        ).fetchall()

        if not result:
            raise ValueError("No route data found")

        routes = []
        for row in result:
            risk_score = round(
                float(row.delay_rate or 0) * 40 +
                min(float(row.avg_arr_delay or 0) / 30, 1) * 30 +
                float(row.cancel_rate or 0) * 3000, 1
            )
            routes.append(RouteRiskItem(
                dest=row.dest,
                risk_score=risk_score,
                delay_rate=round(float(row.delay_rate or 0), 3),
                avg_arr_delay=round(float(row.avg_arr_delay or 0), 1),
                cancel_rate=round(float(row.cancel_rate or 0), 3),
                total_flights=int(row.total_flights),
            ))

        routes.sort(key=lambda x: x.risk_score)
        return RouteRiskResponse(
            origin=origin.upper(),
            year=year,
            safest_route=f"{origin}→{routes[0].dest}",
            riskiest_route=f"{origin}→{routes[-1].dest}",
            routes=routes,
        )

    def system_overview(self) -> Dict[str, Any]:
        result = self.db.execute(text("""
            SELECT COUNT(*) as total_flights, ROUND(AVG(COALESCE(arr_delay_minutes, 0)), 1) as avg_delay,
                   ROUND(AVG(CASE WHEN arr_del_15 = 1 THEN 1.0 ELSE 0 END), 3) as delay_rate,
                   SUM(cancelled) as total_cancelled FROM flights
        """)).fetchone()
        return {
            "total_flights": int(result.total_flights),
            "avg_delay_minutes": float(result.avg_delay),
            "national_delay_rate": float(result.delay_rate),
            "total_cancellations": int(result.total_cancelled)
        }

    def carrier_performance(self, year: int = 2024) -> List[Dict[str, Any]]:
        result = self.db.execute(
            text("""
                SELECT DISTINCT reporting_airline as reporting_airline, COUNT(*) as total_flights,
                       ROUND((1.0 - AVG(CASE WHEN arr_del_15 = 1 THEN 1 ELSE 0 END)), 3) as otp_pct
                FROM flights WHERE strftime('%Y', flight_date) = :year
                GROUP BY reporting_airline HAVING total_flights >= 5000
                ORDER BY otp_pct DESC LIMIT 10
            """), {"year": str(year)}
        ).fetchall()

        return [{
            "carrier": r.reporting_airline,
            "otp_pct": float(r.otp_pct),
            "total_flights": int(r.total_flights),
            "delay_rate": round(1 - float(r.otp_pct), 3)
        } for r in result]

    def monthly_trends(self, year: int = 2024) -> List[Dict[str, Any]]:
        result = self.db.execute(
            text("""
                SELECT strftime('%m-%Y', flight_date) as period, strftime('%m', flight_date) as month_num,
                       COUNT(*) as flights, ROUND(AVG(COALESCE(arr_delay_minutes, 0)), 1) as avg_delay,
                       ROUND(AVG(CASE WHEN arr_del_15 = 1 THEN 1.0 ELSE 0 END), 3) as delay_rate,
                       ROUND(AVG(cancelled*1.0), 3) as cancel_rate
                FROM flights WHERE strftime('%Y', flight_date) = :year
                GROUP BY 1 ORDER BY month_num
            """), {"year": str(year)}
        ).fetchall()

        return [{"period": r.period, "flights": int(r.flights), "avg_delay": float(r.avg_delay),
                 "delay_rate": float(r.delay_rate), "cancel_rate": float(r.cancel_rate)} for r in result]
