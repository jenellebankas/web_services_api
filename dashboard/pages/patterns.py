import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.components import api


st.markdown("# Weekly Patterns")
year = st.selectbox("Year", [2023, 2024], index=1)
airport = st.text_input("Airport Code", "JFK").upper().strip()

if airport:
    data = api.fetch(f"weekly-pattern/{airport}", {"year": year})
    if data:
        st.markdown(f"### Delay Patterns - {airport} ({year})")
        df = pd.DataFrame(data["days"])
        df['delay_rate_pct'] = df['delay_rate'] * 100
        df['cancel_rate_pct'] = df['cancel_rate'] * 100

        fig = px.bar(df, x="dow", y=["delay_rate_pct", "cancel_rate_pct"],
                     title=f"Weekly Delay & Cancel Rates - {airport}",
                     barmode="group", color_discrete_sequence=["#68a368", "#a8d0a8"])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                          font_color="#e8f0e8", title_font_color="#68a368")
        st.plotly_chart(fig, use_container_width=True)

        # Summary metrics
        worst_day = df.loc[df['delay_rate_pct'].idxmax()]
        best_day = df.loc[df['delay_rate_pct'].idxmin()]
        col1, col2, col3 = st.columns(3)
        col1.metric("Worst Day", f"{worst_day['dow']} ({worst_day['delay_rate_pct']:.1f}%)")
        col2.metric("Best Day", f"{best_day['dow']} ({best_day['delay_rate_pct']:.1f}%)")
        col3.metric("Weekly Avg", f"{df['delay_rate_pct'].mean():.1f}%")
