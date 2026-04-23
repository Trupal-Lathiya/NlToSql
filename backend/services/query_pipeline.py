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
from services.embedding_service import embed_text
from services.pinecone_service import search_similar
from services.llm_service import generate_sql, generate_summary
from services.database_service import execute_query
from utils.prompt_templates import RELEVANCE_CHECK_PROMPT
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_CLASSIFIER_MODEL

logger = logging.getLogger(__name__)

CSV_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "exports")

# SQL-level hard block — catches anything the LLM classifier missed
BLOCKED_SQL_KEYWORDS = [
    r'\bDELETE\b', r'\bDROP\b', r'\bTRUNCATE\b', r'\bALTER\b',
    r'\bINSERT\b', r'\bUPDATE\b', r'\bMERGE\b', r'\bEXEC\b',
    r'\bEXECUTE\b', r'\bCREATE\b', r'\bREPLACE\b',
]


def classify_query(nl_query: str) -> str:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        prompt = RELEVANCE_CHECK_PROMPT.format(nl_query=nl_query)
        response = client.chat.completions.create(
            model=GROQ_CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=20
        )
        answer = response.choices[0].message.content.strip().upper()
        answer = answer.strip(".\n\r ")
        logger.info(f"Query classification for '{nl_query}': {answer}")
        print(f"Query classification for '{nl_query}': {answer}")

        # Use startswith — handles truncated responses like "BLOCK" or "BLOCKED_D"
        if answer.startswith("BLOCKED_D"):
            return "BLOCKED_DESTRUCTIVE"
        elif answer.startswith("BLOCKED_I"):
            return "BLOCKED_IRRELEVANT"
        elif answer.startswith("BLOCK"):
            # Ambiguous — re-check the query text itself for safety
            destructive_words = ["delete", "drop", "truncate", "alter", "insert", "update", "remove", "merge"]
            if any(w in nl_query.lower() for w in destructive_words):
                return "BLOCKED_DESTRUCTIVE"
            return "BLOCKED_IRRELEVANT"
        elif answer.startswith("ALLOW") or answer == "":
            # Empty string or ALLOW* — treat as ALLOWED
            # Empty can happen when the model is confident it's a DB query and responds minimally
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
    """
    from services.pinecone_service import get_index

    missing = [t for t in table_ids if t not in already_fetched_ids]
    if not missing:
        return []

    index = get_index()
    extra = []

    for table_id in missing:
        try:
            result = index.fetch(ids=[table_id])
            vectors = result.get("vectors", {})
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
            logger.error(f"Failed to fetch schema for '{table_id}': {e}")

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
        # ── Step 0: LLM Classifier — FIRST gate, runs before everything ─
        logger.info(f"Classifying query: {nl_query}")
        classification = classify_query(nl_query)

        if classification == "BLOCKED_DESTRUCTIVE":
            logger.warning(f"Blocked destructive query: {nl_query}")
            return {
                "status": "error",
                "message": "🚫 This assistant is read-only. Queries that delete, update, insert, or modify data are not allowed."
            }

        if classification == "BLOCKED_IRRELEVANT":
            logger.info(f"Blocked irrelevant query: {nl_query}")
            return {
                "status": "error",
                "message": "🗄️ Please ask a question related to your database — for example: 'Show me all drivers' or 'How many orders were placed this week?'"
            }

        # ── Step 1: Embed the NL query ──────────────────────────────────
        logger.info(f"Embedding query: {nl_query}")
        query_embedding = embed_text(nl_query)

        # ── Step 2: Search Pinecone for relevant schemas ────────────────
        logger.info("Searching Pinecone for relevant tables...")
        matches = search_similar(query_embedding, top_k=top_k)
        if not matches:
            return {
                "status": "error",
                "message": "⚠️ No relevant tables found for your query. Please try rephrasing your question."
            }

        # ── NEW: Filter out low-confidence matches ──────────────────────
        SIMILARITY_THRESHOLD = 0.45
        strong_matches = [m for m in matches if m["score"] >= SIMILARITY_THRESHOLD]
        if not strong_matches:
            best_score = matches[0]["score"]
            logger.warning(f"All matches below threshold. Best score: {best_score:.3f}")
            return {
                "status": "error",
                "message": "🗄️ I couldn't find any relevant tables for your question. Your database may not contain data related to this topic. Please ask about data that exists in your database."
            }
        matches = strong_matches

        already_fetched_ids = [m["id"] for m in matches]
        logger.info(f"Directly matched tables: {already_fetched_ids}")

        # ── Step 3: Auto-fetch FK-related tables missing from results ───
        related_ids = extract_related_table_ids(matches)
        logger.info(f"FK-related tables detected: {related_ids}")

        extra_matches = fetch_schemas_by_ids(related_ids, already_fetched_ids)
        all_matches = matches + extra_matches

        retrieved_tables = [m["id"] for m in all_matches]
        logger.info(f"Final tables sent to LLM: {retrieved_tables}")

        # ── Step 4: Build schema context for LLM ───────────────────────
        schema_context = build_schema_context(all_matches)

        # ── Step 5: Generate SQL using Groq LLM ────────────────────────
        logger.info("Generating SQL with Groq...")
        llm_result = generate_sql(nl_query, schema_context)
        if llm_result["status"] != "success":
            return {
                "status": "error",
                "message": "⚠️ I couldn't generate a valid query for your request. Please try rephrasing your question."
            }

        sql = llm_result["sql"]

        # ── Step 6: Hard block destructive SQL even if LLM slips ───────
        if is_destructive_sql(sql):
            logger.warning(f"LLM generated destructive SQL despite classification: {sql}")
            return {
                "status": "error",
                "message": "🚫 This assistant is read-only. Queries that delete, update, insert, or modify data are not allowed."
            }

        # ── Step 7: Execute SQL on SQL Server ──────────────────────────
        logger.info(f"Executing SQL: {sql}")
        db_result = execute_query(sql)
        if db_result["status"] != "success":
            raw_msg = db_result.get("message", "")
            logger.error(f"DB execution error: {raw_msg}")

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

        # ── Step 8: Generate human-friendly summary ─────────────────────
        logger.info("Generating summary...")
        summary_result = generate_summary(nl_query, sql, columns, display_rows)
        summary = (
            summary_result.get("summary", "Query executed successfully.")
            if summary_result["status"] == "success"
            else "Query executed successfully."
        )

        # ── Step 9: Save CSV if rows > 10 ──────────────────────────────
        csv_path = None
        if total_rows > 10:
            safe_name = "".join(c if c.isalnum() else "_" for c in nl_query[:30])
            csv_path = save_csv(columns, all_rows, f"{safe_name}.csv")

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
            "csv_path": csv_path
        }

    except Exception as e:
        logger.error(f"Pipeline failed for query '{nl_query}': {e}", exc_info=True)
        return {
            "status": "error",
            "message": "⚠️ Something went wrong while processing your request. Please try again."
        }