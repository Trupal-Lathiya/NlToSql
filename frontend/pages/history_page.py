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
