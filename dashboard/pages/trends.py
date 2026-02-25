import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.components import api

st.markdown("# Year-over-Year Trends")
airport = st.text_input("Airport Code", "JFK").upper().strip()

if airport:
    data = api.fetch(f"year-over-year/{airport}")
    if data:
        st.markdown(f"### Performance Comparison - {airport}")
        df = pd.DataFrame({
            "Year": ["2023", "2024"],
            "Avg Delay": [data["year_2023"]["avg_arrival_delay"], data["year_2024"]["avg_arrival_delay"]],
            "Delay Rate (%)": [data["year_2023"]["delay_rate"] * 100, data["year_2024"]["delay_rate"] * 100],
        })

        fig = px.bar(df, x="Year", y=["Avg Delay", "Delay Rate (%)"],
                     barmode="group", title=f"Trends - {airport}",
                     color_discrete_sequence=["#68a368", "#a8d0a8"])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                          font_color="#e8f0e8", title_font_color="#68a368")
        st.plotly_chart(fig, use_container_width=True)

        st.info(f"Improvement: {data['improvement_pct']:.1f}%")
