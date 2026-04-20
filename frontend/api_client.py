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


import requests

BASE_URL = "http://localhost:8000"

def send_query(nl_query: str) -> dict:
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={"natural_language_query": nl_query},
            timeout=120
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timed out. The query took too long."}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Cannot connect to backend. Is the server running?"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


