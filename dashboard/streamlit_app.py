import streamlit as st
from components import api
from components import metrics
import plotly.express as px
import pandas as pd
from components.metrics import DARK_THEME

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
    year = st.selectbox("Year", [2023, 2024], index=1, label_visibility="collapsed", key="main_year")

    data = api.fetch("leaderboard/punctuality", {"year": year})
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
    airport = st.text_input("Airport", "JFK", key="airport_analysis").upper()

    if airport:
        data = api.fetch(f"airport-delays/{airport}")
        if data:
            col1, col2, col3, col4 = st.columns(4)
            metrics.metric_card("Total Flights", f"{data['total_flights']:,}", col1)
            metrics.metric_card("Avg Delay", f"{data['avg_arrival_delay']:.1f}min", col2)
            metrics.metric_card("Delay Rate", f"{data['delay_rate'] * 100:.1f}%", col3)
            metrics.metric_card("Cancel Rate", f"{data['cancel_rate'] * 100:.1f}%", col4)

with tab3:
    pattern_col1, pattern_col2 = st.columns(2)
    with pattern_col1:
        st.markdown("### Daily Pattern")
        airport_daily = st.text_input("Airport", "JFK", key="daily_pattern_airport").upper()

        if airport:
            st.dataframe(api.fetch(f"daily-pattern/{airport}"))

    with pattern_col2:
        st.markdown("### Weekly Pattern")
        airport_weekly = st.text_input("Airport", "JFK", key="weekly_pattern_airport").upper()

        if airport_weekly:
            st.dataframe(api.fetch(f"weekly-pattern/{airport_weekly}"))

with tab4:
    st.markdown("## Route Analysis & Best Times")

    # Row 1: Best Time to Fly (Left) + Route Risk (Right)
    col1, col2 = st.columns(2)

    # LEFT: Best Time to Fly
    with col1:
        st.markdown("### Best Time to Fly")
        year_best = st.selectbox("Year", [2023, 2024], index=1, key="best_time_year")
        airport_best = st.text_input("Airport", "JFK", key="best_time_airport").upper()

        if airport:
            best_data = api.fetch(f"best-time/{airport}", {"year": year})
            if best_data:
                st.success(best_data["insight"])

                # Best vs Worst hours table
                col_best1, col_best2 = st.columns(2)
                best_df = pd.DataFrame(best_data["best_hours"])
                worst_df = pd.DataFrame(best_data["worst_hours"])

                with col_best1:
                    st.metric("Best Hour", f"{best_df.iloc[0]['hour']}:00")
                    st.metric("Delay Risk", f"{best_df.iloc[0]['delay_rate'] * 100:.1f}%")
                with col_best2:
                    st.metric("Worst Hour", f"{worst_df.iloc[0]['hour']}:00")
                    st.metric("Delay Risk", f"{worst_df.iloc[0]['delay_rate'] * 100:.1f}%")

    # RIGHT: Route Risk Analysis
    with col2:
        st.markdown("### Route Risk")
        year_route = st.selectbox("Year", [2023, 2024], index=1, key="route_risk_year")
        origin = st.text_input("Origin", "JFK", key="route_origin").upper()
        destinations = st.text_input("Destinations", "LAX,ORD,ATL", key="route_destinations")

        if origin and destinations:
            route_data = api.fetch("route-risk", {"origin": origin, "destinations": destinations, "year": year})
            if route_data:
                st.success(f"**Safest:** {route_data['safest_route']} | **Riskiest:** {route_data['riskiest_route']}")

                # Top 3 safest routes
                df_routes = pd.DataFrame(route_data["routes"][:3])
                st.dataframe(df_routes[['dest', 'risk_score', 'delay_rate']], use_container_width=True)

    # Row 2: Year-over-Year Airport Comparison
    st.markdown("---")
    st.markdown("### Compare Airport Performance")
    airports_input = st.text_input("Airports", "JFK,LAX,ORD", key="compare_airports")
    compare_year = st.selectbox("Year", [2023, 2024], index=1, key="compare_year")

    if airports_input:
        compare_data = api.fetch("compare-airports", {
            "airports": airports_input,
            "year": compare_year
        })
        if compare_data:
            df_compare = pd.DataFrame(compare_data["airports"])
            st.dataframe(
                df_compare.style.background_gradient(cmap='RdYlGn_r', subset=['delay_rate']),
                use_container_width=True
            )

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("## System-Wide Analytics")
with col2:
    year = st.selectbox("Year:", [2023, 2024], index=1, label_visibility="collapsed")


col1, col2, col3, col4 = st.columns(4)
system_data = api.fetch("system-overview")
if system_data:
    metrics.metric_card("Total Flights (US)", f"{system_data['total_flights']:,}", col1)
    metrics.metric_card("Industry Avg Delay", f"{system_data['avg_delay_minutes']:.1f} min", col2)
    metrics.metric_card("National Delay Rate", f"{system_data['national_delay_rate'] * 100:.1f}%", col3)
    metrics.metric_card("Total Cancellations", f"{system_data['total_cancellations']:,}", col4)
else:
    st.warning("System overview loading...")

# 2. TOP CARRIER PERFORMANCE (Network-wide) - FIXED
st.markdown("### Carrier Performance Ranking")
carrier_data = api.fetch("carrier-performance", {"year": year})  # Pass year param
if carrier_data:
    df_carriers = pd.DataFrame(carrier_data)
    st.dataframe(
        df_carriers.head(10).style.background_gradient(cmap='Greens', subset=['otp_pct']),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Carrier data loading...")


st.markdown("### Monthly Disruption Trends")
monthly_data = api.fetch("monthly-trends", {"year": year})
if monthly_data:
    df_monthly = pd.DataFrame(monthly_data)

    fig = px.line(df_monthly, x="period", y=["delay_rate", "cancel_rate"],
                  title=f"Disruption Trends {year}",
                  color_discrete_sequence=["#68a368", "#a8d0a8"],
                  labels={'value': 'Rate', 'period': 'Month'})

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="#e8f0e8",
        title_font_color="#68a368"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Monthly trends loading...")
