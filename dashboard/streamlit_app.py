import streamlit as st
import pandas as pd
import plotly.express as px

from components import api, metrics
from components.metrics import DARK_THEME


st.set_page_config(page_title="Flight Analytics", page_icon="✈️", layout="wide")

# -------- THEME --------
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

# -------- HEADER --------
st.title("Flight Disruption Analytics")
st.markdown("**System‑wide disruption overview and airport‑level tools.**")

# -------- SIDEBAR NAVIGATION --------
with st.sidebar:
    st.header("Airport analytics")
    selected_view = st.radio(
        "Select analysis",
        [
            "Punctuality leaderboard",
            "Single airport overview",
            "Daily & weekly patterns",
            "Route analysis & best times",
        ],
        index=0,
        key="nav_view",
    )

    st.markdown("---")
    st.caption("API: /api/v1/analytics")

# -------- MAIN: SYSTEM‑WIDE ANALYTICS (always visible) --------
st.subheader("System‑wide analytics")

top_cols, year_col = st.columns([3, 1])
with year_col:
    system_year = st.selectbox("Year", [2023, 2024], index=1, key="system_year")

sys_c1, sys_c2, sys_c3, sys_c4 = st.columns(4)
system_data = api.fetch("system-overview")
if system_data:
    metrics.metric_card("Total flights", f"{system_data['total_flights']:,}", sys_c1)
    metrics.metric_card("Avg delay", f"{system_data['avg_delay_minutes']:.1f} min", sys_c2)
    metrics.metric_card("Delay rate", f"{system_data['national_delay_rate'] * 100:.1f}%", sys_c3)
    metrics.metric_card("Total cancellations", f"{system_data['total_cancellations']:,}", sys_c4)
else:
    st.warning("System overview loading…")

st.markdown("### Carrier performance (network‑wide)")
carrier_data = api.fetch("carrier-performance", {"year": system_year})
if carrier_data:
    df_carriers = pd.DataFrame(carrier_data)
    st.dataframe(
        df_carriers.head(10).style.background_gradient(cmap="Greens", subset=["otp_pct"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Carrier data loading…")

st.markdown("### Monthly disruption trends")
monthly_data = api.fetch("monthly-trends", {"year": system_year})
if monthly_data:
    df_monthly = pd.DataFrame(monthly_data)

    # Melt for two lines (delay_rate / cancel_rate)
    df_melt = df_monthly.melt(
        id_vars=["period"],
        value_vars=["delay_rate", "cancel_rate"],
        var_name="metric",
        value_name="rate",
    )

    fig = px.line(
        df_melt,
        x="period",
        y="rate",
        color="metric",
        title=f"Disruption trends {system_year}",
        color_discrete_sequence=["#68a368", "#a8d0a8"],
        labels={"rate": "Rate", "period": "Month"},
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e8f0e8",
        title_font_color="#68a368",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Monthly trends loading…")

st.markdown("---")

# -------- AIRPORT‑LEVEL VIEWS (sidebar‑controlled) --------
st.subheader("Airport‑level analytics")

if selected_view == "Punctuality leaderboard":
    st.markdown("#### Punctuality leaderboard")
    year_lb = st.selectbox("Year", [2023, 2024], index=1, key="lb_year")
    data = api.fetch("leaderboard/punctuality", {"year": year_lb})
    if data:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("Top 10 airports (on‑time)")
            df_top = pd.DataFrame(data["top_airports"])
            st.dataframe(df_top, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("Bottom 10 airports (most delays)")
            df_bottom = pd.DataFrame(data["bottom_airports"])
            st.dataframe(df_bottom, use_container_width=True, hide_index=True)

elif selected_view == "Single airport overview":
    st.markdown("#### Single airport overview")
    year_air = st.selectbox("Year", [2023, 2024], index=1, key="airport_year")
    airport = st.text_input("Airport code", "JFK", key="airport_overview").upper()
    if airport:
        data = api.fetch(f"airport-delays/{airport}")
        if data:
            c1, c2, c3, c4 = st.columns(4)
            metrics.metric_card("Total flights", f"{data['total_flights']:,}", c1)
            metrics.metric_card("Avg arrival delay", f"{data['avg_arrival_delay']:.1f} min", c2)
            metrics.metric_card("Delay rate", f"{data['delay_rate'] * 100:.1f}%", c3)
            metrics.metric_card("Cancel rate", f"{data['cancel_rate'] * 100:.1f}%", c4)

elif selected_view == "Daily & weekly patterns":
    st.markdown("#### Daily & weekly patterns")
    year_pat = st.selectbox("Year", [2023, 2024], index=1, key="pattern_year")
    airport_pat = st.text_input("Airport code", "JFK", key="pattern_airport").upper()

    if airport_pat:
        col_d, col_w = st.columns(2)

        with col_d:
            st.markdown("Daily (hour‑of‑day) departure pattern")
            daily = api.fetch(f"daily-pattern/{airport_pat}", {"year": year_pat})
            if daily:
                df_daily = pd.DataFrame(daily["hours"])
                st.dataframe(df_daily, use_container_width=True)

        with col_w:
            st.markdown("Weekly arrival pattern")
            weekly = api.fetch(f"weekly-pattern/{airport_pat}", {"year": year_pat})
            if weekly:
                df_weekly = pd.DataFrame(weekly["days"])
                st.dataframe(df_weekly, use_container_width=True)

elif selected_view == "Route analysis & best times":
    st.markdown("#### Route analysis & best times")
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("Best time to depart from an airport")
        year_best = st.selectbox("Year", [2023, 2024], index=1, key="best_year")
        airport_best = st.text_input("Airport code", "JFK", key="best_airport").upper()
        if airport_best:
            best_data = api.fetch(f"best-time/{airport_best}", {"year": year_best})
            if best_data:
                st.success(best_data["insight"])
                best_df = pd.DataFrame(best_data["best_hours"])
                worst_df = pd.DataFrame(best_data["worst_hours"])
                cb1, cb2 = st.columns(2)
                with cb1:
                    st.metric(
                        "Best hour",
                        f"{best_df.iloc[0]['hour']}:00",
                        help="Lowest delay risk",
                    )
                with cb2:
                    st.metric(
                        "Worst hour",
                        f"{worst_df.iloc[0]['hour']}:00",
                        help="Highest delay risk",
                    )

    with col_right:
        st.markdown("Route risk from an origin to multiple destinations")
        year_route = st.selectbox("Year", [2023, 2024], index=1, key="route_year")
        origin = st.text_input("Origin airport", "JFK", key="route_origin").upper()
        destinations = st.text_input(
            "Destination airports (comma‑separated)",
            "LAX,ORD,ATL",
            key="route_destinations",
        ).upper()

        if origin and destinations:
            route_data = api.fetch(
                "route-risk",
                {"origin": origin, "destinations": destinations, "year": year_route},
            )
            if route_data:
                st.success(
                    f"Safest: {route_data['safest_route']}  |  Riskiest: {route_data['riskiest_route']}"
                )
                df_routes = pd.DataFrame(route_data["routes"][:5])
                st.dataframe(
                    df_routes[["dest", "risk_score", "delay_rate", "cancel_rate"]].round(3),
                    use_container_width=True,
                    hide_index=True,
                )
