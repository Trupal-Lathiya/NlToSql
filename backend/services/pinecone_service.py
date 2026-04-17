# =============================================================================
# services/pinecone_service.py - Pinecone Vector Database Service
# =============================================================================
# This file manages all interactions with the Pinecone vector database:
#   - Initialize/connect to the Pinecone index on startup.
#   - Upsert: Store table schema embeddings (with metadata like table name,
#     columns, data types) into the Pinecone index during schema ingestion.
#   - Query/Search: Given a user's NL query embedding, perform a similarity
#     search to retrieve the top-K most relevant table schemas.
#   - Delete: Remove specific table embeddings from the index.
#   - List: Retrieve all stored table metadata from the index.
# This service acts as the bridge between the embedding service and
# the LLM service, providing relevant context for SQL generation.
# =============================================================================
