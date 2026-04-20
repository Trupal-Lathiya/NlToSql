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
from typing import Optional, List, Any

class QueryRequest(BaseModel):
    natural_language_query: str

class QueryResponse(BaseModel):
    status: str
    nl_query: str
    sql: str
    retrieved_tables: List[str]
    columns: List[str]
    rows: List[List[Any]]
    total_row_count: int
    summary: str
    csv_path: Optional[str] = None

class ErrorResponse(BaseModel):
    status: str
    message: str
