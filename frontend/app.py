# =============================================================================
# app.py - Main Streamlit Application Entry Point
# =============================================================================
# This is the main file that runs the Streamlit frontend application.
# It sets up the page configuration (title, icon, layout), initializes
# session state variables, and renders the main page layout including:
#   - A sidebar with navigation (Query, Schema Management, History).
#   - The main content area which loads the appropriate page based on
#     the selected navigation option.
# Run this file with: streamlit run frontend/app.py
# =============================================================================


import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pages.query_page import render as render_query
from pages.history_page import render as render_history

st.set_page_config(
    page_title="NL2SQL",
    page_icon="🗄️",
    layout="wide"
)

with st.sidebar:
    st.title("🗄️ NL2SQL")
    st.markdown("Natural Language to SQL")
    st.divider()
    page = st.radio("Navigation", ["Query", "History"], label_visibility="collapsed")

if page == "Query":
    render_query()
elif page == "History":
    render_history()


