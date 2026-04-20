# =============================================================================
# pages/query_page.py - NL-to-SQL Query Page
# =============================================================================
# This file renders the main query page using Streamlit components:
#   - A text input / text area for the user to type their natural language query.
#   - A "Generate SQL" submit button.
#   - A spinner shown while the backend processes the request.
#   - A code block (st.code) to display the generated SQL query with
#     syntax highlighting and a copy button.
#   - A dataframe / table (st.dataframe) to display the query results
#     returned from SQL Server in a sortable, scrollable table.
#   - Error messages (st.error) if the query fails or returns no results.
#   - Success feedback (st.success) when a query executes successfully.
# Calls api_client.send_query() to communicate with the backend.
# =============================================================================

import streamlit as st
from api_client import send_query
from components.sql_display import render_sql_display
from components.results_table import render_results_table
from datetime import datetime

def render():
    st.title("Ask Your Database")
    st.markdown("Type a question in plain English and get SQL results instantly.")

    nl_query = st.text_area(
        "Your Question",
        placeholder="e.g. Show me all journeys with harsh braking events",
        height=100,
        key="query_input"
    )

    if st.button("Generate & Run", type="primary", use_container_width=True):
        if not nl_query.strip():
            st.warning("Please enter a question.")
            return

        with st.spinner("Embedding → Searching → Generating SQL → Executing..."):
            result = send_query(nl_query)

        if result.get("status") == "error":
            st.error(f"❌ {result.get('message')}")
            return

        result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if "history" not in st.session_state:
            st.session_state.history = []
        st.session_state.history.insert(0, result)

        st.success("✅ Query executed successfully!")

        st.markdown("#### 🤖 Answer")
        st.markdown(result.get("summary", ""))

        st.divider()
        render_sql_display(result["sql"], result["retrieved_tables"])

        st.divider()
        render_results_table(result["columns"], result["rows"], result["total_row_count"])