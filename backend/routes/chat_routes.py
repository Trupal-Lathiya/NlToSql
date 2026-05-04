"""
backend/routes/chat_routes.py
──────────────────────────────
Manages Conversations and Messages tables.

DB Tables required (run once in your SQL Server):

    CREATE TABLE NL2SQL_Conversations (
        ConversationId  UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        UserId          NVARCHAR(450)    NOT NULL,
        Title           NVARCHAR(500)    NOT NULL DEFAULT 'New Chat',
        CreatedAt       DATETIME2        NOT NULL DEFAULT GETUTCDATE(),
        UpdatedAt       DATETIME2        NOT NULL DEFAULT GETUTCDATE()
    );

    CREATE TABLE NL2SQL_Messages (
        MessageId       UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        ConversationId  UNIQUEIDENTIFIER NOT NULL REFERENCES NL2SQL_Conversations(ConversationId) ON DELETE CASCADE,
        NLQuery         NVARCHAR(MAX)    NOT NULL,
        GeneratedSQL    NVARCHAR(MAX)    NULL,
        Summary         NVARCHAR(MAX)    NULL,
        RetrievedTables NVARCHAR(MAX)    NULL,
        Columns         NVARCHAR(MAX)    NULL,
        Rows            NVARCHAR(MAX)    NULL,
        TotalRowCount   INT              NULL,
        CreatedAt       DATETIME2        NOT NULL DEFAULT GETUTCDATE()
    );
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from services.database_service import get_connection

router = APIRouter(prefix="/chats", tags=["Chats"])
logger = logging.getLogger(__name__)


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    user_id: str

class RenameConversationRequest(BaseModel):
    title: str

class SaveMessageRequest(BaseModel):
    conversation_id: str
    nl_query: str
    generated_sql: Optional[str] = None
    summary: Optional[str] = None
    retrieved_tables: Optional[List[str]] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[list]] = None
    total_row_count: Optional[int] = None


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_conn():
    return get_connection()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("")
def create_conversation(req: CreateConversationRequest):
    """Create a new conversation for a user. Returns the new conversation."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO NL2SQL_Conversations (UserId, Title)
            OUTPUT INSERTED.ConversationId, INSERTED.Title, INSERTED.CreatedAt, INSERTED.UpdatedAt
            VALUES (?, ?)
            """,
            (req.user_id, "New Chat"),
        )
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "conversation": {
                "id": str(row[0]),
                "title": row[1],
                "created_at": row[2].isoformat() if row[2] else None,
                "updated_at": row[3].isoformat() if row[3] else None,
                "message_count": 0,
            },
        }
    except Exception as e:
        logger.error(f"create_conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}")
def list_conversations(user_id: str):
    """Return all conversations for a user, newest first, with message count."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                C.ConversationId,
                C.Title,
                C.CreatedAt,
                C.UpdatedAt,
                COUNT(M.MessageId) AS MessageCount
            FROM NL2SQL_Conversations C
            LEFT JOIN NL2SQL_Messages M ON M.ConversationId = C.ConversationId
            WHERE C.UserId = ?
            GROUP BY C.ConversationId, C.Title, C.CreatedAt, C.UpdatedAt
            ORDER BY C.UpdatedAt DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        conversations = [
            {
                "id": str(r[0]),
                "title": r[1],
                "created_at": r[2].isoformat() if r[2] else None,
                "updated_at": r[3].isoformat() if r[3] else None,
                "message_count": r[4],
            }
            for r in rows
        ]
        return {"status": "success", "conversations": conversations}
    except Exception as e:
        logger.error(f"list_conversations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}/messages")
def get_messages(conversation_id: str):
    """Return all messages for a conversation, oldest first."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                MessageId, NLQuery, GeneratedSQL, Summary,
                RetrievedTables, Columns, Rows, TotalRowCount, CreatedAt
            FROM NL2SQL_Messages
            WHERE ConversationId = ?
            ORDER BY CreatedAt ASC
            """,
            (conversation_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        messages = []
        for r in rows:
            def _parse(val):
                if val is None:
                    return None
                try:
                    return json.loads(val)
                except Exception:
                    return val

            messages.append({
                "id": str(r[0]),
                "nl_query": r[1],
                "sql": r[2],
                "summary": r[3],
                "retrieved_tables": _parse(r[4]),
                "columns": _parse(r[5]),
                "rows": _parse(r[6]),
                "total_row_count": r[7],
                "created_at": r[8].isoformat() if r[8] else None,
                # Reconstruct status field for frontend compatibility
                "status": "success",
            })

        return {"status": "success", "messages": messages}
    except Exception as e:
        logger.error(f"get_messages error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages")
def save_message(req: SaveMessageRequest):
    """
    Save ONE successful message to a conversation.
    Also updates the conversation Title (first message only) and UpdatedAt.
    Only call this for SUCCESSFUL responses — errors must NOT be saved.
    """
    try:
        conn = _get_conn()
        cursor = conn.cursor()

        # ── Insert message ────────────────────────────────────────────────────
        cursor.execute(
            """
            INSERT INTO NL2SQL_Messages
                (ConversationId, NLQuery, GeneratedSQL, Summary, RetrievedTables, Columns, Rows, TotalRowCount)
            OUTPUT INSERTED.MessageId, INSERTED.CreatedAt
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req.conversation_id,
                req.nl_query,
                req.generated_sql,
                req.summary,
                json.dumps(req.retrieved_tables) if req.retrieved_tables is not None else None,
                json.dumps(req.columns) if req.columns is not None else None,
                json.dumps(req.rows) if req.rows is not None else None,
                req.total_row_count,
            ),
        )
        msg_row = cursor.fetchone()
        message_id = str(msg_row[0])
        created_at = msg_row[1].isoformat() if msg_row[1] else None

        # ── Update conversation UpdatedAt ─────────────────────────────────────
        cursor.execute(
            "UPDATE NL2SQL_Conversations SET UpdatedAt = GETUTCDATE() WHERE ConversationId = ?",
            (req.conversation_id,),
        )

        # ── Auto-set title from first message (first 80 chars of nl_query) ────
        cursor.execute(
            """
            UPDATE NL2SQL_Conversations
            SET Title = LEFT(?, 80)
            WHERE ConversationId = ?
              AND Title = 'New Chat'
            """,
            (req.nl_query, req.conversation_id),
        )

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message_id": message_id,
            "created_at": created_at,
        }
    except Exception as e:
        logger.error(f"save_message error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{conversation_id}/rename")
def rename_conversation(conversation_id: str, req: RenameConversationRequest):
    """Rename a conversation title."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE NL2SQL_Conversations SET Title = ?, UpdatedAt = GETUTCDATE() WHERE ConversationId = ?",
            (req.title.strip()[:80], conversation_id),
        )
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"rename_conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages (CASCADE)."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM NL2SQL_Conversations WHERE ConversationId = ?",
            (conversation_id,),
        )
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"delete_conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))