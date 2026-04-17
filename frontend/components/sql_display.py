# =============================================================================
# components/sql_display.py - SQL Query Display Component
# =============================================================================
# This file provides a reusable Streamlit component for displaying
# generated SQL queries:
#   - Renders the SQL in a styled code block with syntax highlighting.
#   - Includes a "Copy to Clipboard" button for easy copying.
#   - Shows the list of tables that were retrieved from Pinecone and
#     used as context for generating the SQL.
#   - Optionally displays an explanation of the generated query.
# Used by both query_page.py and history_page.py.
# =============================================================================
