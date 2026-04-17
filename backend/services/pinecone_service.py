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


from pinecone import Pinecone, ServerlessSpec
from config import PINECONE_API_KEY, PINECONE_INDEX_NAME, PINECONE_CLOUD, PINECONE_REGION, EMBEDDING_DIMENSION
import logging

logger = logging.getLogger(__name__)
_index = None

def get_index():
    global _index
    if _index is None:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        if PINECONE_INDEX_NAME not in [i.name for i in pc.list_indexes()]:
            logger.info(f"Creating Pinecone index: {PINECONE_INDEX_NAME}")
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
            )
        _index = pc.Index(PINECONE_INDEX_NAME)
    return _index

def upsert_schemas(records: list[dict]) -> dict:
    index = get_index()
    vectors = [
        {"id": r["id"], "values": r["embedding"], "metadata": r["metadata"]}
        for r in records
    ]
    for i in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[i:i+100])
        logger.info(f"Upserted batch {i//100 + 1}: {len(vectors[i:i+100])} vectors")
    return {"total_vectors": len(vectors)}

def search_similar(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    result = get_index().query(vector=query_embedding, top_k=top_k, include_metadata=True)
    return [{"id": m.id, "score": m.score, "metadata": m.metadata} for m in result.matches]

