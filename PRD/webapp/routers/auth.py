"""
JWT authentication routes for FastAPI.

POST /api/auth/login    → access_token + refresh_token
POST /api/auth/refresh  → new access_token (requires refresh_token Bearer)
DELETE /api/auth/logout → stateless; client must discard tokens

Token generation uses python-jose (HS256, same secret as Flask side) so tokens
issued by either framework are mutually accepted.
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from db_utils import get_db_connection
from schemas import LoginRequest

router = APIRouter(tags=["auth"])

_JWT_SECRET    = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "dev-secret"))
_JWT_ALGORITHM = "HS256"
_ACCESS_TTL    = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES",  "15")))
_REFRESH_TTL   = timedelta(days=int(   os.getenv("JWT_REFRESH_DAYS",    "7")))

_bearer = HTTPBearer()


def _make_token(user_id: int, expires: timedelta, token_type: str) -> str:
    """Create a signed JWT with sub, type and exp claims."""
    payload = {
        "sub":  str(user_id),
        "type": token_type,
        "exp":  datetime.now(tz=timezone.utc) + expires,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


@router.post("/login")
def login(body: LoginRequest):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        from services import user_service
        user = user_service.authenticate_user(conn, body.email, body.password)
    finally:
        conn.close()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return {
        "access_token":  _make_token(user.user_id, _ACCESS_TTL,  "access"),
        "refresh_token": _make_token(user.user_id, _REFRESH_TTL, "refresh"),
    }


@router.post("/refresh")
def refresh(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    try:
        payload = jwt.decode(credentials.credentials, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise ValueError("not a refresh token")
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"access_token": _make_token(user_id, _ACCESS_TTL, "access")}


@router.delete("/logout")
def logout(_: HTTPAuthorizationCredentials = Depends(_bearer)):
    """Stateless logout — client is responsible for discarding tokens."""
    return {"message": "Logged out. Discard your tokens."}
