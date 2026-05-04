import logging
import csv
import os
import re
import asyncio
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

BLOCKED_SQL_KEYWORDS = [
    r'\bDELETE\b', r'\bDROP\b', r'\bTRUNCATE\b', r'\bALTER\b',
    r'\bINSERT\b', r'\bUPDATE\b', r'\bMERGE\b', r'\bEXEC\b',
    r'\bEXECUTE\b', r'\bCREATE\b', r'\bREPLACE\b',
]

_classifier_client = Groq(api_key=GROQ_API_KEY)


def classify_query(nl_query: str, conversation_history: list = None) -> str:
    try:
        history_section = ""
        if conversation_history:
            recent = conversation_history[-3:]
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
    sql_upper = sql.upper()
    return any(re.search(pattern, sql_upper) for pattern in BLOCKED_SQL_KEYWORDS)


def extract_related_table_ids(matches: list[dict]) -> list[str]:
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
    from services.pinecone_service import get_index

    missing = [t for t in table_ids if t not in already_fetched_ids]
    if not missing:
        return []

    index = get_index()
    extra = []

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


# =============================================================================
# Shared Steps 1-5 logic (used by both run_pipeline and run_pipeline_streaming)
# =============================================================================

def _run_steps_1_to_5(nl_query: str, top_k: int, conversation_history: list):
    """
    Runs steps 1-5 synchronously and returns a dict with everything needed
    to execute SQL (or an error dict).
    Returns: {"ok": True, "sql": ..., "retrieved_tables": ..., "is_followup": ...}
          or {"ok": False, "error": ...}
    """
    # ── Step 1 (PARALLEL): Classify + Embed ──────────────────────────────────
    print(f"\n[STEP 1]   ⚙️  Running classifier + embedding in parallel...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_classify = executor.submit(classify_query, nl_query, conversation_history)
        future_embed    = executor.submit(embed_text, nl_query)
        classification  = future_classify.result()
        query_embedding = future_embed.result()

    print(f"           ✅ Classification  : {classification}")
    print(f"           ✅ Embedding       : done (dim={len(query_embedding)})")

    if classification == "BLOCKED_DESTRUCTIVE":
        return {"ok": False, "error": "🚫 This assistant is read-only. Queries that delete, update, insert, or modify data are not allowed."}
    if classification == "BLOCKED_IRRELEVANT":
        return {"ok": False, "error": "🗄️ Please ask a question related to your database — for example: 'Show me all drivers' or 'How many orders were placed this week?'"}

    # ── Step 2: Follow-up detection ──────────────────────────────────────────
    is_followup = False
    if conversation_history:
        is_followup = detect_followup(nl_query, conversation_history)
    print(f"\n[STEP 2]   🔗 Follow-up detection : {'YES' if is_followup else 'NO'}")

    # ── Step 3: Redis cache (skip lookup if follow-up) ────────────────────────
    cache_hit_entry = None
    print(f"\n[STEP 3]   🗃️  Redis Cache Check")
    if not CACHE_ENABLED:
        print(f"           ⏭️  SKIPPED — cache is DISABLED")
    elif is_followup:
        print(f"           ⏭️  SKIPPED — follow-up query, context may differ")
    else:
        cache_hit_entry = find_similar_cache(query_embedding)
        if cache_hit_entry:
            print(f"           ✅ CACHE HIT — '{cache_hit_entry.get('question', '')}'")
        else:
            print(f"           ❌ CACHE MISS")

    if cache_hit_entry:
        return {
            "ok": True,
            "sql": cache_hit_entry["sql"],
            "retrieved_tables": [],
            "is_followup": False,
            "query_embedding": query_embedding,
            "cache_hit": True,
        }

    # ── Step 4: Pinecone search ───────────────────────────────────────────────
    print(f"\n[STEP 4]   🌲 Searching Pinecone for relevant tables...")
    matches = search_similar(query_embedding, top_k=top_k)
    if not matches:
        return {"ok": False, "error": "⚠️ No relevant tables found for your query. Please try rephrasing your question."}

    PINECONE_SIMILARITY_THRESHOLD = 0.35
    strong_matches = [m for m in matches if m["score"] >= PINECONE_SIMILARITY_THRESHOLD]
    print(f"           └─ Total matches  : {len(matches)}")
    print(f"           └─ Strong matches : {len(strong_matches)} (score >= {PINECONE_SIMILARITY_THRESHOLD})")

    if not strong_matches:
        previous_tables = None
        if conversation_history:
            for turn in reversed(conversation_history):
                if turn.get("retrieved_tables"):
                    previous_tables = turn["retrieved_tables"]
                    break

        if previous_tables:
            print(f"           ⚠️  Falling back to previous turn tables : {previous_tables}")
            matches = fetch_schemas_by_ids(previous_tables, [])
            if not matches:
                return {"ok": False, "error": "⚠️ Could not retrieve previous table schemas. Please rephrase your question."}
            is_followup = True
        else:
            best_score = matches[0]["score"]
            return {"ok": False, "error": "🗄️ I couldn't find any relevant tables for your question. Please ask about data that exists in your database."}
    else:
        matches = strong_matches

    already_fetched_ids = [m["id"] for m in matches]
    related_ids = extract_related_table_ids(matches)
    extra_matches = fetch_schemas_by_ids(related_ids, already_fetched_ids)
    all_matches = matches + extra_matches
    retrieved_tables = [m["id"] for m in all_matches]
    schema_context = build_schema_context(all_matches)
    print(f"           └─ Final tables for LLM : {retrieved_tables}")

    # ── Step 5: Generate SQL ──────────────────────────────────────────────────
    print(f"\n[STEP 5]   🤖 Generating SQL with Groq LLM...")
    llm_result = generate_sql(
        nl_query,
        schema_context,
        conversation_history=conversation_history if is_followup else None
    )
    if llm_result["status"] != "success":
        return {"ok": False, "error": "⚠️ I couldn't generate a valid query for your request. Please try rephrasing your question."}

    sql = llm_result["sql"]
    print(f"           ✅ SQL generated : {sql[:100]}{'...' if len(sql) > 100 else ''}")

    if is_destructive_sql(sql):
        return {"ok": False, "error": "🚫 This assistant is read-only. Queries that delete, update, insert, or modify data are not allowed."}

    # Cache write — store ALL successful queries (follow-up or not)
    print(f"\n[CACHE]    💾 Cache Write Check")
    if not CACHE_ENABLED:
        print(f"           ⏭️  SKIPPED — cache is DISABLED")
    else:
        stored = store_in_cache(question=nl_query, embedding=query_embedding, sql=sql)
        print(f"           {'✅ STORED' if stored else '⏭️  SKIPPED (duplicate)'}")

    return {
        "ok": True,
        "sql": sql,
        "retrieved_tables": retrieved_tables,
        "is_followup": is_followup,
        "query_embedding": query_embedding,
        "cache_hit": False,
    }


# =============================================================================
# Original blocking pipeline (unchanged — kept for /query endpoint)
# =============================================================================

def run_pipeline(nl_query: str, top_k: int = 10, conversation_history: list = None) -> dict:
    try:
        print("\n" + "="*60)
        print(f"🚀 PIPELINE STARTED")
        print(f"   Query : {nl_query}")
        print(f"   Cache : {'ENABLED' if CACHE_ENABLED else 'DISABLED'}")
        print("="*60)

        prep = _run_steps_1_to_5(nl_query, top_k, conversation_history)
        if not prep["ok"]:
            return {"status": "error", "message": prep["error"]}

        sql              = prep["sql"]
        retrieved_tables = prep["retrieved_tables"]
        is_followup      = prep["is_followup"]

        # ── Step 6: Execute SQL ───────────────────────────────────────────────
        print(f"\n[STEP 6]   🗄️  Executing SQL on database...")
        db_result = execute_query(sql)
        if db_result["status"] != "success":
            raw_msg = db_result.get("message", "")
            print(f"           ❌ DB execution FAILED : {raw_msg}")
            if any(code in raw_msg for code in ["42000", "42S02", "42S22"]):
                return {"status": "error", "message": "⚠️ I couldn't generate a valid query for your request. Please try rephrasing your question."}
            if "permission" in raw_msg.lower() or "access" in raw_msg.lower():
                return {"status": "error", "message": "🔒 You don't have permission to access this data. Please contact your administrator."}
            return {"status": "error", "message": "⚠️ Something went wrong while running your query. Please try again or rephrase your question."}

        columns      = db_result["columns"]
        all_rows     = db_result["rows"]
        display_rows = all_rows[:10]
        total_rows   = len(all_rows)
        print(f"           ✅ Executed — {total_rows} row(s) returned, {len(columns)} column(s)")

        # ── Step 7: Generate summary ──────────────────────────────────────────
        print(f"\n[STEP 7]   📝 Generating summary...")
        summary_result = generate_summary(nl_query, sql, columns, display_rows)
        summary = (
            summary_result.get("summary", "Query executed successfully.")
            if summary_result["status"] == "success"
            else "Query executed successfully."
        )
        print(f"           ✅ Summary generated.")

        csv_path = None
        if total_rows > 10:
            safe_name = "".join(c if c.isalnum() else "_" for c in nl_query[:30])
            csv_path = save_csv(columns, all_rows, f"{safe_name}.csv")
            print(f"\n[STEP 8]   📁 CSV exported : {csv_path}")

        print(f"\n✅ PIPELINE COMPLETE")
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
        return {"status": "error", "message": "⚠️ Something went wrong while processing your request. Please try again."}


# =============================================================================
# NEW: Streaming pipeline — Steps 6 & 7 run in parallel via SSE
# =============================================================================

async def run_pipeline_streaming(nl_query: str, top_k: int = 10, conversation_history: list = None):
    """
    Async generator that yields SSE-formatted strings.

    Event sequence:
      data: {"event":"result",  "data":{...db fields...}}   ← emitted right after DB finishes
      data: {"event":"summary", "data":{"summary":"..."}}   ← emitted when LLM summary is ready
      data: {"event":"done",    "data":{}}
      data: {"event":"error",   "data":{"message":"..."}}   ← on any failure
    """
    import json

    def _emit(event: str, data: dict) -> str:
        def _serializer(obj):
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        return f"data: {json.dumps({'event': event, 'data': data}, default=_serializer)}\n\n"

    try:
        print("\n" + "="*60)
        print(f"🚀 PIPELINE (STREAMING) STARTED")
        print(f"   Query : {nl_query}")
        print("="*60)

        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=2)

        # ── Steps 1-5: run in a thread so we don't block the event loop ──────
        prep = await loop.run_in_executor(
            executor, _run_steps_1_to_5, nl_query, top_k, conversation_history
        )

        if not prep["ok"]:
            yield _emit("error", {"message": prep["error"]})
            executor.shutdown(wait=False)
            return

        sql              = prep["sql"]
        retrieved_tables = prep["retrieved_tables"]
        is_followup      = prep["is_followup"]

        # ── Step 6: Execute SQL ───────────────────────────────────────────────
        print(f"\n[STEP 6]   🗄️  Executing SQL on database...")
        db_result = await loop.run_in_executor(executor, execute_query, sql)

        if db_result["status"] != "success":
            raw_msg = db_result.get("message", "")
            print(f"           ❌ DB execution FAILED : {raw_msg}")
            if any(code in raw_msg for code in ["42000", "42S02", "42S22"]):
                yield _emit("error", {"message": "⚠️ I couldn't generate a valid query. Please rephrase."})
            elif "permission" in raw_msg.lower() or "access" in raw_msg.lower():
                yield _emit("error", {"message": "🔒 Permission denied. Please contact your administrator."})
            else:
                yield _emit("error", {"message": "⚠️ Something went wrong. Please try again."})
            executor.shutdown(wait=False)
            return

        columns      = db_result["columns"]
        all_rows     = db_result["rows"]
        display_rows = all_rows[:10]
        total_rows   = len(all_rows)
        print(f"           ✅ Executed — {total_rows} row(s) returned, {len(columns)} column(s)")

        # ── Step 7: Kick off summary generation IN THE BACKGROUND ────────────
        # We start the summary task NOW (passing in the rows we just got),
        # then IMMEDIATELY yield the DB result to the frontend so it can
        # render the table without waiting for the LLM.
        print(f"\n[STEP 7]   📝 Generating summary in background...")
        summary_future = loop.run_in_executor(
            executor, generate_summary, nl_query, sql, columns, display_rows
        )

        # ── Yield DB result right away ────────────────────────────────────────
        csv_path = None
        if total_rows > 10:
            safe_name = "".join(c if c.isalnum() else "_" for c in nl_query[:30])
            csv_path = save_csv(columns, all_rows, f"{safe_name}.csv")

        yield _emit("result", {
            "status": "success",
            "nl_query": nl_query,
            "sql": sql,
            "retrieved_tables": retrieved_tables,
            "columns": columns,
            "rows": display_rows,
            "all_rows": all_rows,
            "total_row_count": total_rows,
            "is_followup": is_followup,
            "csv_path": csv_path,
        })

        # ── Now wait for summary and yield it separately ───────────────────────
        summary_result = await summary_future
        summary = (
            summary_result.get("summary", "Query executed successfully.")
            if summary_result["status"] == "success"
            else "Query executed successfully."
        )
        print(f"           ✅ Summary generated.")

        yield _emit("summary", {"summary": summary})
        yield _emit("done", {})

        print(f"\n✅ STREAMING PIPELINE COMPLETE")
        print("="*60 + "\n")

    except Exception as e:
        logger.error(f"Streaming pipeline failed for query '{nl_query}': {e}", exc_info=True)
        print(f"\n❌ STREAMING PIPELINE ERROR: {e}")
        if 'sql' in locals():
            print(f"   SQL that caused the error:\n{sql}")
        yield _emit("error", {"message": "⚠️ Something went wrong while processing your request. Please try again."})
    finally:
        executor.shutdown(wait=False)