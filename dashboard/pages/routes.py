import streamlit as st
import pandas as pd
import plotly.express as px
from components import api


st.markdown("# Route Risk Analysis")
year = st.selectbox("Year", [2023, 2024], index=1)
origin = st.text_input("Origin Airport", "JFK").upper().strip()
destinations = st.text_input("Destinations", "LAX,ORD,ATL",
                             help="Comma-separated: LAX,ORD,ATL").upper().strip()

if origin and destinations:
    data = api.fetch("route-risk", {"origin": origin, "destinations": destinations, "year": year})
    if data:
        st.markdown(f"### Routes from {origin}")
        st.success(f"Safest: **{data['safest_route']}** | Riskiest: **{data['riskiest_route']}**")

        df = pd.DataFrame(data["routes"])
        fig = px.bar(df, x="dest", y="risk_score", title="Route Risk Scores",
                     color="risk_score", color_continuous_scale="Greens")
        st.plotly_chart(fig, use_container_width=True)
