import requests
import streamlit as st
from ..config import API_BASE_URL


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
