"""
JWT authentication routes for FastAPI.

POST   /api/auth/login                → access_token + refresh_token
POST   /api/auth/refresh              → new access_token (requires refresh_token Bearer)
DELETE /api/auth/logout               → stateless; client must discard tokens
POST   /api/auth/register             → create account; returns tokens on success
POST   /api/auth/forgot-password      → send password-reset email
POST   /api/auth/reset-password/{tok} → validate token and set new password
GET    /api/auth/me                   → current user profile + monthly usage count

Token generation uses python-jose (HS256, same secret as Flask side) so tokens
issued by either framework are mutually accepted.
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from db_utils import get_db_connection
from dependencies import get_current_user, get_db
from schemas import LoginRequest, RegisterRequest, ForgotPasswordRequest, ResetPasswordRequest

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


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    """Create a new account and return tokens immediately."""
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        from services import user_service
        user_id = user_service.register_user(conn, body.email, body.password, body.full_name)
    finally:
        conn.close()

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        )

    return {
        "access_token":  _make_token(user_id, _ACCESS_TTL,  "access"),
        "refresh_token": _make_token(user_id, _REFRESH_TTL, "refresh"),
    }


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    """Send a password-reset link to the email address if an account exists."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    def _build_reset_url(token: str) -> str:
        return f"{frontend_url}/reset-password/{token}"

    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        from services import user_service
        user_service.request_password_reset(conn, body.email, _build_reset_url)
    finally:
        conn.close()

    # Always return success to avoid account enumeration
    return {
        "message": "If that email is registered you will receive a reset link shortly. "
                   "Please also check your spam folder."
    }


@router.post("/reset-password/{token}")
def reset_password(token: str, body: ResetPasswordRequest):
    """Validate the reset token and update the user's password."""
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        from services import user_service
        success = user_service.complete_password_reset(conn, token, body.password)
    finally:
        conn.close()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return {"message": "Password updated successfully"}


@router.get("/me")
def me(user=Depends(get_current_user), conn=Depends(get_db)):
    """Return the current user's profile and monthly usage count."""
    usage_count = user.get_monthly_usage(conn)
    return {
        "user_id":                      user.user_id,
        "email":                        user.email,
        "full_name":                    user.full_name,
        "tier_name":                    user.tier_name,
        "subscription_status":          user.subscription_status,
        "searches_per_month":           user.searches_per_month,
        "can_export_data":              user.can_export_data,
        "can_access_analytics":         user.can_access_analytics,
        "can_access_school_catchments": user.can_access_school_catchments,
        "usage_count":                  usage_count,
    }
