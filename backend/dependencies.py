
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Security(security)) -> str:  # noqa: B008
    """
    Mock JWT validation for local dev without Authentik.
    If a Bearer token is provided, we pretend it's a valid JWT and the token string itself is the user_id.
    If no token is provided, we default to "anonymous_user".
    """
    if credentials and credentials.scheme.lower() == "bearer":
        # In a real implementation with Authentik, we would use PyJWT to decode and validate here.
        # token = credentials.credentials
        # payload = jwt.decode(token, public_key, algorithms=["RS256"])
        # return payload.get("sub")
        return credentials.credentials
        
    return "anonymous_user"
