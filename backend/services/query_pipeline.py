# =============================================================================
# services/query_pipeline.py - End-to-End NL-to-SQL Pipeline Orchestrator
# =============================================================================
# This file orchestrates the complete NL-to-SQL workflow by chaining
# all individual services together in sequence:
#   1. Receive the natural language query from the route handler.
#   2. Call embedding_service to convert the NL query into a vector.
#   3. Call pinecone_service to find the most relevant table schemas.
#   4. Call llm_service with the NL query + retrieved schemas to generate SQL.
#   5. Call database_service to execute the generated SQL on SQL Server.
#   6. Return the generated SQL and query results back to the route handler.
# This file keeps the route handlers thin and the pipeline logic centralized.
# =============================================================================
