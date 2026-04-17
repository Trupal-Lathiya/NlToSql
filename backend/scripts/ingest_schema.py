# =============================================================================
# scripts/ingest_schema.py - Schema Ingestion Script
# =============================================================================
# This is a standalone script (not part of the API server) that reads
# the database schema metadata from data/schema_metadata.json, generates
# vector embeddings for each table's description using the embedding
# service, and upserts them into the Pinecone index.
# Run this script once initially and again whenever the database schema
# changes to keep the Pinecone index in sync.
# Usage: python scripts/ingest_schema.py
# =============================================================================
