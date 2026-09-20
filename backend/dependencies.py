from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.services.auth_service import (
    AuthError,
    decode_jwt_token,
    sync_user_from_claims,
)

security = HTTPBearer(auto_error=False)
_security_dep = Security(security)


def get_current_user_claims(
    credentials: HTTPAuthorizationCredentials | None = _security_dep,
) -> dict[str, Any]:
    """Validate Bearer JWT and return decoded claims."""
    if not credentials or credentials.scheme.lower() != "bearer":
        # Fallback for dev / unauthenticated endpoints
        return {
            "sub": "anonymous_user",
            "email": "anonymous@forge.local",
            "name": "Anonymous",
        }

    token = credentials.credentials
    try:
        claims = decode_jwt_token(token)
        return claims
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


_claims_dep = Depends(get_current_user_claims)
_db_dep = Depends(get_db)


def get_current_user_id(
    claims: dict[str, Any] = _claims_dep,
) -> str:
    """Return user id (sub) from validated claims."""
    sub: str = claims.get("sub", "anonymous_user")
    return sub


def get_current_user(
    claims: dict[str, Any] = _claims_dep,
    db: Session = _db_dep,
) -> str:
    """Validate Authentik JWT via PyJWT and sync user record in Postgres."""
    if claims.get("sub") == "anonymous_user":
        return "anonymous_user"

    user = sync_user_from_claims(db, claims)
    return str(user.id)
