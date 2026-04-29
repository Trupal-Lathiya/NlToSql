# =============================================================================
# services/query_pipeline.py - End-to-End NL-to-SQL Pipeline Orchestrator
# =============================================================================
# This file orchestrates the complete NL-to-SQL workflow by chaining
# all individual services together in sequence:
#   1. Receive the natural language query from the route handler.
#   2. Call embedding_service to convert the NL query into a vector.
#   3. Call pinecone_service to find the most relevant table schemas.
#   4. Call llm_service with the NL query + retrieved schemas to generate SQL.
#   5. Call database_service to execute the generated SQL on SQL Server.
#   6. Return the generated SQL and query results back to the route handler.
# This file keeps the route handlers thin and the pipeline logic centralized.
# =============================================================================

import logging
import csv
import os
import re
# ✅ FIX 1: Import ThreadPoolExecutor to run classify + embed in parallel
from concurrent.futures import ThreadPoolExecutor
from services.embedding_service import embed_text
from services.pinecone_service import search_similar
from services.llm_service import generate_sql, generate_summary, detect_followup
from services.database_service import execute_query
from services.redis_cache_service import find_similar_cache, store_in_cache
from utils.prompt_templates import RELEVANCE_CHECK_PROMPT
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_CLASSIFIER_MODEL, CACHE_ENABLED

logger = logging.getLogger(__name__)

CSV_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "exports")

# SQL-level hard block — catches anything the LLM classifier missed
BLOCKED_SQL_KEYWORDS = [
    r'\bDELETE\b', r'\bDROP\b', r'\bTRUNCATE\b', r'\bALTER\b',
    r'\bINSERT\b', r'\bUPDATE\b', r'\bMERGE\b', r'\bEXEC\b',
    r'\bEXECUTE\b', r'\bCREATE\b', r'\bREPLACE\b',
]

# ✅ FIX 2: Module-level Groq client — created once, reused forever.
#    Previously this was created inside classify_query() on every single call.
_classifier_client = Groq(api_key=GROQ_API_KEY)


def classify_query(nl_query: str, conversation_history: list = None) -> str:
    try:
        # Build an optional history section to give the classifier context
        history_section = ""
        if conversation_history:
            recent = conversation_history[-3:]  # last 3 turns is enough
            lines = "\n".join(
                [f"Q{i+1}: {t.get('nl_query', '')}" for i, t in enumerate(recent)]
            )
            history_section = (
                f"Recent conversation history (for context):\n{lines}\n\n"
                f"Given this history, the current question may be a follow-up. "
                f"If it seems to continue the conversation, classify as ALLOWED.\n\n"
            )

        prompt = RELEVANCE_CHECK_PROMPT.format(
            nl_query=nl_query,
            history_section=history_section,
        )
        response = _classifier_client.chat.completions.create(
            model=GROQ_CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=20
        )
        answer = response.choices[0].message.content.strip().upper()
        answer = answer.strip(".\n\r ")
        logger.info(f"Query classification for '{nl_query}': {answer}")
        print(f"Query classification for '{nl_query}': {answer}")

        if answer.startswith("BLOCKED_D"):
            return "BLOCKED_DESTRUCTIVE"
        elif answer.startswith("BLOCKED_I"):
            return "BLOCKED_IRRELEVANT"
        elif answer.startswith("BLOCK"):
            destructive_words = ["delete", "drop", "truncate", "alter", "insert", "update", "remove", "merge"]
            if any(w in nl_query.lower() for w in destructive_words):
                return "BLOCKED_DESTRUCTIVE"
            return "BLOCKED_IRRELEVANT"
        elif answer.startswith("ALLOW") or answer == "":
            return "ALLOWED"
        else:
            logger.warning(f"Unrecognized classification response: '{answer}' — defaulting to ALLOWED")
            return "ALLOWED"

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return "ALLOWED"


def is_destructive_sql(sql: str) -> bool:
    """
    Safety net — checks generated SQL for destructive keywords.
    Uses word-boundary regex to avoid false positives on column names.
    """
    sql_upper = sql.upper()
    return any(re.search(pattern, sql_upper) for pattern in BLOCKED_SQL_KEYWORDS)


def extract_related_table_ids(matches: list[dict]) -> list[str]:
    """
    Reads the Relationships lines from matched schema texts and extracts
    referenced table names so they can be auto-fetched.
    Supports both → and -> arrow formats.
    """
    related = set()
    for match in matches:
        text = match["metadata"].get("text", "")
        for line in text.splitlines():
            line = line.strip()
            if "→" in line or "->" in line:
                arrow = "→" if "→" in line else "->"
                parts = line.split(arrow)
                if len(parts) == 2:
                    right = parts[1].strip()
                    if "." in right:
                        table_name = right.split(".")[0].strip()
                        if table_name:
                            related.add(table_name)
    return list(related)


def fetch_schemas_by_ids(table_ids: list[str], already_fetched_ids: list[str]) -> list[dict]:
    """
    Directly fetches schema records from Pinecone by table ID for tables
    that were referenced via FK relationships but not returned by similarity
    search. Guarantees the LLM always has the full JOIN context.

    ✅ FIX 3: Previously looped over each ID with a separate index.fetch()
    call per table — N tables = N network round-trips. Pinecone's fetch()
    accepts a list of IDs, so we now pass all missing IDs in one call.
    N network round-trips → 1.
    """
    from services.pinecone_service import get_index

    missing = [t for t in table_ids if t not in already_fetched_ids]
    if not missing:
        return []

    index = get_index()
    extra = []

    # ✅ Single batch fetch — one network call for all missing table IDs
    try:
        result = index.fetch(ids=missing)
        vectors = result.get("vectors", {})

        for table_id in missing:
            if table_id in vectors:
                metadata = vectors[table_id].get("metadata", {})
                extra.append({
                    "id": table_id,
                    "score": 0.0,
                    "metadata": metadata
                })
                logger.info(f"Auto-fetched FK-related table schema: {table_id}")
            else:
                logger.warning(f"FK-related table '{table_id}' not found in Pinecone.")

    except Exception as e:
        logger.error(f"Batch fetch failed for FK-related tables {missing}: {e}")

    return extra


def build_schema_context(matches: list[dict]) -> str:
    context_parts = []
    for match in matches:
        text = match["metadata"].get("text", "")
        if text:
            context_parts.append(text)
    return "\n\n".join(context_parts)


def save_csv(columns: list, rows: list, filename: str) -> str:
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(CSV_OUTPUT_DIR, filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    logger.info(f"CSV saved: {filepath}")
    return filepath


def run_pipeline(nl_query: str, top_k: int = 10, conversation_history: list = None) -> dict:
    try:
        print("\n" + "="*60)
        print(f"🚀 PIPELINE STARTED")
        print(f"   Query : {nl_query}")
        print(f"   Cache : {'ENABLED' if CACHE_ENABLED else 'DISABLED'}")
        print("="*60)

        # ── Step 1 (PARALLEL): Classify query + Embed query at the same time
        logger.info(f"Running classifier and embedding in parallel for: {nl_query}")
        print(f"\n[STEP 1]   ⚙️  Running classifier + embedding in parallel...")
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_classify = executor.submit(classify_query, nl_query, conversation_history)
            future_embed    = executor.submit(embed_text, nl_query)

            classification  = future_classify.result()
            query_embedding = future_embed.result()

        print(f"           ✅ Classification  : {classification}")
        print(f"           ✅ Embedding       : done (dim={len(query_embedding)})")

        # ── Gate: Check classification result ──────────────────────────
        if classification == "BLOCKED_DESTRUCTIVE":
            logger.warning(f"Blocked destructive query: {nl_query}")
            print(f"\n🚫 BLOCKED: Destructive query — pipeline stopped. Cache NOT checked.")
            print("="*60 + "\n")
            return {
                "status": "error",
                "message": "🚫 This assistant is read-only. Queries that delete, update, insert, or modify data are not allowed."
            }

        if classification == "BLOCKED_IRRELEVANT":
            logger.info(f"Blocked irrelevant query: {nl_query}")
            print(f"\n🚫 BLOCKED: Irrelevant query — pipeline stopped. Cache NOT checked.")
            print("="*60 + "\n")
            return {
                "status": "error",
                "message": "🗄️ Please ask a question related to your database — for example: 'Show me all drivers' or 'How many orders were placed this week?'"
            }

        # ── Step 2: Redis semantic cache lookup FIRST ─────────────────────────
        # ✅ FIX APPLIED:
        #    Previously: follow-up detection ran first, and if YES → cache was
        #    skipped entirely, even for identical repeated queries.
        #
        #    Now: cache is checked BEFORE follow-up detection.
        #    If the same query was asked before and is cached → return instantly.
        #    Follow-up detection only runs on a CACHE MISS.
        #
        cache_hit_entry = None

        print(f"\n[STEP 2]   🗃️  Redis Cache Check")
        if not CACHE_ENABLED:
            print(f"           ⏭️  SKIPPED — cache is DISABLED in config (CACHE_ENABLED=false)")
        else:
            print(f"           🔍 Searching Redis for semantically similar cached query...")
            cache_hit_entry = find_similar_cache(query_embedding)

            if cache_hit_entry:
                print(f"           ✅ CACHE HIT!")
                print(f"           └─ Matched question : '{cache_hit_entry.get('question', '')}'")
                print(f"           └─ Cached SQL       : {cache_hit_entry.get('sql', '')[:100]}{'...' if len(cache_hit_entry.get('sql', '')) > 100 else ''}")
                print(f"           └─ Cached at        : {cache_hit_entry.get('created_at', 'N/A')}")
                print(f"           ⏭️  Follow-up detection → SKIPPED (cache hit)")
                print(f"           ⏭️  Pinecone search    → SKIPPED (cache hit)")
                print(f"           ⏭️  LLM SQL generation → SKIPPED (cache hit)")
            else:
                print(f"           ❌ CACHE MISS — no similar query found in cache.")
                print(f"           ➡️  Proceeding with follow-up detection + full pipeline...")

        if cache_hit_entry:
            # ── CACHE HIT: reuse cached SQL, skip everything else ─────────────
            sql = cache_hit_entry["sql"]
            retrieved_tables = []
            is_followup = False  # cache hit is treated as a fresh resolved query

        else:
            # ── CACHE MISS: now detect follow-up and run full pipeline ─────────

            # ── Step 3: Detect if query is follow-up using conversation history ─
            is_followup = detect_followup(nl_query, conversation_history or [])
            logger.info(f"Follow-up detection for '{nl_query}': {is_followup}")
            print(f"\n[STEP 3]   🔗 Follow-up detection : {'YES' if is_followup else 'NO'}")

            # ── Step 4: Search Pinecone for relevant schemas ──────────────────
            print(f"\n[STEP 4]   🌲 Searching Pinecone for relevant tables...")
            logger.info("Searching Pinecone for relevant tables...")
            matches = search_similar(query_embedding, top_k=top_k)
            if not matches:
                print(f"           ❌ No matches returned from Pinecone.")
                print("="*60 + "\n")
                return {
                    "status": "error",
                    "message": "⚠️ No relevant tables found for your query. Please try rephrasing your question."
                }

            # ── Filter out low-confidence matches ─────────────────────────────
            PINECONE_SIMILARITY_THRESHOLD = 0.45
            strong_matches = [m for m in matches if m["score"] >= PINECONE_SIMILARITY_THRESHOLD]
            print(f"           └─ Total matches  : {len(matches)}")
            print(f"           └─ Strong matches : {len(strong_matches)} (score >= {PINECONE_SIMILARITY_THRESHOLD})")

            if not strong_matches:
                # ── History-based fallback ────────────────────────────────────
                previous_tables = None
                if conversation_history:
                    for turn in reversed(conversation_history):
                        if turn.get("retrieved_tables"):
                            previous_tables = turn["retrieved_tables"]
                            break

                if previous_tables:
                    logger.info(
                        f"All matches below threshold (best: {matches[0]['score']:.3f}). "
                        f"Falling back to previous turn tables: {previous_tables}"
                    )
                    print(f"           ⚠️  All scores below threshold (best: {matches[0]['score']:.3f}).")
                    print(f"           └─ Falling back to previous turn tables : {previous_tables}")
                    matches = fetch_schemas_by_ids(previous_tables, [])
                    if not matches:
                        print("="*60 + "\n")
                        return {
                            "status": "error",
                            "message": "⚠️ Could not retrieve previous table schemas. Please rephrase your question."
                        }
                    is_followup = True
                else:
                    best_score = matches[0]["score"]
                    logger.warning(f"All matches below threshold. Best score: {best_score:.3f}")
                    print(f"           ❌ All scores below threshold (best: {best_score:.3f}). No history fallback.")
                    print("="*60 + "\n")
                    return {
                        "status": "error",
                        "message": "🗄️ I couldn't find any relevant tables for your question. Your database may not contain data related to this topic. Please ask about data that exists in your database."
                    }
            else:
                matches = strong_matches

            already_fetched_ids = [m["id"] for m in matches]
            logger.info(f"Directly matched tables: {already_fetched_ids}")
            print(f"           └─ Matched tables : {already_fetched_ids}")

            # ── Auto-fetch FK-related tables missing from results ─────────────
            related_ids = extract_related_table_ids(matches)
            logger.info(f"FK-related tables detected: {related_ids}")

            extra_matches = fetch_schemas_by_ids(related_ids, already_fetched_ids)
            all_matches = matches + extra_matches

            retrieved_tables = [m["id"] for m in all_matches]
            logger.info(f"Final tables sent to LLM: {retrieved_tables}")
            if related_ids:
                print(f"           └─ FK-related tables fetched : {related_ids}")
            print(f"           └─ Final tables for LLM      : {retrieved_tables}")

            # ── Step 5: Build schema context for LLM ─────────────────────────
            schema_context = build_schema_context(all_matches)

            # ── Step 6: Generate SQL using Groq LLM ──────────────────────────
            print(f"\n[STEP 5]   🤖 Generating SQL with Groq LLM...")
            logger.info("Generating SQL with Groq...")
            llm_result = generate_sql(
                nl_query,
                schema_context,
                conversation_history=conversation_history if is_followup else None
            )
            if llm_result["status"] != "success":
                print(f"           ❌ LLM SQL generation FAILED.")
                print("="*60 + "\n")
                return {
                    "status": "error",
                    "message": "⚠️ I couldn't generate a valid query for your request. Please try rephrasing your question."
                }

            sql = llm_result["sql"]
            print(f"           ✅ SQL generated : {sql[:100]}{'...' if len(sql) > 100 else ''}")

            # ── Hard block destructive SQL even if LLM slips ─────────────────
            if is_destructive_sql(sql):
                logger.warning(f"LLM generated destructive SQL despite classification: {sql}")
                print(f"\n🚫 BLOCKED: Destructive SQL detected in LLM output — pipeline stopped.")
                print("="*60 + "\n")
                return {
                    "status": "error",
                    "message": "🚫 This assistant is read-only. Queries that delete, update, insert, or modify data are not allowed."
                }

            # ── Cache Write — only if cache enabled AND not a follow-up ───────
            print(f"\n[CACHE]    💾 Cache Write Check")
            if not CACHE_ENABLED:
                print(f"           ⏭️  SKIPPED — cache is DISABLED (CACHE_ENABLED=false)")
            elif is_followup:
                print(f"           ⏭️  SKIPPED — follow-up queries are NOT cached")
            else:
                print(f"           🔍 Checking for duplicates before storing...")
                stored = store_in_cache(
                    question=nl_query,
                    embedding=query_embedding,
                    sql=sql,
                )
                if stored:
                    print(f"           ✅ STORED — new cache entry saved successfully.")
                else:
                    print(f"           ⏭️  SKIPPED — similar entry already exists in cache (duplicate prevention).")

        # ── Step 6: Execute SQL on SQL Server ────────────────────────────────
        print(f"\n[STEP 6]   🗄️  Executing SQL on database...")
        logger.info(f"Executing SQL: {sql}")
        db_result = execute_query(sql)
        if db_result["status"] != "success":
            raw_msg = db_result.get("message", "")
            logger.error(f"DB execution error: {raw_msg}")
            print(f"           ❌ DB execution FAILED : {raw_msg}")
            print("="*60 + "\n")

            if any(code in raw_msg for code in ["42000", "42S02", "42S22"]):
                return {
                    "status": "error",
                    "message": "⚠️ I couldn't generate a valid query for your request. Please try rephrasing your question."
                }
            if "permission" in raw_msg.lower() or "access" in raw_msg.lower():
                return {
                    "status": "error",
                    "message": "🔒 You don't have permission to access this data. Please contact your administrator."
                }
            return {
                "status": "error",
                "message": "⚠️ Something went wrong while running your query. Please try again or rephrase your question."
            }

        columns = db_result["columns"]
        all_rows = db_result["rows"]
        display_rows = all_rows[:10]
        total_rows = len(all_rows)
        print(f"           ✅ Executed — {total_rows} row(s) returned, {len(columns)} column(s)")

        # ── Step 7: Generate human-friendly summary ───────────────────────────
        print(f"\n[STEP 7]   📝 Generating summary...")
        logger.info("Generating summary...")
        summary_result = generate_summary(nl_query, sql, columns, display_rows)
        summary = (
            summary_result.get("summary", "Query executed successfully.")
            if summary_result["status"] == "success"
            else "Query executed successfully."
        )
        print(f"           ✅ Summary generated.")

        # ── Step 8: Save CSV if rows > 10 ────────────────────────────────────
        csv_path = None
        if total_rows > 10:
            safe_name = "".join(c if c.isalnum() else "_" for c in nl_query[:30])
            csv_path = save_csv(columns, all_rows, f"{safe_name}.csv")
            print(f"\n[STEP 8]   📁 CSV exported : {csv_path}")

        print(f"\n✅ PIPELINE COMPLETE")
        print(f"   Source   : {'⚡ REDIS CACHE  (Pinecone + LLM skipped)' if cache_hit_entry else '🔄 FULL PIPELINE (Pinecone + LLM used)'}")
        print(f"   Rows     : {total_rows}")
        print(f"   Follow-up: {is_followup}")
        print("="*60 + "\n")

        return {
            "status": "success",
            "nl_query": nl_query,
            "sql": sql,
            "retrieved_tables": retrieved_tables,
            "columns": columns,
            "rows": display_rows,
            "all_rows": all_rows,
            "total_row_count": total_rows,
            "summary": summary,
            "is_followup": is_followup,
            "csv_path": csv_path
        }

    except Exception as e:
        logger.error(f"Pipeline failed for query '{nl_query}': {e}", exc_info=True)
        print(f"\n❌ PIPELINE ERROR: {e}")
        print("="*60 + "\n")
        return {
            "status": "error",
            "message": "⚠️ Something went wrong while processing your request. Please try again."
        }