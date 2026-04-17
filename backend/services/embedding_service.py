# =============================================================================
# services/embedding_service.py - Text Embedding Service
# =============================================================================
# This file handles the generation of vector embeddings from text.
# It loads a sentence-transformer model (e.g., all-MiniLM-L6-v2) and
# provides functions to:
#   - Convert a natural language query into a vector embedding for
#     similarity search against the Pinecone index.
#   - Convert database schema descriptions (table names, column info)
#     into vector embeddings for storage in Pinecone during ingestion.
# The embedding model is loaded once at startup and reused for efficiency.
# =============================================================================
