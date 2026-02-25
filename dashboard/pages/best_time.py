import streamlit as st
import plotly.express as px
from dashboard.components import api


st.markdown("# Best Time to Fly")
year = st.selectbox("Year", [2023, 2024], index=1)
airport = st.text_input("Airport Code", "JFK").upper().strip()

if airport:
    data = api.fetch(f"best-time/{airport}", {"year": year})
    if data:
        st.markdown(f"### Optimal Times - {airport} ({year})")
        st.success(data["insight"])

        fig = px.scatter(data["best_hours"], x="hour", y="delay_rate", size="total_flights",
                         title="Best Hours (Green dots)", color_discrete_sequence=["#68a368"])
        st.plotly_chart(fig, use_container_width=True)
