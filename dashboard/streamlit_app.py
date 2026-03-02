import pandas as pd
import plotly.express as px
import streamlit as st

from components import api
from components import metrics
from components.metrics import DARK_THEME


# Add safe API wrapper
def safe_api_call(endpoint: str, params: dict = None, spinner_text: str = "Loading..."):
    """Safe API call with proper error handling"""
    try:
        with st.spinner(spinner_text):
            return api.fetch(endpoint, params or {})
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        st.info("Try a different airport/year or check server status")
        return None


st.set_page_config(page_title="Flight Analytics", page_icon="✈️", layout="wide")

# Apply theme (unchanged)
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

no_sidebar_style = """
    <style>
        div[data-testid="stSidebarNav"] {display: none;}
    </style>
"""
st.markdown(no_sidebar_style, unsafe_allow_html=True)

# Sidebar (unchanged)
with st.sidebar:
    st.header("Airport analytics")
    selected_view = st.radio(
        "Select analysis",
        [
            "System Overview",
            "Single Airport Overview",
            "Disruption Score",
            "Route Risk",
            "Best Time to Fly"
        ],
        index=0,
        key="nav_view",
    )

st.title("Flight Disruption Analytics")

# SYSTEM OVERVIEW - Safe version
if selected_view == "System Overview":
    tab1, tab2, tab3 = st.tabs(["Leaderboard", "Carrier & Airport Performance", "Time Patterns"])

    with tab1:
        st.markdown("## System-Wide Analytics")
        system_data = safe_api_call("system-overview", spinner_text="Loading system stats...")

        if system_data:
            col1, col2, col3, col4 = st.columns(4)
            metrics.metric_card("Total Flights (US)", f"{system_data.get('total_flights', 0):,}", col1)
            metrics.metric_card("Industry Avg Delay", f"{system_data.get('avg_delay_minutes', 0):.1f} min", col2)
            metrics.metric_card("National Delay Rate", f"{system_data.get('national_delay_rate', 0) * 100:.1f}%", col3)
            metrics.metric_card("Total Cancellations", f"{system_data.get('total_cancellations', 0):,}", col4)

        st.markdown("## Punctuality Leaderboard")
        year = st.selectbox("Year", [2023, 2024], index=1, label_visibility="collapsed", key="main_year")
        leaderboard_data = safe_api_call("leaderboard/punctuality", {"year": year})

        if leaderboard_data and leaderboard_data.get("top_airports"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### Top 10 Airports")
                st.dataframe(pd.DataFrame(leaderboard_data["top_airports"]), use_container_width=True)
            with col2:
                st.markdown("### Bottom 10 Airports")
                st.dataframe(pd.DataFrame(leaderboard_data["bottom_airports"]), use_container_width=True)
        elif not leaderboard_data:
            st.info("No leaderboard data available")

    with tab2:
        st.markdown("### Compare Airport Performance")
        airports_input = st.text_input("Airports (comma-separated)", "JFK,LAX,ORD", key="compare_airports")
        compare_year = st.selectbox("Year", [2023, 2024], index=1, key="compare_year")

        if airports_input.strip():
            compare_data = safe_api_call("compare-airports", {
                "airports": airports_input.strip(),
                "year": compare_year
            }, "Comparing airports...")
            if compare_data and compare_data.get("airports"):
                df_compare = pd.DataFrame(compare_data["airports"])
                st.dataframe(df_compare, use_container_width=True)

        st.markdown("### Carrier Performance Ranking")
        carrier_data = safe_api_call("carrier-performance", {"year": compare_year})
        if carrier_data:
            df_carriers = pd.DataFrame(carrier_data)
            fig_carrier = px.bar(df_carriers.head(10), x="carrier", y="otp_pct",
                                 title="Top Carriers by On-Time Performance",
                                 color_discrete_sequence=["#4caf50"])
            st.plotly_chart(fig_carrier, use_container_width=True)

    with tab3:
        st.markdown("### Monthly Disruption Trends")
        trends_year = st.selectbox("Year", [2023, 2024], index=1, label_visibility="collapsed", key="tab3_year")
        monthly_data = safe_api_call("monthly-trends", {"year": trends_year})
        if monthly_data:
            df_monthly = pd.DataFrame(monthly_data)
            fig = px.line(df_monthly, x="period", y=["delay_rate", "cancel_rate"],
                          title=f"Disruption Trends {trends_year}",
                          color_discrete_sequence=["#68a368", "#a8d0a8"])
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

# SINGLE AIRPORT OVERVIEW - Safe version
if selected_view == "Single Airport Overview":
    airport = st.text_input("Airport", "JFK", key="overview_airport").upper().strip()
    analysis_year = st.selectbox("Year", [2023, 2024], index=1, key="overview_year")

    if len(airport) == 3 and airport.isalpha():
        # Airport metrics
        airport_data = safe_api_call(f"airport-delays/{airport}", spinner_text=f"Loading {airport} stats...")
        if airport_data:
            col1, col2, col3, col4 = st.columns(4)
            metrics.metric_card("Total Flights", f"{airport_data.get('total_flights', 0):,}", col1)
            metrics.metric_card("Avg Delay", f"{airport_data.get('avg_arrival_delay', 0):.1f}min", col2)
            metrics.metric_card("Delay Rate", f"{airport_data.get('delay_rate', 0) * 100:.1f}%", col3)
            metrics.metric_card("Cancel Rate", f"{airport_data.get('cancel_rate', 0) * 100:.1f}%", col4)

        # Daily patterns
        st.markdown("### Daily Delay Patterns")
        daily_data = safe_api_call("daily-pattern", {"airport": airport, "year": analysis_year})
        if daily_data and daily_data.get("hours"):
            df_daily = pd.DataFrame(daily_data["hours"])
            if not df_daily.empty:
                fig_daily = px.line(df_daily, x="hour", y="delay_rate",
                                    title=f"{airport} Hourly Delay Rate ({analysis_year})",
                                    markers=True, color_discrete_sequence=["#4caf50"])
                fig_daily.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_daily, use_container_width=True)

                best_hour = df_daily.loc[df_daily['delay_rate'].idxmin()]
                worst_hour = df_daily.loc[df_daily['delay_rate'].idxmax()]
                col1, col2 = st.columns(2)

        # Weekly patterns
        st.markdown("### Weekly Delay Patterns")
        weekly_data = safe_api_call("weekly-pattern", {"airport": airport, "year": analysis_year})
        if weekly_data and weekly_data.get("days"):
            df_weekly = pd.DataFrame(weekly_data["days"])
            if not df_weekly.empty:
                df_weekly['delay_rate_pct'] = df_weekly['delay_rate'] * 100
                fig_weekly = px.bar(df_weekly, x="dow", y="delay_rate_pct",
                                    title=f"{airport} Weekly Delay Rates ({analysis_year})",
                                    color_discrete_sequence=["#66bb6a"], text="delay_rate_pct")
                fig_weekly.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig_weekly.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_weekly, use_container_width=True)

                worst_day = df_weekly.loc[df_weekly['delay_rate_pct'].idxmax()]
                best_day = df_weekly.loc[df_weekly['delay_rate_pct'].idxmin()]
                col1, col2 = st.columns(2)
                col1.metric("Worst Day", worst_day['dow'], f"{worst_day['delay_rate_pct']:.1f}%")
                col2.metric("Best Day", best_day['dow'], f"{best_day['delay_rate_pct']:.1f}%")
    else:
        st.warning("Enter a valid 3-letter airport code (JFK, LAX, ORD, etc.)")

# DISRUPTION SCORE - Safe version
if selected_view == "Disruption Score":
    st.markdown("### Airport Disruption Score Dashboard")

    # Sidebar controls
    col1, col2 = st.columns([2, 1])
    with col1:
        airport = st.text_input("Airport Code", "JFK", key="disruption_airport").upper().strip()
    with col2:
        year = st.selectbox("Year", [2023, 2024], index=1, key="disruption_year")

    if len(airport) == 3 and airport.isalpha():
        data = safe_api_call(f"disruption-score/{airport}", {"year": year})
        if data:
            # HERO GAUGE (center stage)
            st.markdown("---")
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            score = data.get('disruption_score', 0)
            level = data.get('disruption_level', 'Unknown')
            color = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(level, "⚪")

            # KEY METRICS ROW
            col1.metric(
                f"{color} {airport} Disruption Score",
                f"{score:.0f}/100",
                f"{data.get('vs_baseline', 'N/A')}"
            )
            col2.metric("Delay Frequency", f"{data.get('delay_frequency', 0) * 100:.1f}%")
            col3.metric("Cancel Frequency", f"{data.get('cancel_frequency', 0) * 100:.1f}%")
            col4.metric("Avg Delay", f"{data.get('avg_delay', 0):.0f} min")

            # STATUS & CAUSE
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.error(f"**Status**: {data.get('disruption_level', 'Unknown')}")
            with col2:
                st.info(f"**Top Issue**: {data.get('top_delay_cause', 'N/A')}")
        else:
            st.error("No disruption data available")
    else:
        st.warning("Enter valid 3-letter airport code (JFK, LAX, SFO, etc.)")

    # 📈 AIRPORT BENCHMARKS (Bonus!)
    st.markdown("---")
    st.markdown("### Airport Comparison")
    benchmark_airports = ["LAX", "JFK", "SFO", "ORD"]
    scores = []
    for apt in benchmark_airports:
        data = safe_api_call(f"disruption-score/{apt}", {"year": year})
        if data:
            scores.append({"airport": apt, "score": data.get('disruption_score', 0)})

    if scores:
        df = pd.DataFrame(scores)
        st.bar_chart(
            df.set_index("airport")["score"],
            use_container_width=True
        )

# ROUTE RISK - Safe version
if selected_view == "Route Risk":
    st.markdown("### Route Risk Analysis")
    year_route = st.selectbox("Year", [2023, 2024], index=1, key="route_risk_year")
    origin = st.text_input("Origin Airport", "JFK", key="route_origin").upper().strip()
    destinations = st.text_input("Destinations (comma-separated)", "LAX,ORD,ATL", key="route_destinations").strip()

    if len(origin) == 3 and origin.isalpha() and destinations:
        route_data = safe_api_call("route-risk", {
            "origin": origin,
            "destinations": destinations,
            "year": year_route
        }, "Analysing routes...")
        if route_data and route_data.get("routes"):
            st.success(
                f"Safest: {route_data.get('safest_route', 'N/A')} | Riskiest: {route_data.get('riskiest_route', 'N/A')}"
            )
            df_routes = pd.DataFrame(route_data["routes"][:5])
            st.dataframe(df_routes[['dest', 'risk_score', 'delay_rate']], use_container_width=True)
    else:
        st.warning("Enter valid origin (3 letters) and destinations")

# BEST TIME TO FLY - Safe version
if selected_view == "Best Time to Fly":
    st.markdown("### Best Time Analysis")
    year_best = st.selectbox("Year", [2023, 2024], index=1, key="best_time_year")
    airport = st.text_input("Airport", "JFK", key="best_time_airport").upper().strip()

    if len(airport) == 3 and airport.isalpha():
        best_data = safe_api_call(f"best-time/{airport}", {"year": year_best})
        if best_data:
            st.success(best_data.get("insight", "Analysis complete"))
            if best_data.get("best_hours") and best_data.get("worst_hours"):
                best_df = pd.DataFrame(best_data["best_hours"])
                worst_df = pd.DataFrame(best_data["worst_hours"])
                col1, col2 = st.columns(2)
                with col1:
                    best_hour = best_df.iloc[0]
                    st.metric("Best Hour", f"{int(best_hour['hour'])}:00")
                    st.metric("Delay Risk", f"{best_hour['delay_rate'] * 100:.1f}%")
                with col2:
                    worst_hour = worst_df.iloc[0]
                    st.metric("Worst Hour", f"{int(worst_hour['hour'])}:00")
                    st.metric("Delay Risk", f"{worst_hour['delay_rate'] * 100:.1f}%")
    else:
        st.warning("Enter a valid 3-letter airport code")
