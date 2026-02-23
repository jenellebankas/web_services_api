# dashboard/streamlit_app.py
import streamlit as st
import pandas as pd
import requests


st.set_page_config(page_title="Aviation Analytics", layout="wide")

API_BASE = st.secrets.get("API_BASE_URL", "https://web-services-api.onrender.com/")

st.title("Aviation Disruption Dashboard")
st.markdown("**FastAPI Backend** → " + API_BASE)

# Airport selector
airport = st.selectbox("Select Airport", ["LAX", "JFK", "ORD", "ATL", "DFW"], index=0)

if st.button("Analyse Airport", type="primary"):
    with st.spinner("Fetching analytics..."):
        try:
            # Call your existing endpoints
            delays = requests.get(f"{API_BASE}/api/v1/analytics/airport-delays/{airport}", timeout=10).json()
            score = requests.get(f"{API_BASE}/api/v1/analytics/disruption-score/{airport}", timeout=10).json()
            year = requests.get(f"{API_BASE}/api/v1/analytics/year-over-year/{airport}", timeout=10).json()

            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Flights", delays["total_flights"], delta=None)
            col2.metric("Avg Delay (min)", f"{delays['avg_arrival_delay']:.1f}")
            col3.metric("Delay Rate", f"{delays['delay_rate']:.1%}")
            col4.metric("Cancel Rate", f"{delays['cancel_rate']:.1%}")

            # Charts
            st.subheader(f"{airport} Performance")

            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Disruption Score", f"{score['disruption_score']:.2f}")
                st.info(f"Worst day: {delays['worst_day']}")

            with col_b:
                # YOY comparison (adjust fields to match your schema)
                st.bar_chart({
                    "2023 Delay Rate": [year.get("year_2023", {}).get("delay_rate", 0)],
                    "2024 Delay Rate": [year.get("year_2024", {}).get("delay_rate", 0)]
                })

        except requests.exceptions.RequestException:
            st.error("API not responding. Check Render deployment.")
        except KeyError as e:
            st.error(f"Unexpected API response format. Missing: {e}")
