"""User management endpoints (REQ-033, REQ-048)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.models import User
from backend.db.session import get_db
from backend.dependencies import get_current_user_claims

router = APIRouter(prefix="/api/v1/users", tags=["users"])

_db_dep = Depends(get_db)
_claims_dep = Depends(get_current_user_claims)


class UserUpdateRequest(BaseModel):
    name: str | None = None
    avatar_url: str | None = None


@router.get("/me")
def get_current_user_profile(
    claims: dict[str, Any] = _claims_dep,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """Retrieve current user profile."""
    user_id = claims.get("sub", "anonymous_user")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Fallback if anonymous or not synced yet
        return {
            "data": {
                "id": user_id,
                "email": claims.get("email", "anonymous@forge.local"),
                "name": claims.get("name", "Anonymous"),
                "avatar_url": None,
                "provider": "local",
            }
        }
    return {
        "data": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "provider": user.provider,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }
    }


@router.put("/me")
def update_current_user_profile(
    payload: UserUpdateRequest,
    claims: dict[str, Any] = _claims_dep,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """Update profile information (REQ-048 AC 2)."""
    user_id = claims.get("sub", "anonymous_user")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.name is not None:
        user.name = payload.name
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url
    user.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(user)

    return {
        "data": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "updated_at": user.updated_at.isoformat(),
        }
    }


@router.get("/{user_id}")
def get_user_by_id(user_id: str, db: Session = _db_dep) -> dict[str, Any]:
    """Retrieve user details by user ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "data": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
        }
    }
