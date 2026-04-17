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

import sys, os, json, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SCHEMA_METADATA_PATH
from services.embedding_service import embed_texts
from services.pinecone_service import upsert_schemas

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    with open(SCHEMA_METADATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    ids   = [e["id"]   for e in data]
    texts = [e["text"] for e in data]

    logger.info(f"Embedding {len(texts)} tables...")
    embeddings = embed_texts(texts)

    records = [
        {"id": tid, "embedding": emb, "metadata": {"id": tid, "text": txt}}
        for tid, txt, emb in zip(ids, texts, embeddings)
    ]

    result = upsert_schemas(records)
    logger.info(f"Done. {result['total_vectors']} vectors upserted into Pinecone.")

if __name__ == "__main__":
    main()



