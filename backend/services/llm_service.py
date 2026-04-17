# =============================================================================
# services/llm_service.py - Groq LLM Service for SQL Generation
# =============================================================================
# This file handles communication with the Groq LLM API to generate SQL:
#   - Constructs a prompt combining the user's natural language query with
#     the relevant table schemas retrieved from Pinecone.
#   - Sends the prompt to the Groq API (e.g., using llama3-70b model).
#   - Parses the LLM response to extract the clean SQL query.
#   - Includes prompt engineering logic to ensure the LLM generates
#     valid T-SQL syntax compatible with SQL Server.
#   - Handles error cases like malformed responses or API failures.
# =============================================================================
