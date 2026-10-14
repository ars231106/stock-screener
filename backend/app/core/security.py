"""JWT verification for Supabase-issued access tokens.

The frontend signs in through Supabase Auth and receives an access token.
It sends that token as ``Authorization: Bearer <token>``. We verify the
signature locally with the project's JWT secret — no network round-trip
per request.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user_id: str, email: Optional[str], claims: dict):
        self.id = user_id
        self.email = email
        self.claims = claims

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CurrentUser {self.email or self.id}>"


def _decode(token: str) -> dict:
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server auth is not configured (missing SUPABASE_JWT_SECRET).",
        )
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_aud": True},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentUser:
    """Dependency for protected routes. Raises 401 when absent/invalid."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = _decode(credentials.credentials)
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has no subject"
        )
    return CurrentUser(user_id=user_id, email=claims.get("email"), claims=claims)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[CurrentUser]:
    """Same as above but returns None instead of raising — for routes that
    work anonymously but personalise when signed in."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        claims = _decode(credentials.credentials)
    except HTTPException:
        return None
    user_id = claims.get("sub")
    if not user_id:
        return None
    return CurrentUser(user_id=user_id, email=claims.get("email"), claims=claims)
