# dashboard/streamlit_app.py
import requests
import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------
# CONFIGURATION
# -----------------------
API_BASE_URL = "https://web-services-api.onrender.com"

st.set_page_config(
    page_title="Flight Disruption Analytics",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark Forest Green Theme
st.markdown("""
    <style>
        :root {
            --primary-color: #2d5a2d;
            --secondary-color: #4a7c4a;
            --accent-color: #68a368;
            --background-color: #1a1f1a;
            --surface-color: #212622;
            --card-bg: #252a25;
            --sidebar-bg: #1f2421;
            --text-primary: #e8f0e8;
            --text-secondary: #b8c9b8;
        }

        .main .block-container {
            background-color: var(--background-color);
            padding-top: 1rem;
        }

        body { background-color: var(--background-color); color: var(--text-primary); }
        [data-testid="stSidebar"] { 
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--secondary-color);
        }
        h1, h2, h3 { color: var(--accent-color) !important; font-weight: 500; }

        .metric-container {
            background: linear-gradient(135deg, var(--card-bg) 0%, #2a332a 100%);
            border: 1px solid var(--secondary-color);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            border-left: 4px solid var(--accent-color);
            margin: 10px 0;
        }

        .stPlotlyChart {
            border-radius: 12px;
            background: var(--card-bg);
            border: 1px solid var(--secondary-color);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
    </style>
""", unsafe_allow_html=True)


# -----------------------
# HELPER FUNCTIONS
# -----------------------
@st.cache_data(ttl=300)
def fetch_data(endpoint: str, params=None):
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


# -----------------------
# METRIC DISPLAY FUNCTION (Fixed)
# -----------------------
def display_metric(title: str, value: str, col):
    """Display metric in styled card - FIXED version"""
    html = f"""
    <div class="metric-container">
        <h4 style='color: var(--text-secondary); margin: 0 0 8px 0;'>{title}</h4>
        <h1 style='color: var(--accent-color); margin: 0; font-size: 2.5rem;'>{value}</h1>
    </div>
    """
    col.markdown(html, unsafe_allow_html=True)


# -----------------------
# HEADER & SIDEBAR
# -----------------------
st.title("Flight Disruption Analytics")
st.markdown("Dark mode dashboard for airport performance insights")

with st.sidebar:
    st.markdown("### Analytics Menu")
    st.markdown("─" * 30)

    view = st.radio("Select view:", [
        "Airport Delays", "Year-over-Year", "Daily Pattern",
        "Weekly Pattern", "Leaderboard", "Best Time", "Route Risk"
    ], index=0)

    st.markdown("─" * 30)
    year = st.selectbox("Year", [2023, 2024], index=1)
    airport = st.text_input("Airport", "JFK", help="e.g., JFK, LAX, ORD").upper().strip()

    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# -----------------------
# VIEWS
# -----------------------
if view == "Airport Delays" and airport:
    st.markdown(f"### Delay Summary - {airport}")
    data = fetch_data(f"airport-delays/{airport}")
    if data:
        col1, col2, col3, col4 = st.columns(4)

        # FIXED: Proper string formatting before HTML
        display_metric("Total Flights", f"{data['total_flights']:,}", col1)
        display_metric("Avg Delay", f"{data['avg_arrival_delay']:.1f} min", col2)
        display_metric("Delay Rate", f"{data['delay_rate'] * 100:.1f}%", col3)
        display_metric("Cancel Rate", f"{data['cancel_rate'] * 100:.1f}%", col4)

        st.success(f"Most disrupted day: {data['worst_day']}")

elif view == "Year-over-Year" and airport:
    st.markdown(f"### Trends - {airport}")
    data = fetch_data(f"year-over-year/{airport}")
    if data:
        df = pd.DataFrame({
            "Year": ["2023", "2024"],
            "Avg Delay": [data["year_2023"]["avg_arrival_delay"], data["year_2024"]["avg_arrival_delay"]],
            "Delay Rate (%)": [data["year_2023"]["delay_rate"] * 100, data["year_2024"]["delay_rate"] * 100],
        })

        fig = px.bar(df, x="Year", y=["Avg Delay", "Delay Rate (%)"],
                     barmode="group", title="Performance Comparison",
                     color_discrete_sequence=["#68a368", "#a8d0a8"])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                          font_color="#e8f0e8", title_font_color="#68a368")
        st.plotly_chart(fig, use_container_width=True)

elif view == "Daily Pattern" and airport:
    st.markdown(f"### Hourly Patterns - {airport} ({year})")
    data = fetch_data(f"daily-pattern/{airport}", {"year": year})
    if data:
        df = pd.DataFrame([dict(hour=h['hour'], delay_rate=h['delay_rate'] * 100)
                           for h in data["hours"]])
        fig = px.line(df, x="hour", y="delay_rate", title="Delay Rate by Hour",
                      markers=True, color_discrete_sequence=["#68a368"])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                          font_color="#e8f0e8", title_font_color="#68a368")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("*Dark mode dashboard powered by FastAPI analytics*")
