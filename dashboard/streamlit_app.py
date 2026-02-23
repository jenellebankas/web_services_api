# streamlit_app.py
import streamlit as st
import requests

API_BASE = st.secrets.get("API_BASE_URL", "http://localhost:8000")

st.title("Aviation Analytics Dashboard")

airport = st.selectbox("Airport", ["LAX", "JFK", "ORD", "ATL"])

if st.button("Analyze"):
    with st.spinner("Fetching data..."):
        try:
            delays = requests.get(f"{API_BASE}/api/v1/analytics/airport-delays/{airport}").json()
            score = requests.get(f"{API_BASE}/api/v1/analytics/disruption-score/{airport}").json()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Avg Delay (min)", delays["avg_arrival_delay"])
            col2.metric("Delay Rate", f"{delays['delay_rate']:.1%}")
            col3.metric("Cancel Rate", f"{delays['cancel_rate']:.1%}")
            col4.metric("Disruption Score", f"{score['disruption_score']:.1f}")

            st.bar_chart({"2023": [score["year_2023"]["delay_rate"]], "2024": [score["year_2024"]["delay_rate"]]})

        except Exception as e:
            st.error(f"API not responding - check Render deployment: {str(e)}")
