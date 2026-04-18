"""
middleware/auth.py - JWT creation, verification, and FastAPI dependency.
"""

import jwt
import time
from datetime import datetime, timezone
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ── Config ─────────────────────────────────────────────────────────────────────
SECRET_KEY  = "CHANGE_ME_IN_PRODUCTION_super_secret_key_2024"
ALGORITHM   = "HS256"
TOKEN_TTL   = 3600   # 1 hour in seconds

# ── In-Memory User Store (dummy credentials) ──────────────────────────────────
USERS: dict[str, str] = {
    "admin":   "password123",
    "analyst": "trade2024",
    "demo":    "demo1234",
}

# ── In-Memory Session Store ────────────────────────────────────────────────────
# Maps token jti → expiry timestamp (for optional revocation)
SESSIONS: dict[str, float] = {}

# ── Bearer Scheme ──────────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer()


def create_access_token(username: str) -> tuple[str, int]:
    """
    Create a signed JWT for `username`.
    Returns (token_string, expires_in_seconds).
    """
    issued_at = int(time.time())
    expiry    = issued_at + TOKEN_TTL
    jti       = f"{username}-{issued_at}"

    payload = {
        "sub": username,
        "iat": issued_at,
        "exp": expiry,
        "jti": jti,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    # Register session
    SESSIONS[jti] = expiry
    return token, TOKEN_TTL


def verify_token(token: str) -> dict:
    """
    Decode and validate a JWT.
    Raises HTTPException on failure.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )

    # Check session revocation (optional but useful)
    jti = payload.get("jti", "")
    if jti not in SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found. Please log in again.",
        )

    return payload


# ── FastAPI Dependency ─────────────────────────────────────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> str:
    """
    FastAPI dependency — extracts and validates JWT from Authorization header.
    Returns the authenticated username.
    """
    payload = verify_token(credentials.credentials)
    return payload["sub"]
