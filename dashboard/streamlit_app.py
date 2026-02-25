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
        if airport:
            st.dataframe(fetch(f"daily-pattern/{airport}"))
    with pattern_col2:
        st.markdown("### Weekly Pattern")
        st.dataframe(fetch("weekly-pattern/JFK"))

with tab4:
    st.markdown("## Route Analysis & Best Times")

    # Row 1: Best Time to Fly (Left) + Route Risk (Right)
    col1, col2 = st.columns(2)

    # LEFT: Best Time to Fly
    with col1:
        st.markdown("### Best Time to Fly")
        year = st.selectbox("Year", [2023, 2024], index=1, key="best_time_year")
        airport = st.text_input("Airport", "JFK", key="best_time_airport").upper().strip()

        if airport:
            best_data = fetch(f"best-time/{airport}", {"year": year})
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
        st.markdown("### Route Risk Scores")
        year = st.selectbox("Year", [2023, 2024], index=1, key="route_year")
        origin = st.text_input("Origin", "JFK", key="route_origin").upper().strip()
        destinations = st.text_input("Destinations", "LAX,ORD,ATL,DEN",
                                     help="Comma-separated e.g. LAX,ORD,ATL").upper().strip()

        if origin and destinations:
            route_data = fetch("route-risk", {"origin": origin, "destinations": destinations, "year": year})
            if route_data:
                st.success(f"**Safest:** {route_data['safest_route']} | **Riskiest:** {route_data['riskiest_route']}")

                # Top 3 safest routes
                df_routes = pd.DataFrame(route_data["routes"].head(3))
                st.dataframe(df_routes[['dest', 'risk_score', 'delay_rate']], use_container_width=True)

    # Row 2: Year-over-Year Airport Comparison
    st.markdown("---")
    st.markdown("### Compare Airport Performance")
    airports_input = st.text_input("Airports", "JFK,LAX,ORD,ATL",
                                   help="Comma-separated airport codes").upper().strip()
    compare_year = st.selectbox("Year", [2023, 2024], index=1, key="compare_year")

    if airports_input:
        compare_data = fetch("compare-airports", {
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
system_data = fetch("system-overview")
if system_data:
    metric_card("Total Flights (US)", f"{system_data['total_flights']:,}", col1)
    metric_card("Industry Avg Delay", f"{system_data['avg_delay_minutes']:.1f} min", col2)
    metric_card("National Delay Rate", f"{system_data['national_delay_rate'] * 100:.1f}%", col3)
    metric_card("Total Cancellations", f"{system_data['total_cancellations']:,}", col4)
else:
    st.warning("System overview loading...")

# 2. TOP CARRIER PERFORMANCE (Network-wide) - FIXED
st.markdown("### Carrier Performance Ranking")
carrier_data = fetch("carrier-performance", {"year": year})  # Pass year param
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
monthly_data = fetch("monthly-trends", {"year": year})
if monthly_data:
    df_monthly = pd.DataFrame(monthly_data)

    # Fixed column name (period instead of month)
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
