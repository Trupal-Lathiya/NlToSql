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


import streamlit as st
import pandas as pd

def render_results_table(columns: list, rows: list, total_row_count: int):
    if not rows:
        st.info("Query returned no results.")
        return

    df = pd.DataFrame(rows, columns=columns)
    
    st.markdown(f"**Showing {len(rows)} of {total_row_count} total rows**")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="query_results.csv",
        mime="text/csv"
    )


