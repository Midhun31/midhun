"""
middleware/rate_limiter.py
Sliding-window rate limiter stored in memory.
Per-user limit: 10 requests per 60-second window.
The ASGI middleware also enforces IP-level limits for unauthenticated endpoints.
"""

import time
from collections import defaultdict, deque
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ── Config ─────────────────────────────────────────────────────────────────────
WINDOW_SECONDS   = 60
MAX_REQUESTS     = 10          # per user / IP within the window
ANALYZE_ENDPOINT = "/analyze"  # only rate-limit analysis calls

# ── In-Memory Store ────────────────────────────────────────────────────────────
# key → deque of request timestamps (floats)
_rate_store: dict[str, deque] = defaultdict(deque)


def _get_identifier(request: Request) -> str:
    """
    Prefer JWT subject; fall back to client IP.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            import jwt
            from middleware.auth import SECRET_KEY, ALGORITHM
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return f"user:{payload['sub']}"
        except Exception:
            pass
    # Fall back to IP
    ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


def check_rate_limit(identifier: str) -> tuple[bool, dict]:
    """
    Sliding-window check.
    Returns (allowed: bool, info: dict).
    """
    now = time.time()
    window_start = now - WINDOW_SECONDS
    q = _rate_store[identifier]

    # Evict timestamps outside the window
    while q and q[0] < window_start:
        q.popleft()

    count = len(q)
    reset_in = int(WINDOW_SECONDS - (now - q[0])) if q else WINDOW_SECONDS

    if count >= MAX_REQUESTS:
        return False, {
            "requests_made":   count,
            "requests_limit":  MAX_REQUESTS,
            "window_seconds":  WINDOW_SECONDS,
            "reset_in_seconds": max(reset_in, 0),
        }

    q.append(now)
    return True, {
        "requests_made":   count + 1,
        "requests_limit":  MAX_REQUESTS,
        "window_seconds":  WINDOW_SECONDS,
        "reset_in_seconds": WINDOW_SECONDS,
    }


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that rate-limits /analyze/* routes.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(ANALYZE_ENDPOINT):
            identifier = _get_identifier(request)
            allowed, info = check_rate_limit(identifier)

            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded.",
                        "rate_limit": info,
                    },
                    headers={
                        "Retry-After": str(info["reset_in_seconds"]),
                        "X-RateLimit-Limit": str(MAX_REQUESTS),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(info["reset_in_seconds"]),
                    },
                )

        response = await call_next(request)
        return response
