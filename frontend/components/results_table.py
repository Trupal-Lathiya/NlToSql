# =============================================================================
# components/results_table.py - Query Results Table Component
# =============================================================================
# This file provides a reusable Streamlit component for displaying
# SQL query results in a table format:
#   - Converts the raw results (columns + rows) into a Pandas DataFrame.
#   - Renders the DataFrame using st.dataframe with sorting, searching,
#     and column resizing capabilities.
#   - Shows a row count summary (e.g., "Showing 25 of 150 rows").
#   - Provides a "Download CSV" button to export the results.
#   - Handles empty result sets with an informational message.
# Used by both query_page.py and history_page.py.
# =============================================================================
