"""Message management endpoints (REQ-033)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.models import Conversation, Message
from backend.db.session import get_db

router = APIRouter(
    prefix="/api/v1/conversations/{conversation_id}/messages", tags=["messages"]
)

_db_dep = Depends(get_db)


class CreateMessageRequest(BaseModel):
    role: str = "user"
    content: str


@router.get("")
def list_messages(
    conversation_id: str,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """List messages for a specific conversation."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return {
        "data": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]
    }


@router.post("", status_code=201)
def add_message(
    conversation_id: str,
    payload: CreateMessageRequest,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """Append a message to a conversation."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=payload.role,
        content=payload.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "data": {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
    }
