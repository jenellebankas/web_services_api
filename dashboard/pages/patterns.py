import streamlit as st
import pandas as pd
import plotly.express as px
from components import api

st.markdown("# Weekly Patterns")
year = st.selectbox("Year", [2023, 2024], index=1, key="weekly_year")
airport = st.text_input("Airport Code", "JFK").upper().strip()

if airport:
    with st.spinner(f"Loading {airport} patterns..."):
        data = api.fetch(f"weekly-pattern/{airport}", {"year": year})

    if data and data["days"]:
        st.markdown(f"### Delay Patterns - {airport} ({year})")

        # Convert to DataFrame
        df = pd.DataFrame(data["days"])
        df['delay_rate_pct'] = df['delay_rate'] * 100
        df['cancel_rate_pct'] = df['cancel_rate'] * 100

        # 1️⃣ BEAUTIFUL GROUPED BAR CHART (full width)
        fig = px.bar(df, x="dow", y=["delay_rate_pct", "cancel_rate_pct"],
                     title=f"{airport} Weekly Delay & Cancel Rates ({year})",
                     barmode="group",
                     color_discrete_sequence=["#4caf50", "#81c784"],
                     text_auto=True)

        fig.update_traces(textfont_size=12, textangle=0, textposition="outside")
        fig.update_layout(
            height=500,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color="#2e7d32",
            title_font_color="#1b5e20",
            bargap=0.2,
            xaxis_title="Day of Week",
            yaxis_title="Percentage (%)"
        )
        st.plotly_chart(fig, use_container_width=True)

        # 2️⃣ EXECUTIVE SUMMARY CARDS (3 columns)
        st.markdown("---")
        worst_day = df.loc[df['delay_rate_pct'].idxmax()]
        best_day = df.loc[df['delay_rate_pct'].idxmin()]
        avg_delay = df['avg_arr_delay'].mean()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Worst Day", f"{worst_day['dow']}",
                      f"{worst_day['delay_rate_pct']:.1f}%")
        with col2:
            st.metric("Best Day", f"{best_day['dow']}",
                      f"{best_day['delay_rate_pct']:.1f}%")
        with col3:
            st.metric("Avg Delay", f"{avg_delay:.1f} min")
        with col4:
            improvement = (
                        (worst_day['delay_rate_pct'] - best_day['delay_rate_pct']) / worst_day['delay_rate_pct'] * 100)
            st.metric("Avoid Peak", f"{improvement:.0f}% better")

        # 3️⃣ HORIZONTAL TREND CHART (secondary viz)
        st.markdown("### Day-by-Day Comparison")
        fig_trend = px.line(df, x="dow", y="delay_rate_pct",
                            markers=True, text="delay_rate_pct",
                            title="Delay Rate Trend Across Week",
                            color_discrete_sequence=["#388e3c"])
        fig_trend.update_traces(textposition="top center", texttemplate="%{text:.1f}%")
        fig_trend.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_trend, use_container_width=True)

        # 4️⃣ COMPACT DATA TABLE (styled, collapsible)
        with st.expander(f"Detailed Data ({len(df)} days)", expanded=False):
            styled_df = df[['dow', 'avg_arr_delay', 'delay_rate_pct', 'cancel_rate_pct']].copy()
            styled_df.columns = ['Day', 'Avg Delay (min)', 'Delay Rate (%)', 'Cancel Rate (%)']
            styled_df = styled_df.round(1)
            styled_df_style = styled_df.style.background_gradient(
                subset=['Delay Rate (%)', 'Cancel Rate (%)'], cmap='RdYlGn_r'
            ).format({
                'Avg Delay (min)': '{:.1f}',
                'Delay Rate (%)': '{:.1f}%',
                'Cancel Rate (%)': '{:.1f}%'
            })
            st.dataframe(styled_df_style, use_container_width=True)

    else:
        st.warning(f"No weekly data found for {airport} ({year})")
        st.info("Try JFK, LAX, ORD, or ATL")
