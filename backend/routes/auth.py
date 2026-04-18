"""
routes/auth.py - Authentication endpoint.
POST /auth/login  →  returns JWT access token.
"""

from fastapi import APIRouter, HTTPException, status
from models.schemas import LoginRequest, TokenResponse
from middleware.auth import USERS, create_access_token

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="Obtain JWT access token")
async def login(body: LoginRequest):
    """
    Authenticate with username + password.
    Returns a JWT bearer token valid for 1 hour.

    **Demo credentials:**
    - admin / password123
    - analyst / trade2024
    - demo / demo1234
    """
    stored_password = USERS.get(body.username)
    if not stored_password or stored_password != body.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, expires_in = create_access_token(body.username)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
    )
