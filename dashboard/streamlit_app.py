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

# Source - https://stackoverflow.com/a/74281694
# Posted by sumshyftw
# Retrieved 2026-02-27, License - CC BY-SA 4.0

no_sidebar_style = """
    <style>
        div[data-testid="stSidebarNav"] {display: none;}
    </style>
"""
st.markdown(no_sidebar_style, unsafe_allow_html=True)

with st.sidebar:
    st.header("Airport analytics")
    selected_view = st.radio(
        "Select analysis",
        [
            "System Overview",
            "Single Airport Overview",
            "Route Risk",
            "Best Time to Fly"
        ],
        index=0,
        key="nav_view",
    )


# Header
st.title("Flight Disruption Analytics")

if selected_view == "System Overview":
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["Leaderboard", "Carrier Performance", "Time Patterns"])

    with tab1:
        st.markdown("## System-Wide Analytics")

        col1, col2, col3, col4 = st.columns(4)
        system_data = api.fetch("system-overview")
        if system_data:
            metrics.metric_card("Total Flights (US)", f"{system_data['total_flights']:,}", col1)
            metrics.metric_card("Industry Avg Delay", f"{system_data['avg_delay_minutes']:.1f} min", col2)
            metrics.metric_card("National Delay Rate", f"{system_data['national_delay_rate'] * 100:.1f}%", col3)
            metrics.metric_card("Total Cancellations", f"{system_data['total_cancellations']:,}", col4)
        else:
            st.warning("System overview loading...")

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

        # Row 2: Year-over-Year Airport Comparison
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

        # 2. TOP CARRIER PERFORMANCE (Network-wide)
        st.markdown("### Carrier Performance Ranking")
        carrier_data = api.fetch("carrier-performance", {"year": compare_year})  # Pass year param
        if carrier_data:
            df_carriers = pd.DataFrame(carrier_data)
            fig_carrier = px.bar(df_carriers.head(10), x="carrier", y="otp_pct",
                                 title="Top Carriers by On-Time Performance",
                                 color_discrete_sequence=["#4caf50"])
            st.plotly_chart(fig_carrier, use_container_width=True)
        else:
            st.info("Carrier data loading...")

    with tab3:

        st.markdown("### Monthly Disruption Trends")
        trends_year = st.selectbox("Year", [2023, 2024], index=1, label_visibility="collapsed", key="tab3_year")
        monthly_data = api.fetch("monthly-trends", {"year": trends_year})

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

if selected_view == "Single Airport Overview":
    # COMMON INPUTS (batch at top)
    airport = st.text_input("Airport", "JFK", key="overview_airport").upper()
    analysis_year = st.selectbox("Year", [2023, 2024], index=1, key="overview_year")

    if airport:
        # AIRPORT METRICS (existing - perfect)
        data = api.fetch(f"airport-delays/{airport}")
        if data:
            col1, col2, col3, col4 = st.columns(4)
            metrics.metric_card("Total Flights", f"{data['total_flights']:,}", col1)
            metrics.metric_card("Avg Delay", f"{data['avg_arrival_delay']:.1f}min", col2)
            metrics.metric_card("Delay Rate", f"{data['delay_rate'] * 100:.1f}%", col3)
            metrics.metric_card("Cancel Rate", f"{data['cancel_rate'] * 100:.1f}%", col4)

        # DAILY PATTERNS → CHART (NEW)
        st.markdown("### Daily Delay Patterns")
        daily_data = api.fetch("daily-pattern", {"airport": airport, "year": analysis_year})
        if daily_data and daily_data["hours"]:
            df_daily = pd.DataFrame(daily_data["hours"])
            fig_daily = px.line(df_daily, x="hour", y="delay_rate",
                                title=f"{airport} Hourly Delay Rate ({analysis_year})",
                                markers=True, color_discrete_sequence=["#4caf50"])
            fig_daily.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_daily, use_container_width=True)

            # Daily best/worst
            best_hour = df_daily.loc[df_daily['delay_rate'].idxmin()]
            worst_hour = df_daily.loc[df_daily['delay_rate'].idxmax()]
            col1, col2 = st.columns(2)
            col1.metric("Best Hour", f"{str(best_hour['hour']).replace('.',':')}0", f"{best_hour['delay_rate']:.1%}")
            col2.metric("Worst Hour", f"{str(worst_hour['hour']).replace('.', ':')}0", f"{worst_hour['delay_rate']:.1%}")

        # WEEKLY PATTERNS → CHART (NEW)
        st.markdown("### Weekly Delay Patterns")
        weekly_data = api.fetch("weekly-pattern", {"airport": airport, "year": analysis_year})
        if weekly_data and weekly_data["days"]:
            df_weekly = pd.DataFrame(weekly_data["days"])
            df_weekly['delay_rate_pct'] = df_weekly['delay_rate'] * 100

            fig_weekly = px.bar(df_weekly, x="dow", y="delay_rate_pct",
                                title=f"{airport} Weekly Delay Rates ({analysis_year})",
                                color_discrete_sequence=["#66bb6a"], text="delay_rate_pct")
            fig_weekly.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_weekly.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_weekly, use_container_width=True)

            # Weekly best/worst
            worst_day = df_weekly.loc[df_weekly['delay_rate_pct'].idxmax()]
            best_day = df_weekly.loc[df_weekly['delay_rate_pct'].idxmin()]
            col1, col2 = st.columns(2)
            col1.metric("Worst Day", worst_day['dow'], f"{worst_day['delay_rate_pct']:.1f}%")
            col2.metric("Best Day", best_day['dow'], f"{best_day['delay_rate_pct']:.1f}%")

if selected_view == "Route Risk":

    st.markdown("### Route Risk")
    year_route = st.selectbox("Year", [2023, 2024], index=1, key="route_risk_year")
    origin = st.text_input("Origin", "JFK", key="route_origin").upper()
    destinations = st.text_input("Destinations", "LAX,ORD,ATL", key="route_destinations")

    if origin and destinations:
        route_data = api.fetch("route-risk", {"origin": origin, "destinations": destinations, "year": year_route})
        if route_data:
            st.success(f"**Safest:** {route_data['safest_route']} | **Riskiest:** {route_data['riskiest_route']}")

            # Top 3 safest routes
            df_routes = pd.DataFrame(route_data["routes"][:3])
            st.dataframe(df_routes[['dest', 'risk_score', 'delay_rate']], use_container_width=True)

if selected_view == "Best Time to Fly":

    st.markdown("### Best Time to Fly")
    year_best = st.selectbox("Year", [2023, 2024], index=1, key="best_time_year")
    airport = st.text_input("Airport", "JFK", key="best_time_airport").upper()

    if airport:
        best_data = api.fetch(f"best-time/{airport}", {"year": year_best})
        if best_data:
            st.success(best_data["insight"])

            # Best vs Worst hours table
            col_best1, col_best2 = st.columns(2)
            best_df = pd.DataFrame(best_data["best_hours"])
            worst_df = pd.DataFrame(best_data["worst_hours"])

            with col_best1:
                st.metric("Best Hour", f"{str(best_df.iloc[0]['hour']).replace('.', ':')}0")
                st.metric("Delay Risk", f"{best_df.iloc[0]['delay_rate'] * 100:.1f}%")
            with col_best2:
                st.metric("Worst Hour", f"{str(worst_df.iloc[0]['hour']).replace('.', ':')}0")
                st.metric("Delay Risk", f"{worst_df.iloc[0]['delay_rate'] * 100:.1f}%")