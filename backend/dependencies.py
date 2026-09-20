from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)

_security_dep = Security(security)  # evaluated once at module level (B008 fix)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = _security_dep,
) -> str:
    """
    Mock JWT validation for local dev without Authentik.

    If a Bearer token is provided we pretend it is a valid JWT and the token
    string itself is the ``user_id``.  If no token is provided we default to
    ``"anonymous_user"``.
    """
    if credentials and credentials.scheme.lower() == "bearer":
        # In production with Authentik, use PyJWT to decode and validate here:
        #   payload = jwt.decode(credentials.credentials, public_key, algorithms=["RS256"])
        #   return payload["sub"]
        return credentials.credentials

    return "anonymous_user"
