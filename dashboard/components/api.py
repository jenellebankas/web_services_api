# dashboard/components/api.py
import requests
import streamlit as st

API_BASE_URL = "https://web-services-api.onrender.com/api/v1/analytics"


@st.cache_data(ttl=300)
def fetch(endpoint, params=None):
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None
