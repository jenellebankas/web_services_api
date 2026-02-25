import streamlit as st
from dashboard.components import api
from dashboard.components import metrics


st.markdown("# Airport Delays Overview")
airport = st.text_input("Airport Code", "JFK", help="e.g., JFK, LAX, ORD").upper().strip()

if airport:
    data = api.fetch(f"airport-delays/{airport}")
    if data:
        st.markdown(f"### Delay Summary - {airport}")
        col1, col2, col3, col4 = st.columns(4)
        metrics.metric_card("Total Flights", f"{data['total_flights']:,}", col1)
        metrics.metric_card("Avg Delay", f"{data['avg_arrival_delay']:.1f} min", col2)
        metrics.metric_card("Delay Rate", f"{data['delay_rate']*100:.1f}%", col3)
        metrics.metric_card("Cancel Rate", f"{data['cancel_rate']*100:.1f}%", col4)
        st.success(f"Most disrupted day: {data['worst_day']}")
