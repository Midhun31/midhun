"""
models/schemas.py - Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
import re

# ── Auth Schemas ───────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, example="admin")
    password: str = Field(..., min_length=4, max_length=100, example="password123")

    @validator("username")
    def username_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must be alphanumeric (underscores allowed).")
        return v.lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# ── Analysis Schemas ───────────────────────────────────────────────────────────

VALID_SECTORS = [
    "technology", "agriculture", "pharma", "textile",
    "automobile", "energy", "finance", "real_estate",
    "fmcg", "manufacturing", "healthcare", "education",
    "defence", "infrastructure", "chemicals",
]

class AnalysisResponse(BaseModel):
    sector: str
    report: str                     # Full markdown string
    data_sources: list[str]
    generated_at: str               # ISO timestamp


class ErrorResponse(BaseModel):
    detail: str
    message: Optional[str] = None


# ── Rate Limit Info ────────────────────────────────────────────────────────────

class RateLimitInfo(BaseModel):
    requests_made: int
    requests_limit: int
    window_seconds: int
    reset_in_seconds: int
