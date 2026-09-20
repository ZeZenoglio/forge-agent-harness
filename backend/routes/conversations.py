"""Conversation management endpoints (REQ-033)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.models import Conversation
from backend.db.session import get_db
from backend.dependencies import get_current_user_claims

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])

_db_dep = Depends(get_db)
_claims_dep = Depends(get_current_user_claims)


class CreateConversationRequest(BaseModel):
    title: str = "New Conversation"


@router.get("")
def list_conversations(
    claims: dict[str, Any] = _claims_dep,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """List conversations for the current authenticated user."""
    user_id = claims.get("sub", "anonymous_user")
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return {
        "data": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in conversations
        ]
    }


@router.post("", status_code=201)
def create_conversation(
    payload: CreateConversationRequest,
    claims: dict[str, Any] = _claims_dep,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """Create a new conversation."""
    user_id = claims.get("sub", "anonymous_user")
    conv = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=payload.title,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {
        "data": {
            "id": conv.id,
            "title": conv.title,
            "user_id": conv.user_id,
            "created_at": conv.created_at.isoformat(),
        }
    }


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """Retrieve conversation details and its messages."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "data": {
            "id": conv.id,
            "title": conv.title,
            "user_id": conv.user_id,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in conv.messages
            ],
        }
    }


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """Delete a conversation."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"data": {"deleted": True, "id": conversation_id}}
