# =============================================================================
# services/redis_cache_service.py - Redis Semantic Cache Service
# =============================================================================
# Handles semantic caching for the NL2SQL pipeline.
# Cache stores: question, embedding, sql (NOT db results or summary).
# Uses cosine similarity to detect duplicate/similar queries.
# Supports TTL, LRU, and combined cache eviction modes.
# =============================================================================

import json
import uuid
import logging
import numpy as np
from datetime import datetime
from typing import Optional

import redis

from config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    CACHE_ENABLED,
    CACHE_TTL_ENABLED,
    CACHE_LRU_ENABLED,
    CACHE_TTL_SECONDS,
    SIMILARITY_THRESHOLD,
)

logger = logging.getLogger(__name__)

# Redis key prefix for all cache entries
CACHE_KEY_PREFIX = "nl2sql:cache:"

_redis_client: Optional[redis.Redis] = None


# ─────────────────────────────────────────────────────────────────────────────
# Redis client (singleton)
# ─────────────────────────────────────────────────────────────────────────────

def get_redis_client() -> redis.Redis:
    """Returns a singleton Redis client. Raises on connection failure."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            decode_responses=True,   # all values come back as str
        )
        # Verify connectivity immediately so we fail fast at startup
        _redis_client.ping()
        logger.info(f"Redis connected at {REDIS_HOST}:{REDIS_PORT} db={REDIS_DB}")
    return _redis_client


# ─────────────────────────────────────────────────────────────────────────────
# Cosine similarity helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Returns cosine similarity in [0, 1] between two vectors."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _all_cache_keys() -> list[str]:
    """Returns all cache entry keys stored in Redis."""
    try:
        client = get_redis_client()
        return client.keys(f"{CACHE_KEY_PREFIX}*")
    except Exception as e:
        logger.error(f"Redis: failed to list keys: {e}")
        return []


def _get_entry(key: str) -> Optional[dict]:
    """Deserialises a single cache entry from Redis. Returns None on error."""
    try:
        raw = get_redis_client().get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Redis: failed to read key {key}: {e}")
        return None


def _write_entry(entry: dict, with_ttl: bool) -> bool:
    """
    Writes a cache entry to Redis.
    - with_ttl=True  → store with CACHE_TTL_SECONDS expiry
    - with_ttl=False → store without expiry (LRU eviction only)
    Returns True on success.
    """
    key = f"{CACHE_KEY_PREFIX}{entry['id']}"
    payload = json.dumps(entry)
    try:
        client = get_redis_client()
        if with_ttl:
            client.setex(key, CACHE_TTL_SECONDS, payload)
            logger.debug(f"Redis: stored {key} with TTL={CACHE_TTL_SECONDS}s")
        else:
            client.set(key, payload)
            logger.debug(f"Redis: stored {key} without TTL")
        return True
    except Exception as e:
        logger.error(f"Redis: failed to write key {key}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def find_similar_cache(query_embedding: list[float]) -> Optional[dict]:
    """
    Scans all cached embeddings and returns the best-matching entry
    if its cosine similarity >= SIMILARITY_THRESHOLD.

    Returns the full cache entry dict on HIT, or None on MISS.
    """
    if not CACHE_ENABLED:
        return None

    best_score = -1.0
    best_entry = None

    keys = _all_cache_keys()
    if not keys:
        logger.debug("Redis cache: empty, treating as MISS")
        return None

    for key in keys:
        entry = _get_entry(key)
        if entry is None:
            continue
        cached_emb = entry.get("embedding")
        if not cached_emb:
            continue

        score = _cosine_similarity(query_embedding, cached_emb)
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_score >= SIMILARITY_THRESHOLD:
        logger.info(
            f"Redis cache HIT (similarity={best_score:.4f} >= {SIMILARITY_THRESHOLD}): "
            f"question='{best_entry.get('question', '')}'"
        )
        return best_entry

    logger.info(
        f"Redis cache MISS (best similarity={best_score:.4f} < {SIMILARITY_THRESHOLD})"
    )
    return None


def store_in_cache(question: str, embedding: list[float], sql: str) -> bool:
    """
    Stores a new cache entry ONLY if no similar entry already exists
    (duplicate prevention with cosine similarity >= SIMILARITY_THRESHOLD).

    Cache entry structure:
        {
            id:         <uuid>,
            question:   <original NL query>,
            embedding:  <dense vector>,
            sql:        <generated SQL>,
            created_at: <ISO timestamp>,
        }

    Cache write mode (from .env):
        TTL=true,  LRU=false  → store with expiry
        TTL=false, LRU=true   → store without expiry (LRU handles eviction)
        TTL=true,  LRU=true   → store with expiry (also subject to LRU)
        TTL=false, LRU=false  → store without expiry (no eviction control)
    """
    if not CACHE_ENABLED:
        return False

    # Duplicate prevention: check similarity before inserting
    existing = find_similar_cache(embedding)
    if existing is not None:
        logger.info(
            f"Redis cache: duplicate detected for '{question}' — skipping insert."
        )
        return False  # do NOT store; reuse existing entry

    entry = {
        "id": str(uuid.uuid4()),
        "question": question,
        "embedding": embedding,
        "sql": sql,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Decide TTL based on config flags
    use_ttl = CACHE_TTL_ENABLED  # LRU is a global Redis policy; we only control TTL here

    success = _write_entry(entry, with_ttl=use_ttl)
    if success:
        logger.info(
            f"Redis cache: stored new entry id={entry['id']} "
            f"(TTL={'yes' if use_ttl else 'no'}, LRU={'yes' if CACHE_LRU_ENABLED else 'no'})"
        )
    return success