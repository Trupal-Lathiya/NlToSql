import logging
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_CLASSIFIER_MODEL
from utils.prompt_templates import (
    SYSTEM_PROMPT,
    SQL_GENERATION_PROMPT,
    SQL_GENERATION_WITH_MEMORY_PROMPT,
    FOLLOWUP_DETECTION_PROMPT,
    RESPONSE_SUMMARY_PROMPT,
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


def generate_sql(nl_query: str, schema_context: str, conversation_history: list = None) -> dict:
    try:
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
                {"role": "system", "content": SYSTEM_PROMPT},
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