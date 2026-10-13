"""Supabase JWT verification for authenticated trip endpoints.

New Supabase projects sign access tokens asymmetrically (ES256); keys are
resolved via the project's JWKS URL. Anonymous requests carry no token and
continue to use the local SQLite plan store.
"""

import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)
_jwks_client_instance: jwt.PyJWKClient | None = None


def _jwks_client() -> jwt.PyJWKClient:
    global _jwks_client_instance
    if _jwks_client_instance is None:
        _jwks_client_instance = jwt.PyJWKClient(settings.supabase_jwks_url, cache_keys=True)
    return _jwks_client_instance


def verify_token(token: str) -> str:
    """Verify a Supabase access token and return the user id (sub)."""
    if not settings.supabase_jwks_url or not settings.supabase_url:
        raise ValueError("Supabase auth is not configured")
    try:
        key = _jwks_client().get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
            options={"require": ["exp", "sub"]},
        )
    except Exception as e:
        logger.warning("Token verification failed: %s", e)
        raise ValueError("Invalid access token") from e
    return str(payload["sub"])


async def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    """Return the user id when a valid Bearer token is present, else None.

    A present-but-invalid token is rejected (401) rather than silently
    treated as anonymous, so expired sessions surface instead of losing
    trip ownership.
    """
    if credentials is None:
        return None
    try:
        return verify_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")


async def get_required_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    user_id = await get_optional_user_id(credentials)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return user_id
