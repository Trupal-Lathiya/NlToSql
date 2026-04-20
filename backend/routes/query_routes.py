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

# =============================================================================
# routes/query_routes.py
# =============================================================================

from fastapi import APIRouter
from models.schemas import QueryRequest, QueryResponse
from services.query_pipeline import run_pipeline

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=QueryResponse)
def handle_query(request: QueryRequest):
    """
    Accepts natural language query and returns SQL + results or error.
    """
    result = run_pipeline(request.natural_language_query)
    return result
