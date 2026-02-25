import streamlit as st
from components.api import fetch
from components.metrics import metric_card
from config import DARK_THEME
import plotly as px
import pandas as pd

st.set_page_config(page_title="Flight Analytics", page_icon="✈️", layout="wide")

# Apply theme
st.markdown(f"""
<style>
:root {{
    --primary: {DARK_THEME["primary"]};
    --accent: {DARK_THEME["accent"]};
    --bg: {DARK_THEME["bg"]};
    --card: {DARK_THEME["card"]};
}}
.main .block-container {{ background-color: {DARK_THEME["bg"]}; }}
body {{ color: {DARK_THEME["text"]}; }}
h1,h2,h3 {{ color: {DARK_THEME["accent"]}!important; }}
</style>
""", unsafe_allow_html=True)

# Header
st.title("Flight Disruption Analytics")
st.markdown("**Professional dashboard for aviation performance insights**")

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs(["Leaderboard", "Airport Analysis", "Time Patterns", "Route Planning"])

with tab1:
    st.markdown("## Punctuality Leaderboard")
    year = st.selectbox("Year", [2023, 2024], index=1, label_visibility="collapsed")

    data = fetch("leaderboard/punctuality", {"year": year})
    if data:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Top 10 Airports")
            pd.DataFrame(data["top_airports"]).style.background_gradient(cmap='Greens')
            st.dataframe(pd.DataFrame(data["top_airports"]), use_container_width=True)
        with col2:
            st.markdown("### Bottom 10 Airports")
            st.dataframe(pd.DataFrame(data["bottom_airports"]), use_container_width=True)

with tab2:
    st.markdown("## Airport Delays")
    airport = st.text_input("Airport", "JFK").upper()
    if airport:
        data = fetch(f"airport-delays/{airport}")
        if data:
            col1, col2, col3, col4 = st.columns(4)
            metric_card("Total Flights", f"{data['total_flights']:,}", col1)
            metric_card("Avg Delay", f"{data['avg_arrival_delay']:.1f}min", col2)
            metric_card("Delay Rate", f"{data['delay_rate'] * 100:.1f}%", col3)
            metric_card("Cancel Rate", f"{data['cancel_rate'] * 100:.1f}%", col4)

with tab3:
    pattern_col1, pattern_col2 = st.columns(2)
    with pattern_col1:
        st.markdown("### Daily Pattern")
        airport = st.text_input("Airport", "JFK").upper()
        if airport: st.dataframe(fetch(f"daily-pattern/{airport}"))
    with pattern_col2:
        st.markdown("### Weekly Pattern")
        st.dataframe(fetch("weekly-pattern/JFK"))

with tab4:
    st.markdown("## Route Analysis")
    # Route risk + best time logic here
    st.info("Coming soon...")


# SYSTEM-WIDE METRICS (Add above Leaderboard section in app.py)

# 1. INDUSTRY OVERVIEW METRICS
col1, col2, col3, col4 = st.columns(4)
data_total = fetch("airport-delays/JFK")  # Use any airport to get structure, modify for totals
if data_total:
    # These need NEW API endpoints but show what belongs here:
    metric_card("Total Flights (US)", "2.1M", col1)
    metric_card("Industry Avg Delay", "14.2 min", col2)
    metric_card("National Delay Rate", "19.8%", col3)
    metric_card("Total Cancellations", "12.4K", col4)

# 2. TOP CARRIER PERFORMANCE (Network-wide)
st.markdown("### Carrier Performance (All Airports)")
carrier_data = fetch("carrier-performance")  # NEW ENDPOINT NEEDED
if carrier_data:
    df_carriers = pd.DataFrame(carrier_data)
    st.dataframe(df_carriers.head(8), use_container_width=True)

# 3. MONTHLY TRENDS (System-wide)
st.markdown("### Monthly Disruption Trends")
monthly_data = fetch("monthly-trends")  # NEW ENDPOINT NEEDED
if monthly_data:
    df_monthly = pd.DataFrame(monthly_data)
    fig = px.line(df_monthly, x="month", y=["delay_rate", "cancel_rate"])
    st.plotly_chart(fig, use_container_width=True)
