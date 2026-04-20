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
from services.embedding_service import embed_text
from services.pinecone_service import search_similar
from services.llm_service import generate_sql, generate_summary
from services.database_service import execute_query
from utils.prompt_templates import RELEVANCE_CHECK_PROMPT
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

CSV_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "exports")


def classify_query(nl_query: str) -> str:
    """
    Returns: 'ALLOWED', 'BLOCKED_DESTRUCTIVE', or 'BLOCKED_IRRELEVANT'
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)
        prompt = RELEVANCE_CHECK_PROMPT.format(nl_query=nl_query)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10
        )
        answer = response.choices[0].message.content.strip().upper()
        logger.info(f"Query classification for '{nl_query}': {answer}")

        if "BLOCKED_DESTRUCTIVE" in answer:
            return "BLOCKED_DESTRUCTIVE"
        elif "BLOCKED_IRRELEVANT" in answer:
            return "BLOCKED_IRRELEVANT"
        else:
            return "ALLOWED"

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return "ALLOWED"  # Fail open


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


def run_pipeline(nl_query: str, top_k: int = 10) -> dict:
    try:
        # ── Step 0: Classify the query ──────────────────────────────────
        logger.info(f"Classifying query: {nl_query}")
        classification = classify_query(nl_query)

        if classification == "BLOCKED_DESTRUCTIVE":
            return {
                "status": "error",
                "message": "🚫 This assistant is read-only. Queries that delete, update, insert, or modify data are not allowed."
            }

        if classification == "BLOCKED_IRRELEVANT":
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
            return {"status": "error", "message": "No relevant tables found in Pinecone."}

        retrieved_tables = [m["id"] for m in matches]
        logger.info(f"Retrieved tables: {retrieved_tables}")

        # ── Step 3: Build schema context for LLM ───────────────────────
        schema_context = build_schema_context(matches)

        # ── Step 4: Generate SQL using Groq LLM ────────────────────────
        logger.info("Generating SQL with Groq...")
        llm_result = generate_sql(nl_query, schema_context)
        if llm_result["status"] != "success":
            return llm_result

        sql = llm_result["sql"]

        # ── Step 5: Hard block destructive SQL even if LLM slips ───────
        blocked_keywords = ["DELETE", "DROP", "TRUNCATE", "ALTER", "INSERT", "UPDATE"]
        sql_upper = sql.upper()
        if any(kw in sql_upper for kw in blocked_keywords):
            logger.warning(f"LLM generated destructive SQL despite classification: {sql}")
            return {
                "status": "error",
                "message": "🚫 This assistant is read-only. The generated query contains a restricted operation."
            }

        # ── Step 6: Execute SQL on SQL Server ──────────────────────────
        logger.info(f"Executing SQL: {sql}")
        db_result = execute_query(sql)
        if db_result["status"] != "success":
            return db_result

        columns = db_result["columns"]
        rows = db_result["rows"]
        total_rows = len(rows)

        # ── Step 7: Generate human-friendly summary ─────────────────────
        logger.info("Generating summary...")
        summary_result = generate_summary(nl_query, sql, columns, rows)
        summary = summary_result.get("summary", "Query executed successfully.") \
            if summary_result["status"] == "success" else "Query executed successfully."

        # ── Step 8: Save CSV if rows > 10 ──────────────────────────────
        csv_path = None
        if total_rows > 10:
            safe_name = "".join(c if c.isalnum() else "_" for c in nl_query[:30])
            csv_path = save_csv(columns, rows, f"{safe_name}.csv")

        return {
            "status": "success",
            "nl_query": nl_query,
            "sql": sql,
            "retrieved_tables": retrieved_tables,
            "columns": columns,
            "rows": rows[:10],
            "total_row_count": total_rows,
            "summary": summary,
            "csv_path": csv_path
        }

    except Exception as e:
        logger.error(f"Pipeline failed for query '{nl_query}': {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Could not process your query. Error: {str(e)}"
        }