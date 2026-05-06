import json
import logging
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_CLASSIFIER_MODEL
from utils.prompt_templates import (
    build_system_prompt,
    SQL_GENERATION_PROMPT,
    SQL_GENERATION_WITH_MEMORY_PROMPT,
    SQL_RETRY_PROMPT,
    FOLLOWUP_DETECTION_PROMPT,
    RESPONSE_SUMMARY_PROMPT,
    FOLLOWUP_QUESTIONS_PROMPT,
)

logger = logging.getLogger(__name__)
_client = None


def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def detect_followup(nl_query: str, conversation_history: list) -> bool:
    """Returns True if the new query is a follow-up to previous queries."""
    if not conversation_history:
        return False
    try:
        history_text = "\n".join(
            [f"Q{i+1}: {t.get('nl_query', '')}" for i, t in enumerate(conversation_history)]
        )
        prompt = FOLLOWUP_DETECTION_PROMPT.format(
            conversation_history=history_text,
            nl_query=nl_query
        )
        response = get_client().chat.completions.create(
            model=GROQ_CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10
        )
        answer = response.choices[0].message.content.strip().upper()
        logger.info(f"Follow-up detection for '{nl_query}': {answer}")
        return answer.startswith("FOLLOW")
    except Exception as e:
        logger.error(f"Follow-up detection failed: {e}")
        return False


def generate_sql(
    nl_query: str,
    schema_context: str,
    conversation_history: list = None,
    user_id: str = None,
    customer_id: int = None,
) -> dict:
    """
    Generate SQL for the given NL query.

    When user_id / customer_id are provided, the system prompt is extended
    with multitenancy rules so the LLM always scopes the query to the
    correct tenant (user + customer).
    """
    try:
        # Build the system prompt — includes tenant rules when IDs are present
        system = build_system_prompt(user_id=user_id, customer_id=customer_id)

        if conversation_history and len(conversation_history) > 0:
            history_text = ""
            for i, turn in enumerate(conversation_history, 1):
                history_text += f"Q{i}: {turn.get('nl_query', '')}\n"
                if turn.get('sql'):
                    history_text += f"SQL{i}: {turn.get('sql', '')}\n"
                history_text += "\n"

            prompt = SQL_GENERATION_WITH_MEMORY_PROMPT.format(
                schema_context=schema_context,
                history_count=len(conversation_history),
                conversation_history=history_text.strip(),
                nl_query=nl_query
            )
        else:
            prompt = SQL_GENERATION_PROMPT.format(
                schema_context=schema_context,
                nl_query=nl_query
            )

        response = get_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1024
        )

        sql = response.choices[0].message.content.strip()

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


def generate_sql_retry(
    nl_query: str,
    schema_context: str,
    failed_sql: str,
    error_message: str,
    attempt: int,
    user_id: str = None,
    customer_id: int = None,
) -> dict:
    """
    Ask the LLM to self-correct a previously generated SQL query that failed
    on execution. Preserves tenant-scoping in corrected query.
    """
    try:
        system = build_system_prompt(user_id=user_id, customer_id=customer_id)
        truncated_error = error_message[:800] if len(error_message) > 800 else error_message

        prompt = SQL_RETRY_PROMPT.format(
            nl_query=nl_query,
            schema_context=schema_context,
            failed_sql=failed_sql,
            error_message=truncated_error,
            attempt=attempt,
        )

        logger.info(f"[RETRY {attempt}] Asking LLM to self-correct SQL...")
        print(f"           🔄 Retry attempt {attempt} — sending error back to LLM...")

        response = get_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
        )

        sql = response.choices[0].message.content.strip()

        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.lower().startswith("sql"):
                sql = sql[3:]
            sql = sql.strip()

        if sql == "CANNOT_GENERATE":
            logger.warning(f"[RETRY {attempt}] LLM returned CANNOT_GENERATE")
            return {"status": "error", "message": "LLM could not fix the query based on the schema."}

        logger.info(f"[RETRY {attempt}] Corrected SQL: {sql[:120]}{'...' if len(sql) > 120 else ''}")
        print(f"           ✅ Retry {attempt} SQL: {sql[:100]}{'...' if len(sql) > 100 else ''}")
        return {"status": "success", "sql": sql}

    except Exception as e:
        logger.error(f"[RETRY {attempt}] LLM retry generation failed: {e}")
        return {"status": "error", "message": str(e)}


def generate_summary(nl_query: str, sql: str, columns: list, rows: list) -> dict:
    try:
        total_count = len(rows)
        preview_rows = rows[:10]
        preview_count = len(preview_rows)

        rows_text = "\n".join(
            [str(dict(zip(columns, row))) for row in preview_rows]
        )

        csv_note = (
            f"Note: Only the first 10 rows are shown. Full {total_count} rows available in CSV."
            if total_count > 10 else ""
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
            model=GROQ_CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )

        summary = response.choices[0].message.content.strip()
        return {"status": "success", "summary": summary}

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return {"status": "error", "message": str(e)}


def generate_followup_questions(
    nl_query: str,
    retrieved_tables: list,
    summary: str,
    columns: list,
) -> list:
    """
    Given context from the previous query, returns 3 follow-up question strings.
    Falls back to an empty list on any failure.
    """
    try:
        prompt = FOLLOWUP_QUESTIONS_PROMPT.format(
            nl_query=nl_query,
            retrieved_tables=", ".join(retrieved_tables),
            summary=summary,
            columns=", ".join(columns),
        )

        response = get_client().chat.completions.create(
            model=GROQ_CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=200,
        )

        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.lower().startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        questions = json.loads(raw)

        if isinstance(questions, list):
            questions = [q for q in questions if isinstance(q, str)][:3]
            logger.info(f"Generated follow-up questions: {questions}")
            return questions

        return []

    except Exception as e:
        logger.error(f"Follow-up question generation failed: {e}")
        return []