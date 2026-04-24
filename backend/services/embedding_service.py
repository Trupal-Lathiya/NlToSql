from FlagEmbedding import BGEM3FlagModel
from config import EMBEDDING_MODEL
import logging

logger = logging.getLogger(__name__)
_model = None

def get_model():
    global _model
    if _model is None:
        logger.info(f"Loading BGE-M3 model: {EMBEDDING_MODEL}")
        _model = BGEM3FlagModel(
            EMBEDDING_MODEL,
            use_fp16=False,
        )
        logger.info("Model loaded.")
    return _model

def embed_text(text: str) -> list[float]:
    result = get_model().encode(
        [text],
        batch_size=1,
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    return result["dense_vecs"][0].tolist()

def embed_texts(texts: list[str]) -> list[list[float]]:
    result = get_model().encode(
        texts,
        batch_size=4,
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    return [vec.tolist() for vec in result["dense_vecs"]]