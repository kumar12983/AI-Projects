"""
FastAPI shared dependencies.

  get_db()              — yields a psycopg2 connection, closes after request
  get_current_user_id() — decodes JWT Bearer token → user_id (int), no DB hit
  get_current_user()    — JWT decode + DB load → User object (for routes needing user data)
  get_premium_user()    — get_current_user + premium subscription check

FastAPI caches Depends(get_db) within a single request, so get_current_user (which
also declares Depends(get_db)) and the route itself share the same connection instance.
"""
import os
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from db_utils import get_db_connection

_JWT_SECRET    = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "dev-secret"))
_JWT_ALGORITHM = "HS256"
_bearer        = HTTPBearer()


# ── Database connection ───────────────────────────────────────────────────────

def get_db() -> Generator:
    """Open a psycopg2 connection; close it when the request completes."""
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )
    try:
        yield conn
    finally:
        conn.close()


# ── JWT auth ──────────────────────────────────────────────────────────────────

def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> int:
    """
    Fast auth guard — decodes the JWT Bearer token and returns user_id as int.
    No database lookup.  Use as an auth guard on routes that don't need user attributes.
    """
    try:
        payload = jwt.decode(credentials.credentials, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise ValueError("missing sub")
        return int(sub)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    """
    Full User object — used when routes need user attributes (premium check, rate limits).
    Shares the same DB connection as the route via FastAPI dependency caching.
    """
    from services import user_service
    user = user_service.get_user_by_id(conn, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# ── Premium guard ─────────────────────────────────────────────────────────────

def get_premium_user(user=Depends(get_current_user)):
    """get_current_user + premium subscription check.  Returns 403 if not premium."""
    if not user.is_premium():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
            headers={"X-Upgrade-URL": "/pricing"},
        )
    return user
