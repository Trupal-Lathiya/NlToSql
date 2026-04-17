# =============================================================================
# routes/schema_routes.py - Database Schema Management API Endpoints
# =============================================================================
# This file defines API endpoints for managing database schema metadata:
#   - POST /schema/ingest : Accepts database schema information (table names,
#     column names, data types, relationships) and ingests them into Pinecone
#     as vector embeddings for later similarity search.
#   - GET /schema/tables : Returns a list of all tables currently indexed
#     in the Pinecone vector database.
#   - DELETE /schema/table/{name} : Removes a specific table's embeddings
#     from Pinecone.
# =============================================================================
