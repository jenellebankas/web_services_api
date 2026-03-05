import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components import api
from components import metrics
from components.metrics import DARK_THEME


# ── helpers ─────────────────────────────────────────────────────────────────

def safe_api_call(endpoint: str, params: dict = None, spinner_text: str = "Loading..."):
    try:
        with st.spinner(spinner_text):
            return api.fetch(endpoint, params or {})
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        st.info("Try a different airport/year or check server status")
        return None


def safe_graph_call(endpoint: str, params: dict = None, spinner_text: str = "Loading..."):
    try:
        with st.spinner(spinner_text):
            return api.fetch_graph(endpoint, params or {})
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None


# ── page config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Flight Analytics", page_icon="✈️", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;600&display=swap');

:root {{
    --primary:  {DARK_THEME["primary"]};
    --accent:   {DARK_THEME["accent"]};
    --bg:       {DARK_THEME["bg"]};
    --card:     {DARK_THEME["card"]};
}}
.main .block-container {{ background-color: {DARK_THEME["bg"]}; }}
body, p, li  {{ color: {DARK_THEME["text"]}; font-family: 'DM Sans', sans-serif; }}
h1,h2,h3    {{ color: {DARK_THEME["accent"]} !important; }}
div[data-testid="stSidebarNav"] {{ display: none; }}

/* ripple chain card */
.hop-card {{
    background: {DARK_THEME["card"]};
    border-left: 4px solid {DARK_THEME["accent"]};
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
}}
.hop-card.recovered {{ border-left-color: #4caf50; }}
.hop-card.propagated {{ border-left-color: #ff7043; }}
.hop-card.origin     {{ border-left-color: #ffd54f; }}

/* score pill */
.score-pill {{
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem;
    font-weight: 600;
}}
</style>
""", unsafe_allow_html=True)

# ── sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Airport analytics")
    selected_view = st.radio(
        "Select analysis",
        [
            "System Overview",
            "Single Airport Overview",
            "Disruption Score",
            "Route Risk",
            "Best Time to Fly",
            "✈ Ripple Effect",
            "🌐 Network Contagion",
        ],
        index=0,
        key="nav_view",
    )

st.title("Flight Disruption Analytics")

# ════════════════════════════════════════════════════════════════════════════
# EXISTING VIEWS (unchanged)
# ════════════════════════════════════════════════════════════════════════════

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

    with tab2:
        st.markdown("### Compare Airport Performance")
        airports_input = st.text_input("Airports (comma-separated)", "JFK,LAX,ORD", key="compare_airports")
        compare_year = st.selectbox("Year", [2023, 2024], index=1, key="compare_year")
        if airports_input.strip():
            compare_data = safe_api_call("compare-airports", {"airports": airports_input.strip(), "year": compare_year})
            if compare_data and compare_data.get("airports"):
                st.dataframe(pd.DataFrame(compare_data["airports"]), use_container_width=True)

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

if selected_view == "Single Airport Overview":
    airport = st.text_input("Airport", "JFK", key="overview_airport").upper().strip()
    analysis_year = st.selectbox("Year", [2023, 2024], index=1, key="overview_year")

    if len(airport) == 3 and airport.isalpha():
        airport_data = safe_api_call(f"airport-delays/{airport}")
        if airport_data:
            col1, col2, col3, col4 = st.columns(4)
            metrics.metric_card("Total Flights", f"{airport_data.get('total_flights', 0):,}", col1)
            metrics.metric_card("Avg Delay", f"{airport_data.get('avg_arrival_delay', 0):.1f}min", col2)
            metrics.metric_card("Delay Rate", f"{airport_data.get('delay_rate', 0) * 100:.1f}%", col3)
            metrics.metric_card("Cancel Rate", f"{airport_data.get('cancel_rate', 0) * 100:.1f}%", col4)

        st.markdown("### Daily Delay Patterns")
        daily_data = safe_api_call("daily-pattern", {"airport": airport, "year": analysis_year})
        if daily_data and daily_data.get("hours"):
            df_daily = pd.DataFrame(daily_data["hours"])
            fig_daily = px.line(df_daily, x="hour", y="delay_rate",
                                title=f"{airport} Hourly Delay Rate ({analysis_year})",
                                markers=True, color_discrete_sequence=["#4caf50"])
            fig_daily.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_daily, use_container_width=True)

        st.markdown("### Weekly Delay Patterns")
        weekly_data = safe_api_call("weekly-pattern", {"airport": airport, "year": analysis_year})
        if weekly_data and weekly_data.get("days"):
            df_weekly = pd.DataFrame(weekly_data["days"])
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

if selected_view == "Disruption Score":
    st.markdown("### Airport Disruption Score Dashboard")
    col1, col2 = st.columns([2, 1])
    with col1:
        airport = st.text_input("Airport Code", "JFK", key="disruption_airport").upper().strip()
    with col2:
        year = st.selectbox("Year", [2023, 2024], index=1, key="disruption_year")

    if len(airport) == 3 and airport.isalpha():
        data = safe_api_call(f"disruption-score/{airport}", {"year": year})
        if data:
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            score = data.get('disruption_score', 0)
            level = data.get('disruption_level', 'Unknown')
            color = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(level, "⚪")
            col1.metric(f"{color} {airport} Disruption Score", f"{score:.0f}/100", data.get('vs_baseline', 'N/A'))
            col2.metric("Delay Frequency", f"{data.get('delay_frequency', 0) * 100:.1f}%")
            col3.metric("Cancel Frequency", f"{data.get('cancel_frequency', 0) * 100:.1f}%")
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.error(f"**Status**: {data.get('disruption_level', 'Unknown')}")
            with col2:
                st.info(f"**Top Issue**: {data.get('top_delay_cause', 'N/A')}")

    st.markdown("---")
    st.markdown("### Airport Comparison")
    benchmark_airports = ["LAX", "JFK", "SFO", "ORD"]
    scores = []
    for apt in benchmark_airports:
        d = safe_api_call(f"disruption-score/{apt}", {"year": year})
        if d:
            scores.append({"airport": apt, "score": d.get('disruption_score', 0)})
    if scores:
        st.bar_chart(pd.DataFrame(scores).set_index("airport")["score"], use_container_width=True)

if selected_view == "Route Risk":
    st.markdown("### Route Risk Analysis")
    year_route = st.selectbox("Year", [2023, 2024], index=1, key="route_risk_year")
    origin = st.text_input("Origin Airport", "JFK", key="route_origin").upper().strip()
    destinations = st.text_input("Destinations (comma-separated)", "LAX,ORD,ATL", key="route_destinations").strip()

    if len(origin) == 3 and origin.isalpha() and destinations:
        route_data = safe_api_call("route-risk", {"origin": origin, "destinations": destinations, "year": year_route})
        if route_data and route_data.get("routes"):
            st.success(f"Safest: {route_data.get('safest_route')} | Riskiest: {route_data.get('riskiest_route')}")
            df_routes = pd.DataFrame(route_data["routes"][:5])
            st.dataframe(df_routes[['dest', 'risk_score', 'delay_rate']], use_container_width=True)
    else:
        st.warning("Enter valid origin (3 letters) and destinations")

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
                    bh = best_df.iloc[0]
                    st.metric("Best Hour", f"{int(bh['hour'])}:00")
                    st.metric("Delay Risk", f"{bh['delay_rate'] * 100:.1f}%")
                with col2:
                    wh = worst_df.iloc[0]
                    st.metric("Worst Hour", f"{int(wh['hour'])}:00")
                    st.metric("Delay Risk", f"{wh['delay_rate'] * 100:.1f}%")
    else:
        st.warning("Enter a valid 3-letter airport code")

# ════════════════════════════════════════════════════════════════════════════
# NEW: RIPPLE EFFECT VIEW
# ════════════════════════════════════════════════════════════════════════════

if selected_view == "✈ Ripple Effect":
    st.markdown("## ✈ Delay Ripple Effect")
    st.caption(
        "Enter a flight and seed a hypothetical delay to see how it propagates "
        "through every subsequent leg that aircraft flies that day."
    )

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        carrier = st.text_input("Carrier code", "AA", max_chars=3).upper().strip()
    with col2:
        flight_num = st.number_input("Flight number", min_value=1, max_value=9999, value=100, step=1)
    with col3:
        flight_date = st.date_input("Date", value=pd.Timestamp("2024-06-15"))
    with col4:
        initial_delay = st.slider("Seed delay (mins)", min_value=15, max_value=300, value=60, step=15)

    run = st.button("▶  Simulate ripple", type="primary")

    if run and carrier:
        data = safe_graph_call(
            f"ripple-effect",
            {
                "carrier": carrier,
                "flight_num": int(flight_num),
                "flight_date": str(flight_date),
                "initial_delay": initial_delay,
            },
            spinner_text="Simulating delay chain...",
        )

        if data:
            chain = data.get("chain", [])

            # ── summary metrics ──────────────────────────────────────────
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Legs in chain", len(chain))
            c2.metric("Flights affected", data.get("total_flights_affected", 0))
            c3.metric("Seed delay", f"{data.get('initial_delay_mins', 0):.0f} min")
            c4.metric("Final carried delay", f"{data.get('final_carried_delay', 0):.0f} min")

            # ── delay decay chart ────────────────────────────────────────
            st.markdown("### Delay across each leg")
            if chain:
                df_chain = pd.DataFrame(chain)
                df_chain["leg"] = [
                    f"{r['origin']}→{r['dest']}" for _, r in df_chain.iterrows()
                ]
                colour_map = {"origin": "#ffd54f", "propagated": "#ff7043"}
                bar_colours = [
                    colour_map.get(s, "#4caf50") for s in df_chain["source"].tolist()
                ]

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_chain["leg"],
                    y=df_chain["estimated_delay_mins"],
                    marker_color=bar_colours,
                    text=df_chain["estimated_delay_mins"].apply(lambda x: f"{x:.0f}m"),
                    textposition="outside",
                ))
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color=DARK_THEME["text"],
                    xaxis_title="Flight leg",
                    yaxis_title="Estimated delay (mins)",
                    height=350,
                    margin=dict(t=20),
                )
                st.plotly_chart(fig, use_container_width=True)

                # ── legend ───────────────────────────────────────────────
                st.markdown(
                    "🟡 **Origin** &nbsp;&nbsp; 🔴 **Propagated** &nbsp;&nbsp; 🟢 **Recovered**",
                    unsafe_allow_html=True,
                )

            # ── hop-by-hop cards ─────────────────────────────────────────
            st.markdown("### Leg-by-leg breakdown")
            for hop in chain:
                css_class = hop.get("source", "propagated")
                dep = hop.get("crs_dep_time", "")[:16] if hop.get("crs_dep_time") else ""
                absorbed = hop.get("delay_absorbed_mins", 0)
                estimated = hop.get("estimated_delay_mins", 0)
                st.markdown(f"""
                <div class="hop-card {css_class}">
                    <strong>{hop.get('origin')} → {hop.get('dest')}</strong>
                    &nbsp;·&nbsp; Flight {hop.get('flight_num')}
                    &nbsp;·&nbsp; Dep {dep}
                    <br/>
                    Carried delay: <strong>{estimated:.0f} min</strong>
                    &nbsp;|&nbsp; Absorbed by ground buffer: <strong>{absorbed:.0f} min</strong>
                    &nbsp;|&nbsp; <em>{css_class}</em>
                </div>
                """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# NEW: NETWORK CONTAGION VIEW
# ════════════════════════════════════════════════════════════════════════════

if selected_view == "🌐 Network Contagion":
    st.markdown("## 🌐 Network Contagion")
    st.caption(
        "See how influential each airport is in the US flight network. "
        "A high contagion score means delays there tend to ripple across the country."
    )

    tab1, tab2 = st.tabs(["Airport Score", "Network Leaderboard"])

    # ── tab 1: single airport ────────────────────────────────────────────────
    with tab1:
        st.markdown("### Contagion score for a single airport")
        col1, col2 = st.columns([2, 3])

        with col1:
            airport_c = st.text_input("Airport code", "ORD", max_chars=3, key="contagion_airport").upper().strip()
            depth = st.radio("Network depth", [1, 2, 3], horizontal=True, key="contagion_depth")
            go_btn = st.button("Analyse", type="primary", key="contagion_go")

        if go_btn and len(airport_c) == 3:
            score_data = safe_graph_call(f"contagion-score/{airport_c}")
            neighbors_data = safe_graph_call(f"network-neighbors/{airport_c}", {"depth": depth})

            with col2:
                if score_data:
                    composite = score_data.get("composite_score", 0)
                    pct = int(composite * 100)

                    # radial gauge
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=pct,
                        number={"suffix": "%", "font": {"color": DARK_THEME["accent"]}},
                        gauge={
                            "axis": {"range": [0, 100], "tickcolor": DARK_THEME["text"]},
                            "bar": {"color": DARK_THEME["accent"]},
                            "bgcolor": DARK_THEME["card"],
                            "steps": [
                                {"range": [0, 25], "color": "#2a332a"},
                                {"range": [25, 50], "color": "#2d3d2d"},
                                {"range": [50, 75], "color": "#3a4e2a"},
                                {"range": [75, 100], "color": "#4a6a2a"},
                            ],
                            "threshold": {"line": {"color": "#ff7043", "width": 3}, "value": 75},
                        },
                        title={"text": f"{airport_c} Contagion Score",
                               "font": {"color": DARK_THEME["accent"]}},
                    ))
                    fig_gauge.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color=DARK_THEME["text"],
                        height=280,
                        margin=dict(t=40, b=0),
                    )
                    st.plotly_chart(fig_gauge, use_container_width=True)

            if score_data:
                st.markdown(f"> {score_data.get('interpretation', '')}")
                st.markdown("---")

                # component breakdown
                c1, c2, c3 = st.columns(3)
                c1.metric("Betweenness", f"{score_data.get('betweenness_score', 0):.3f}",
                          help="How often this airport lies on shortest paths between others")
                c2.metric("Degree", f"{score_data.get('degree_score', 0):.3f}",
                          help="Number of direct connections, normalised")
                c3.metric("Closeness", f"{score_data.get('closeness_score', 0):.3f}",
                          help="How quickly a delay could reach all other airports")

            # network neighbour map
            if neighbors_data and neighbors_data.get("neighbors"):
                st.markdown(f"### Airports reachable from {airport_c} within {depth} hop(s)")
                df_nb = pd.DataFrame(neighbors_data["neighbors"])

                # bar chart grouped by hop count
                hop_counts = df_nb.groupby("hops").size().reset_index(name="count")
                fig_hops = px.bar(
                    hop_counts, x="hops", y="count",
                    labels={"hops": "Hops away", "count": "Airports reachable"},
                    color_discrete_sequence=[DARK_THEME["accent"]],
                    title=f"{neighbors_data.get('total_reachable')} airports reachable",
                )
                fig_hops.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color=DARK_THEME["text"],
                    height=280,
                )
                st.plotly_chart(fig_hops, use_container_width=True)

                # show full table in expander
                with st.expander("See all reachable airports"):
                    st.dataframe(df_nb, use_container_width=True, hide_index=True)

    # ── tab 2: leaderboard ───────────────────────────────────────────────────
    with tab2:
        st.markdown("### Most & least influential airports in the US network")
        limit = st.slider("Airports to show at each end", 5, 25, 10, key="contagion_limit")

        lb_data = safe_graph_call("contagion-leaderboard", {"limit": limit},
                                  "Computing network scores...")

        if lb_data:
            st.caption(f"Scored across {lb_data.get('total_airports', '?')} airports in the network")

            most = lb_data.get("most_influential", [])
            least = lb_data.get("least_influential", [])

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 🔴 Most influential (highest contagion)")
                if most:
                    df_most = pd.DataFrame(most)[["airport_code", "composite_score",
                                                  "betweenness_score", "degree_score"]]
                    df_most["composite_score"] = df_most["composite_score"].apply(lambda x: f"{x:.3f}")
                    st.dataframe(df_most, use_container_width=True, hide_index=True)

                    # horizontal bar
                    df_plot = pd.DataFrame(most).head(10)
                    fig_most = px.bar(
                        df_plot, x="composite_score", y="airport_code",
                        orientation="h",
                        color="composite_score",
                        color_continuous_scale=["#2d5a2d", "#ff7043"],
                        labels={"composite_score": "Contagion score", "airport_code": "Airport"},
                    )
                    fig_most.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color=DARK_THEME["text"],
                        coloraxis_showscale=False,
                        height=350,
                        yaxis={"autorange": "reversed"},
                        margin=dict(l=0),
                    )
                    st.plotly_chart(fig_most, use_container_width=True)

            with col2:
                st.markdown("#### 🟢 Least influential (lowest contagion)")
                if least:
                    df_least = pd.DataFrame(least)[["airport_code", "composite_score",
                                                    "betweenness_score", "degree_score"]]
                    df_least["composite_score"] = df_least["composite_score"].apply(lambda x: f"{x:.3f}")
                    st.dataframe(df_least, use_container_width=True, hide_index=True)

                    df_plot2 = pd.DataFrame(least).head(10)
                    fig_least = px.bar(
                        df_plot2, x="composite_score", y="airport_code",
                        orientation="h",
                        color="composite_score",
                        color_continuous_scale=["#4caf50", "#2d5a2d"],
                        labels={"composite_score": "Contagion score", "airport_code": "Airport"},
                    )
                    fig_least.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color=DARK_THEME["text"],
                        coloraxis_showscale=False,
                        height=350,
                        yaxis={"autorange": "reversed"},
                        margin=dict(l=0),
                    )
                    st.plotly_chart(fig_least, use_container_width=True)
