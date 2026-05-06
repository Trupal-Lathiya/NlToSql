# =============================================================================
# models/schemas.py - Pydantic Request & Response Schemas
# =============================================================================
# This file defines all Pydantic models used for API request validation
# and response serialization:
#   - QueryRequest: Validates the incoming NL query from the user
#     (fields: natural_language_query).
#   - QueryResponse: Structures the API response with the generated SQL,
#     retrieved table names, and the query execution results.
#   - SchemaIngestRequest: Validates the incoming table schema data
#     for ingestion into Pinecone (fields: table_name, columns, descriptions).
#   - SchemaIngestResponse: Confirms successful schema ingestion.
#   - ErrorResponse: Standardized error response format.
#   - TableInfo: Represents metadata about a single database table.
# =============================================================================

from pydantic import BaseModel
from typing import Optional, List, Any, Literal, Union


class ConversationTurn(BaseModel):
    """A single turn in the conversation history"""
    nl_query: str
    sql: Optional[str] = None
    summary: Optional[str] = None
    retrieved_tables: Optional[List[str]] = None


class QueryRequest(BaseModel):
    """Incoming natural language query with optional conversation history"""
    natural_language_query: str
    conversation_history: Optional[List[ConversationTurn]] = []
    # ── Multitenancy ─────────────────────────────────────────────────────────
    # The frontend sends these after login. The pipeline uses them to scope
    # every generated SQL query to the correct user / customer.
    user_id: Optional[str] = None
    customer_id: Optional[int] = None


class QuerySuccessResponse(BaseModel):
    """Successful NL-to-SQL response"""
    status: Literal["success"]
    nl_query: str
    sql: str
    retrieved_tables: List[str]
    columns: List[str]
    rows: List[List[Any]]
    total_row_count: int
    summary: str
    is_followup: bool = False
    csv_path: Optional[str] = None


class QueryErrorResponse(BaseModel):
    """Error response for /query endpoint"""
    status: Literal["error"]
    message: str


class ErrorResponse(BaseModel):
    """General error response for other endpoints"""
    status: Literal[\"error\"] = "error"
    message: str


class SchemaIngestRequest(BaseModel):
    table_name: str
    columns: List[dict]
    description: Optional[str] = None


class SchemaIngestResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str
    table_name: str


# Combined type for the /query endpoint
QueryResponse = Union[QuerySuccessResponse, QueryErrorResponse]