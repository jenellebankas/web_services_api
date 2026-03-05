# dashboard/components/api.py
import requests
import streamlit as st

API_BASE_URL = "https://web-services-api.onrender.com/api/v1/analytics"
GRAPH_API_BASE_URL = "https://web-services-api.onrender.com/api/v1/graph"


@st.cache_data(ttl=300)
def fetch(endpoint: str, params: dict = None):
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


@st.cache_data(ttl=300)
def fetch_graph(endpoint: str, params: dict = None):
    """Calls the /api/v1/graph endpoints."""
    try:
        url = f"{GRAPH_API_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=30)  # graph calls can be slow
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Graph API Error: {e}")
        return None
