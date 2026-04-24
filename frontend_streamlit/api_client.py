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


# =============================================================================
# api_client.py - Backend API Communication Layer
# =============================================================================

import requests

BASE_URL = "http://localhost:8000"
MEMORY_SIZE = 5  # Max number of past turns to send


def send_query(nl_query: str, conversation_history: list[dict] | None = None) -> dict:
    """
    Sends a POST request to /query with the user's NL query
    and the last MEMORY_SIZE turns of conversation history.

    conversation_history items should have keys:
        - nl_query (str)
        - sql (str, optional)
        - summary (str, optional)
        - retrieved_tables (list[str], optional)
    """
    # Trim to last MEMORY_SIZE successful turns only
    history = []
    if conversation_history:
        successful = [
            h for h in conversation_history if h.get("status") == "success"
        ]
        for turn in successful[-MEMORY_SIZE:]:
            history.append({
                "nl_query": turn.get("nl_query", ""),
                "sql": turn.get("sql"),
                "summary": turn.get("summary"),
                "retrieved_tables": turn.get("retrieved_tables"),
            })

    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={
                "natural_language_query": nl_query,
                "conversation_history": history,
            },
            timeout=120,
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timed out. The query took too long."}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Cannot connect to backend. Is the server running?"}
    except Exception as e:
        return {"status": "error", "message": str(e)}