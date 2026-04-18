"""
utils/helpers.py
Shared utility functions used across the application.
"""

import re
import html


def normalize_sector(sector: str) -> str:
    """
    Normalize a sector string:
    - Lowercase
    - Replace spaces/hyphens with underscores
    - Strip non-alphanumeric characters (except underscores)
    """
    s = sector.strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


def sanitize_text(text: str) -> str:
    """
    Basic sanitization for output text.
    Removes null bytes, strips excessive whitespace.
    Does NOT HTML-escape (markdown is returned as-is to the client).
    """
    if not text:
        return ""
    # Remove null bytes
    text = text.replace("\x00", "")
    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate(text: str, max_chars: int = 300) -> str:
    """Truncate a string to max_chars, appending '...' if truncated."""
    return text if len(text) <= max_chars else text[:max_chars].rstrip() + "..."


def format_iso_timestamp(dt_str: str) -> str:
    """
    Convert ISO 8601 timestamp string to a human-readable format.
    e.g. '2024-03-15T10:30:00+00:00' → 'March 15, 2024 10:30 UTC'
    """
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%B %d, %Y %H:%M UTC")
    except Exception:
        return dt_str
