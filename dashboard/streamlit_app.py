# dashboard/streamlit_app.py
import requests
import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------
# CONFIGURATION
# -----------------------
API_BASE_URL = "https://web-services-api.onrender.com/"

st.set_page_config(
    page_title="Flight Disruption Analytics",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global Style Override
st.markdown("""
    <style>
        /* Main theme */
        :root {
            --primary-color: #2e7d32;
            --secondary-color: #66bb6a;
            --background-color: #f6fff7;
        }

        body {
            background-color: var(--background-color);
        }

        [data-testid="stSidebar"] {
            background-color: #e8f5e9;
        }

        h1, h2, h3 {
            color: var(--primary-color);
        }

        .stProgress > div > div > div {
            background-color: var(--secondary-color);
        }

        .metric-container {
            background-color: white;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------
# HELPER FUNCTIONS
# -----------------------


def fetch_data(endpoint: str, params=None):
    """Safely fetch JSON data from API."""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None

# -----------------------
# SIDEBAR MENU
# -----------------------


st.sidebar.title("Analytics Dashboard")
st.sidebar.markdown("---")

view = st.sidebar.radio(
    "Select insight:",
    [
        "Airport Delays Overview",
        "Year-over-Year Trends",
        "Daily Pattern",
        "Weekly Pattern",
        "Punctuality Leaderboard",
        "Best Time to Fly",
        "Route Risk",
    ]
)

st.sidebar.markdown("---")
year = st.sidebar.selectbox("Select year", [2023, 2024])
airport = st.sidebar.text_input("Enter airport code (e.g., JFK, LAX)").upper().strip()

# -----------------------
# VIEW: AIRPORT DELAYS
# -----------------------
if view == "Airport Delays Overview" and airport:
    st.header(f"Delay Summary for {airport}")
    data = fetch_data(f"airport-delays/{airport}")
    if data:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Flights", data["total_flights"])
        col2.metric("Avg Delay (min)", data["avg_arrival_delay"])
        col3.metric("Delay Rate", f"{data['delay_rate']*100:.1f}%")
        col4.metric("Cancel Rate", f"{data['cancel_rate']*100:.1f}%")

        st.success(f"Most disrupted day historically: **{data['worst_day']}**")

# -----------------------
# VIEW: YEAR-OVER-YEAR
# -----------------------
elif view == "Year-over-Year Trends" and airport:
    st.header(f"Year-over-Year Performance for {airport}")
    data = fetch_data(f"year-over-year/{airport}")
    if data:
        df = pd.DataFrame({
            "Year": ["2023", "2024"],
            "Avg Delay (min)": [
                data["year_2023"]["avg_arrival_delay"],
                data["year_2024"]["avg_arrival_delay"],
            ],
            "Delay Rate": [
                data["year_2023"]["delay_rate"],
                data["year_2024"]["delay_rate"],
            ],
            "Cancel Rate": [
                data["year_2023"]["cancel_rate"],
                data["year_2024"]["cancel_rate"],
            ],
        })
        fig = px.bar(df, x="Year", y=["Delay Rate", "Cancel Rate"], barmode="group",
                     title="Delays and Cancellations per Year",
                     color_discrete_sequence=["#2e7d32", "#66bb6a"])
        st.plotly_chart(fig, use_container_width=True)

        st.info(f"Improvement YoY: {data['improvement_pct']}%")

# -----------------------
# VIEW: DAILY PATTERN
# -----------------------
elif view == "Daily Pattern" and airport:
    st.header(f"Hourly Delay Pattern at {airport}")
    data = fetch_data(f"daily-pattern/{airport}", {"year": year})
    if data:
        df = pd.DataFrame([dict(hour=h['hour'], delay_rate=h['delay_rate'], avg_delay=h['avg_dep_delay'])
                           for h in data["hours"]])
        fig = px.line(df, x="hour", y="delay_rate", title="Delay Rate by Hour of Day",
                      color_discrete_sequence=["#2e7d32"])
        st.plotly_chart(fig, use_container_width=True)

# -----------------------
# VIEW: WEEKLY PATTERN
# -----------------------
elif view == "Weekly Pattern" and airport:
    st.header(f"Weekly Pattern for {airport}")
    data = fetch_data(f"weekly-pattern/{airport}", {"year": year})
    if data:
        df = pd.DataFrame(data["days"])
        fig = px.bar(df, x="dow", y="delay_rate", title="Delay Rate by Day of Week",
                     color_discrete_sequence=["#388e3c"])
        st.plotly_chart(fig, use_container_width=True)

# -----------------------
# VIEW: LEADERBOARD
# -----------------------
elif view == "Punctuality Leaderboard":
    st.header("Punctuality Leaderboard")
    data = fetch_data("leaderboard/punctuality", {"year": year, "limit": 10})
    if data:
        df_top = pd.DataFrame(data["top_airports"])
        st.subheader("Top 10 Airports (On-Time Performance)")
        st.table(df_top)

        df_bottom = pd.DataFrame(data["bottom_airports"])
        st.subheader("Bottom 10 Airports (Most Delays)")
        st.table(df_bottom)

# -----------------------
# VIEW: BEST TIME
# -----------------------
elif view == "Best Time to Fly" and airport:
    st.header(f"Best Times to Fly from {airport}")
    data = fetch_data(f"best-time/{airport}", {"year": year})
    if data:
        st.success(data["insight"])
        best_df = pd.DataFrame(data["best_hours"])
        worst_df = pd.DataFrame(data["worst_hours"])
        fig = px.scatter(best_df, x="hour", y="delay_rate", size="total_flights",
                         title="Delay Risk by Hour", color_discrete_sequence=["#2e7d32"])
        st.plotly_chart(fig, use_container_width=True)

# -----------------------
# VIEW: ROUTE RISK
# -----------------------
elif view == "Route Risk" and airport:
    st.header(f"Route Risk Analysis from {airport}")
    destinations = st.text_input("Enter destinations (e.g., JFK,LAX,ORD)").upper().strip()
    if destinations:
        data = fetch_data("route-risk", {"origin": airport, "destinations": destinations, "year": year})
        if data:
            st.success(f"Safest route: **{data['safest_route']}**, Riskiest: **{data['riskiest_route']}**")
            df = pd.DataFrame(data["routes"])
            fig = px.bar(df, x="dest", y="risk_score", title="Route Risk Scores", color="risk_score",
                         color_continuous_scale="Greens", height=400)
            st.plotly_chart(fig, use_container_width=True)
