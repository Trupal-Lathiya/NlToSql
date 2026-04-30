from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from models.schemas import QueryRequest, QueryResponse
from services.query_pipeline import run_pipeline, run_pipeline_streaming
from services.llm_service import generate_followup_questions
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/query", tags=["Query"])


class FollowupRequest(BaseModel):
    nl_query: str
    retrieved_tables: List[str]
    summary: str
    columns: List[str]


class FollowupResponse(BaseModel):
    questions: List[str]


# ── IMPORTANT: specific sub-routes must be defined BEFORE the catch-all "" ──

@router.post("/followup-questions", response_model=FollowupResponse)
def get_followup_questions(request: FollowupRequest):
    """
    Given the previous query context (tables, summary, columns),
    returns 3 suggested follow-up questions the user might want to ask.
    """
    questions = generate_followup_questions(
        nl_query=request.nl_query,
        retrieved_tables=request.retrieved_tables,
        summary=request.summary,
        columns=request.columns,
    )
    return {"questions": questions}


@router.post("/stream")
async def handle_query_stream(request: QueryRequest):
    """
    Streaming variant of /query using Server-Sent Events (SSE).

    Yields events as: data: {"event": "...", "data": {...}}\n\n

    Event types:
      result  — DB rows ready (sent immediately after SQL executes)
      summary — LLM summary ready (sent when summary generation finishes)
      done    — stream complete
      error   — something went wrong
    """
    async def event_generator():
        async for chunk in run_pipeline_streaming(
            nl_query=request.natural_language_query,
            conversation_history=[turn.dict() for turn in (request.conversation_history or [])]
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables nginx buffering if behind a proxy
        }
    )


@router.post("", response_model=QueryResponse)
def handle_query(request: QueryRequest):
    """
    Accepts natural language query + optional conversation history,
    returns SQL + results or error.
    """
    result = run_pipeline(
        nl_query=request.natural_language_query,
        conversation_history=[turn.dict() for turn in (request.conversation_history or [])]
    )
    return result