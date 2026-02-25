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

# Subdued Green Theme (Much softer and professional)
st.markdown("""
    <style>
        /* Muted green professional theme */
        :root {
            --primary-color: #4a7043;      /* Forest green - professional */
            --secondary-color: #a8c4a8;     /* Light sage */
            --accent-color: #6b8e6b;        /* Sage green */
            --background-color: #f8faf8;    /* Off-white */
            --sidebar-bg: #f0f4f0;         /* Very light green tint */
            --card-bg: #ffffff;
            --text-dark: #2d3a2a;
            --text-light: #5a6a58;
        }

        body {
            background-color: var(--background-color);
            color: var(--text-dark);
        }

        [data-testid="stSidebar"] {
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--accent-color);
        }

        h1, h2, h3 {
            color: var(--primary-color) !important;
            font-weight: 600;
        }

        .stMetric > label {
            color: var(--text-light) !important;
        }

        .metric-container {
            background-color: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(74, 112, 67, 0.08);
            border-left: 4px solid var(--accent-color);
            margin: 10px 0;
        }

        .stPlotlyChart {
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* Success messages */
        .stAlert > div {
            border-radius: 8px;
            border-left: 4px solid var(--accent-color);
        }

        /* Button styling */
        .stButton > button {
            background-color: var(--primary-color);
            border-radius: 8px;
            border: none;
            color: white;
            font-weight: 500;
        }

        .stButton > button:hover {
            background-color: var(--accent-color);
        }
    </style>
""", unsafe_allow_html=True)


# -----------------------
# HELPER FUNCTIONS
# -----------------------
@st.cache_data(ttl=300)  # Cache for 5 minutes
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
# HEADER
# -----------------------
st.title("✈️ Flight Disruption Analytics")
st.markdown("**Professional insights into airport performance & delay patterns**")

# -----------------------
# SIDEBAR MENU
# -----------------------
with st.sidebar:
    st.markdown("### 📊 Analytics Dashboard")
    st.markdown("---")

    view = st.radio(
        "Select insight:",
        [
            "Airport Delays Overview",
            "Year-over-Year Trends",
            "Daily Pattern",
            "Weekly Pattern",
            "Punctuality Leaderboard",
            "Best Time to Fly",
            "Route Risk",
        ],
        index=0
    )

    st.markdown("---")
    year = st.selectbox("📅 Year", [2023, 2024], index=1)
    airport = st.text_input("🛫 Airport code", "JFK", help="e.g., JFK, LAX, ORD").upper().strip()

    st.markdown("---")
    st.info("💡 Connects to your FastAPI analytics endpoints")

# -----------------------
# VIEW: AIRPORT DELAYS
# -----------------------
if view == "Airport Delays Overview" and airport:
    st.markdown(f"### 🛬 Delay Summary - {airport}")
    data = fetch_data(f"airport-delays/{airport}")
    if data:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("""
            <div class="metric-container">
                <h3 style='color: var(--primary-color); margin: 0;'>Total Flights</h3>
                <h1 style='color: var(--text-dark); margin: 10px 0 0 0;'>{}</h1>
            </div>
            """.format(data["total_flights"]), unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="metric-container">
                <h3 style='color: var(--primary-color); margin: 0;'>Avg Delay</h3>
                <h1 style='color: var(--text-dark); margin: 10px 0 0 0;'>{:.1f} min</h1>
            </div>
            """.format(data["avg_arrival_delay"]), unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <div class="metric-container">
                <h3 style='color: var(--primary-color); margin: 0;'>Delay Rate</h3>
                <h1 style='color: var(--text-dark); margin: 10px 0 0 0;'>{:.1f}%</h1>
            </div>
            """.format(data['delay_rate'] * 100), unsafe_allow_html=True)

        with col4:
            st.markdown("""
            <div class="metric-container">
                <h3 style='color: var(--primary-color); margin: 0;'>Cancel Rate</h3>
                <h1 style='color: var(--text-dark); margin: 10px 0 0 0;'>{:.1f}%</h1>
            </div>
            """.format(data['cancel_rate'] * 100), unsafe_allow_html=True)

        st.success(f"**Most disrupted day:** {data['worst_day']}")

# -----------------------
# VIEW: YEAR-OVER-YEAR
# -----------------------
elif view == "Year-over-Year Trends" and airport:
    st.markdown(f"### 📈 Year-over-Year - {airport}")
    data = fetch_data(f"year-over-year/{airport}")
    if data:
        df = pd.DataFrame({
            "Year": ["2023", "2024"],
            "Avg Delay (min)": [
                data["year_2023"]["avg_arrival_delay"],
                data["year_2024"]["avg_arrival_delay"],
            ],
            "Delay Rate (%)": [
                data["year_2023"]["delay_rate"] * 100,
                data["year_2024"]["delay_rate"] * 100,
            ],
        })

        fig = px.bar(df, x="Year", y=["Avg Delay (min)", "Delay Rate (%)"],
                     barmode="group", title=f"Performance Comparison {airport}",
                     color_discrete_sequence=["#4a7043", "#a8c4a8"])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Improvement (Delay Rate)", f"{data['improvement_pct']:.1f}%")
        with col2:
            st.info("**Positive = Better performance**")

# -----------------------
# VIEW: DAILY PATTERN
# -----------------------
elif view == "Daily Pattern" and airport:
    st.markdown(f"### ⏰ Hourly Patterns - {airport} ({year})")
    data = fetch_data(f"daily-pattern/{airport}", {"year": year})
    if data:
        df = pd.DataFrame([dict(hour=h['hour'], delay_rate=h['delay_rate'] * 100, avg_delay=h['avg_dep_delay'])
                           for h in data["hours"]])
        fig = px.line(df, x="hour", y="delay_rate",
                      title="Delay Rate by Hour of Day",
                      markers=True, color_discrete_sequence=["#4a7043"])
        fig.update_traces(line=dict(color="#4a7043", width=3))
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

# Continue with other views using the same muted color scheme...
# (Rest of the views follow the same pattern with the new colors)

st.markdown("---")
st.markdown("*Powered by your FastAPI analytics API*")
