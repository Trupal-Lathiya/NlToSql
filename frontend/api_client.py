# =============================================================================
# api_client.py - Backend API Communication Layer
# =============================================================================
# This file handles all HTTP communication with the FastAPI backend using
# the 'requests' library. It provides functions to:
#   - send_query(nl_query): Sends a POST request to /query with the user's
#     natural language query and returns the generated SQL + results.
#   - get_query_history(): Fetches past query history from the backend.
#   - ingest_schema(schema_data): Sends schema metadata to /schema/ingest
#     for Pinecone indexing.
#   - get_indexed_tables(): Fetches the list of tables stored in Pinecone.
#   - delete_table(table_name): Removes a table's embeddings from Pinecone.
# Contains the BASE_URL configuration pointing to the backend server.
# All functions include error handling for network/timeout failures.
# =============================================================================
