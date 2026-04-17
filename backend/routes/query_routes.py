# =============================================================================
# routes/query_routes.py - NL-to-SQL Query API Endpoints
# =============================================================================
# This file defines the main API endpoints for the NL-to-SQL workflow:
#   - POST /query : Accepts a natural language query from the user,
#     orchestrates the full pipeline (embedding → Pinecone search →
#     Groq SQL generation → SQL Server execution), and returns the
#     generated SQL query along with the query results to the frontend.
#   - GET /query/history : (Optional) Returns the history of past queries
#     and their results for display in the frontend.
# =============================================================================
