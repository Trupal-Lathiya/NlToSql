from fastapi import APIRouter
from models.schemas import QueryRequest, QueryResponse
from services.query_pipeline import run_pipeline
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