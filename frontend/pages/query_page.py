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
