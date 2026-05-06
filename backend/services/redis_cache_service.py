# =============================================================================
# services/redis_cache_service.py - Redis Semantic Cache Service
# =============================================================================
# Handles semantic caching for the NL2SQL pipeline.
#
# Cache key strategy:
#   - Admin (no user_id / no customer_id) → prefix "nl2sql:cache:admin:"
#   - Authenticated user                  → prefix "nl2sql:cache:user:<user_id>:"
#
# This means:
#   * Admin queries are cached globally and reused across admin sessions.
#   * Customer queries are cached per-user so one customer never sees another's
#     cached SQL (which may contain tenant-scoped WHERE clauses).
#   * Tenant queries are NEVER served from the admin cache and vice-versa.
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

# Redis key prefix for all cache entries (base — tenant suffix appended at runtime)
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
            decode_responses=True,
        )
        _redis_client.ping()
        logger.info(f"Redis connected at {REDIS_HOST}:{REDIS_PORT} db={REDIS_DB}")
    return _redis_client


# ─────────────────────────────────────────────────────────────────────────────
# Tenant-aware key prefix
# ─────────────────────────────────────────────────────────────────────────────

def _tenant_prefix(user_id: Optional[str] = None) -> str:
    """
    Returns the Redis key prefix scoped to this user.

    * No user_id  (admin / anonymous) → "nl2sql:cache:admin:"
    * user_id present (customer)      → "nl2sql:cache:user:<user_id>:"

    Admin and customer caches are completely isolated — a customer query will
    never hit or pollute the admin cache.
    """
    if user_id:
        return f"{CACHE_KEY_PREFIX}user:{user_id}:"
    return f"{CACHE_KEY_PREFIX}admin:"


# ─────────────────────────────────────────────────────────────────────────────
# Cosine similarity helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cosine_similarity(vec_a: list, vec_b: list) -> float:
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

def _all_cache_keys(prefix: str) -> list:
    """Returns all cache entry keys for the given prefix."""
    try:
        client = get_redis_client()
        return client.keys(f"{prefix}*")
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


def _write_entry(entry: dict, prefix: str, with_ttl: bool) -> bool:
    """
    Writes a cache entry to Redis under the given prefix.
    - with_ttl=True  → store with CACHE_TTL_SECONDS expiry
    - with_ttl=False → store without expiry (LRU eviction only)
    Returns True on success.
    """
    key = f"{prefix}{entry['id']}"
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

def find_similar_cache(
    query_embedding: list,
    user_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Scans cached embeddings scoped to this user and returns the best-matching
    entry if its cosine similarity >= SIMILARITY_THRESHOLD.

    Admin queries search the admin cache.
    Customer queries search only their own cache — never the admin cache.

    Returns the full cache entry dict on HIT, or None on MISS.
    """
    if not CACHE_ENABLED:
        return None

    prefix = _tenant_prefix(user_id)
    best_score = -1.0
    best_entry = None

    keys = _all_cache_keys(prefix)
    if not keys:
        logger.debug(f"Redis cache ({prefix}): empty, treating as MISS")
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
            f"Redis cache HIT [{prefix}] (similarity={best_score:.4f} >= {SIMILARITY_THRESHOLD}): "
            f"question='{best_entry.get('question', '')}'"
        )
        return best_entry

    logger.info(
        f"Redis cache MISS [{prefix}] (best similarity={best_score:.4f} < {SIMILARITY_THRESHOLD})"
    )
    return None


def store_in_cache(
    question: str,
    embedding: list,
    sql: str,
    user_id: Optional[str] = None,
) -> bool:
    """
    Stores a new cache entry ONLY if no similar entry already exists in this
    user's namespace (duplicate prevention via cosine similarity).

    Cache entry structure:
        {
            id:         <uuid>,
            question:   <original NL query>,
            embedding:  <dense vector>,
            sql:        <generated SQL>,
            created_at: <ISO timestamp>,
            user_id:    <user_id or "admin">,
        }

    Cache write mode (from .env):
        TTL=true,  LRU=false  → store with expiry
        TTL=false, LRU=true   → store without expiry (LRU handles eviction)
        TTL=true,  LRU=true   → store with expiry (also subject to LRU)
        TTL=false, LRU=false  → store without expiry (no eviction control)
    """
    if not CACHE_ENABLED:
        return False

    prefix = _tenant_prefix(user_id)

    # Duplicate prevention: check similarity before inserting
    existing = find_similar_cache(embedding, user_id=user_id)
    if existing is not None:
        logger.info(
            f"Redis cache [{prefix}]: duplicate detected for '{question}' — skipping insert."
        )
        return False

    entry = {
        "id":         str(uuid.uuid4()),
        "question":   question,
        "embedding":  embedding,
        "sql":        sql,
        "created_at": datetime.utcnow().isoformat(),
        "user_id":    user_id or "admin",
    }

    use_ttl = CACHE_TTL_ENABLED

    success = _write_entry(entry, prefix=prefix, with_ttl=use_ttl)
    if success:
        logger.info(
            f"Redis cache [{prefix}]: stored new entry id={entry['id']} "
            f"(TTL={'yes' if use_ttl else 'no'}, LRU={'yes' if CACHE_LRU_ENABLED else 'no'})"
        )
    return success