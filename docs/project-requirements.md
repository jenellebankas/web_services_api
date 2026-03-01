# Aviation Disruption Analytics API - Project Requirements

## Project Overview

**Purpose**: REST API analysing US domestic flight disruptions (2023-2024) for operational dashboards and research tools.

**Problem**: Airlines/airports need clear, actionable insights into delay patterns, cancellation causes, and year-over-year performance trends.

**Business Value**: Enables route optimisation, capacity planning, and disruption forecasting.

**Target Users**: Airport operations, airline analysts, aviation researchers.

## Data Source

**Datasets**: US Bureau of Transportation Statistics flight data
- `flights_2023.parquet` (~6847899 rows)
- `flights_2024.parquet` (~7079061 rows)

**Key Fields**:

- Core: flight_date, airline, origin, dest, times
- Disruption: dep/arr delays, cancelled, diverted  
- Causes: carrier_delay, weather_delay, nas_delay
