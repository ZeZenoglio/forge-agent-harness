"""Authentik authentication and user synchronization service (REQ-035, REQ-036, REQ-048).

Validates Authentik JWTs using PyJWT, verifies expiration, and synchronizes
user accounts (including social logins and profile updates) in Postgres.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import jwt
from sqlalchemy.orm import Session

from backend.db.models import Session as UserSession
from backend.db.models import User

AUTHENTIK_SECRET = os.getenv(
    "JWT_SECRET", "authentik-default-secret-key-change-in-prod"
)
AUTHENTIK_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTHENTIK_AUDIENCE = os.getenv("JWT_AUDIENCE", None)
AUTHENTIK_ISSUER = os.getenv("JWT_ISSUER", None)


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def decode_jwt_token(
    token: str,
    key: str = AUTHENTIK_SECRET,
    algorithms: list[str] | None = None,
    verify_exp: bool = True,
) -> dict[str, Any]:
    """Decode and validate a JWT using PyJWT (not python-jose).

    Enforces expiration check (REQ-035 AC 5).
    """
    algs = algorithms or [AUTHENTIK_ALGORITHM, "RS256"]
    options = {"verify_exp": verify_exp}

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            key=key,
            algorithms=algs,
            options=options,  # type: ignore[arg-type]
            audience=AUTHENTIK_AUDIENCE,
            issuer=AUTHENTIK_ISSUER,
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired", status_code=401) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError(
            f"Invalid authentication token: {exc!s}", status_code=401
        ) from exc


def sync_user_from_claims(db: Session, claims: dict[str, Any]) -> User:
    """Synchronize user profile from Authentik claims into Postgres.

    - Links/merges existing users sharing the same email (REQ-036 AC 4).
    - Syncs profile attributes (name, avatar) on token refresh (REQ-048 AC 5).
    """
    email = (
        claims.get("email")
        or claims.get("preferred_username")
        or f"{claims.get('sub')}@authentik.local"
    )
    name = claims.get("name") or claims.get("preferred_username") or ""
    avatar_url = claims.get("avatar_url") or claims.get("picture")
    provider = claims.get("provider") or claims.get("idp") or "authentik"

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        # Create new user
        user = User(
            id=str(claims.get("sub", "")),
            email=email,
            name=name,
            avatar_url=avatar_url,
            provider=provider,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(user)
    else:
        # Merge / update user profile attributes
        if name and user.name != name:
            user.name = name
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
        if provider and user.provider != provider:
            user.provider = provider
        user.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(user)
    return user


def record_user_session(
    db: Session, user_id: str, token: str, expires_at: datetime | None = None
) -> UserSession:
    """Record an active session in the database (REQ-048 AC 3)."""
    user_session = UserSession(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
    )
    db.add(user_session)
    db.commit()
    db.refresh(user_session)
    return user_session


def revoke_user_session(db: Session, session_id: str) -> bool:
    """Revoke an active session (REQ-048 AC 3)."""
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if session:
        db.delete(session)
        db.commit()
        return True
    return False
