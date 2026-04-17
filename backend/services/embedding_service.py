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


from FlagEmbedding import BGEM3FlagModel
from config import EMBEDDING_MODEL
import logging

logger = logging.getLogger(__name__)
_model = None

def get_model():
    global _model
    if _model is None:
        logger.info(f"Loading BGE-M3 model: {EMBEDDING_MODEL}")
        _model = BGEM3FlagModel(EMBEDDING_MODEL, use_fp16=True)
    return _model

def embed_text(text: str) -> list[float]:
    result = get_model().encode([text], batch_size=1, max_length=8192)
    return result["dense_vecs"][0].tolist()

def embed_texts(texts: list[str]) -> list[list[float]]:
    result = get_model().encode(texts, batch_size=12, max_length=8192, show_progress_bar=True)
    return [vec.tolist() for vec in result["dense_vecs"]]



