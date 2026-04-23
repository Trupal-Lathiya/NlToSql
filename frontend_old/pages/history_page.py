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
    st.title("📜 Query History")

    if "history" not in st.session_state or not st.session_state.history:
        st.info("No queries yet. Go to the **Query** page to get started.")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔎 Search history", placeholder="Filter by keyword...", label_visibility="collapsed")
    with col2:
        if st.button("🗑️ Clear All History", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    st.markdown(f"**{len(st.session_state.history)} total queries stored**")
    st.divider()

    filtered = st.session_state.history
    if search.strip():
        kw = search.strip().lower()
        filtered = [
            r for r in filtered
            if kw in r.get("nl_query", "").lower()
            or kw in r.get("sql", "").lower()
            or kw in r.get("summary", "").lower()
        ]
        if not filtered:
            st.warning(f"No results matching **'{search}'**.")
            return

    for i, result in enumerate(filtered):
        timestamp = result.get("timestamp", "")
        label = f"Query {i+1}: {result['nl_query'][:70]}{'...' if len(result['nl_query']) > 70 else ''}"
        if timestamp:
            label += f"  ·  🕒 {timestamp}"

        with st.expander(label, expanded=False):
            st.markdown(f"**❓ Question:** {result['nl_query']}")
            if result.get("summary"):
                st.markdown("**🤖 Answer:**")
                st.markdown(result["summary"])
            st.markdown(f"**📊 Rows returned:** {result.get('total_row_count', 'N/A')}")
            if timestamp:
                st.caption(f"🕒 Executed at: {timestamp}")

            st.divider()
            render_sql_display(result["sql"], result["retrieved_tables"])

            st.divider()
            render_results_table(result["columns"], result["rows"], result["total_row_count"])

            if st.button("🗑️ Delete this entry", key=f"del_{i}"):
                st.session_state.history = [r for r in st.session_state.history if r is not result]
                st.rerun()