# =============================================================================
# services/llm_service.py - Groq LLM Service for SQL Generation
# =============================================================================
# This file handles communication with the Groq LLM API to generate SQL:
#   - Constructs a prompt combining the user's natural language query with
#     the relevant table schemas retrieved from Pinecone.
#   - Sends the prompt to the Groq API (e.g., using llama3-70b model).
#   - Parses the LLM response to extract the clean SQL query.
#   - Includes prompt engineering logic to ensure the LLM generates
#     valid T-SQL syntax compatible with SQL Server.
#   - Handles error cases like malformed responses or API failures.
# =============================================================================


import logging
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from utils.prompt_templates import SYSTEM_PROMPT, SQL_GENERATION_PROMPT, RESPONSE_SUMMARY_PROMPT

logger = logging.getLogger(__name__)
_client = None

def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client

def generate_sql(nl_query: str, schema_context: str) -> dict:
    try:
        prompt = SQL_GENERATION_PROMPT.format(
            schema_context=schema_context,
            nl_query=nl_query
        )

        response = get_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1024
        )

        sql = response.choices[0].message.content.strip()

        # Clean up if model wraps in markdown
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.lower().startswith("sql"):
                sql = sql[3:]
            sql = sql.strip()

        if sql == "CANNOT_GENERATE":
            return {"status": "error", "message": "Could not generate SQL for this query."}

        logger.info(f"Generated SQL: {sql}")
        return {"status": "success", "sql": sql}

    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return {"status": "error", "message": str(e)}


def generate_summary(nl_query: str, sql: str, columns: list, rows: list) -> dict:
    try:
        total_count = len(rows)
        preview_rows = rows[:10]
        preview_count = len(preview_rows)

        # Format rows as readable table text
        rows_text = "\n".join(
            [str(dict(zip(columns, row))) for row in preview_rows]
        )

        csv_note = (
            f"Note: Only the first 10 rows are shown here. The full {total_count} rows are available in the CSV download."
            if total_count > 10
            else ""
        )

        prompt = RESPONSE_SUMMARY_PROMPT.format(
            nl_query=nl_query,
            sql=sql,
            preview_count=preview_count,
            total_count=total_count,
            columns=", ".join(columns),
            rows_preview=rows_text,
            csv_note=csv_note
        )

        response = get_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1024
        )

        summary = response.choices[0].message.content.strip()
        logger.info("Summary generated successfully.")
        return {"status": "success", "summary": summary}

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return {"status": "error", "message": str(e)}