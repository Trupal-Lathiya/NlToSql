# =============================================================================
# pages/history_page.py - Query History Page
# =============================================================================
# This file renders the query history page using Streamlit components:
#   - Fetches and displays a list of past NL queries and their generated
#     SQL queries from the backend.
#   - Each history entry shows: the original NL query, the generated SQL,
#     timestamp, and the number of results returned.
#   - Expandable sections (st.expander) to view the full results of each
#     past query without cluttering the page.
#   - A "Clear History" button to remove all past queries.
#   - A search/filter input to find specific past queries.
# Calls api_client.get_query_history() to fetch the history data.
# =============================================================================


import streamlit as st
from components.sql_display import render_sql_display
from components.results_table import render_results_table

def render():
    st.title("Query History")

    if "history" not in st.session_state or not st.session_state.history:
        st.info("No queries yet. Go to the Query page to get started.")
        return

    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()

    for i, result in enumerate(st.session_state.history):
        with st.expander(f"Query {i+1}: {result['nl_query'][:80]}"):
            st.markdown(f"**Question:** {result['nl_query']}")
            st.markdown(f"**Summary:** {result.get('summary', '')}")
            render_sql_display(result["sql"], result["retrieved_tables"])
            render_results_table(result["columns"], result["rows"], result["total_row_count"])


