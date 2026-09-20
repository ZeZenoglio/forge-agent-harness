"""Auth endpoints (REQ-033, REQ-035, REQ-036, REQ-048).

Handles token exchange, verification, user session management, and social auth profile sync.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.models import Session as UserSession
from backend.db.session import get_db
from backend.dependencies import get_current_user_claims
from backend.services.auth_service import (
    decode_jwt_token,
    revoke_user_session,
    sync_user_from_claims,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_db_dep = Depends(get_db)
_claims_dep = Depends(get_current_user_claims)


class TokenVerifyRequest(BaseModel):
    token: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/verify")
def verify_token(req: TokenVerifyRequest, db: Session = _db_dep) -> dict[str, Any]:
    """Verify an Authentik JWT token and sync the user locally (REQ-035)."""
    try:
        claims = decode_jwt_token(req.token)
        user = sync_user_from_claims(db, claims)
        return {
            "data": {
                "valid": True,
                "user_id": user.id,
                "email": user.email,
                "name": user.name,
                "provider": user.provider,
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/refresh")
def refresh_token(req: RefreshRequest, db: Session = _db_dep) -> dict[str, Any]:
    """Simulate or process token refresh and sync profile changes (REQ-048 AC 5)."""
    try:
        claims = decode_jwt_token(req.refresh_token)
        user = sync_user_from_claims(db, claims)
        return {
            "data": {
                "access_token": req.refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "avatar_url": user.avatar_url,
                },
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/me")
def get_auth_me(
    claims: dict[str, Any] = _claims_dep,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """Return authenticated user profile and synchronize claims."""
    if claims.get("sub") == "anonymous_user":
        return {
            "data": {
                "id": "anonymous_user",
                "email": "anonymous@forge.local",
                "name": "Anonymous",
                "provider": "local",
            }
        }
    user = sync_user_from_claims(db, claims)
    return {
        "data": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "provider": user.provider,
        }
    }


@router.get("/sessions")
def list_sessions(
    claims: dict[str, Any] = _claims_dep,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """List active sessions for the current user (REQ-048 AC 3)."""
    user_id = claims.get("sub", "anonymous_user")
    sessions = db.query(UserSession).filter(UserSession.user_id == user_id).all()
    return {
        "data": [
            {
                "id": s.id,
                "user_id": s.user_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            }
            for s in sessions
        ]
    }


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: str,
    claims: dict[str, Any] = _claims_dep,
    db: Session = _db_dep,
) -> dict[str, Any]:
    """Revoke an active user session (REQ-048 AC 3)."""
    revoked = revoke_user_session(db, session_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"data": {"revoked": True}}
