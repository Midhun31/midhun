"""
routes/analyze.py
GET /analyze/{sector} — main analysis endpoint.

Workflow:
  1. Validate sector input
  2. Authenticate user via JWT
  3. Rate limiting handled by middleware
  4. Fetch market data (DuckDuckGo + static fallback)
  5. Send data to Gemini for AI analysis
  6. Return structured markdown report
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from middleware.auth import get_current_user
from models.schemas import AnalysisResponse, VALID_SECTORS
from services.data_collector import fetch_sector_data
from services.ai_analyzer import generate_analysis
from utils.helpers import normalize_sector, sanitize_text

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{sector}",
    response_model=AnalysisResponse,
    summary="Analyze a market sector for trade opportunities",
    responses={
        200: {"description": "Structured markdown trade report"},
        400: {"description": "Invalid sector"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def analyze_sector(
    sector: str,
    current_user: str = Depends(get_current_user),
):
    """
    Returns a structured markdown report of trade opportunities for the
    specified Indian market sector.

    **Valid sectors:** technology, agriculture, pharma, textile, automobile,
    energy, finance, real_estate, fmcg, manufacturing, healthcare, education,
    defence, infrastructure, chemicals.
    """
    # ── 1. Normalize & Validate ────────────────────────────────────────────────
    sector_clean = normalize_sector(sector)

    

    logger.info("User '%s' requested analysis for sector: %s", current_user, sector_clean)

    # ── 2. Fetch Market Data ───────────────────────────────────────────────────
    try:
        snippets, sources = await fetch_sector_data(sector_clean)
    except Exception as exc:
        logger.error("Data collection failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch market data. Please try again.",
        )

    if not snippets:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No market data available for this sector at the moment.",
        )

    # ── 3. AI Analysis ─────────────────────────────────────────────────────────
    try:
        report_markdown = await generate_analysis(sector_clean, snippets)
    except Exception as exc:
        logger.error("AI analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI analysis service is temporarily unavailable.",
        )

    # ── 4. Sanitize & Return ───────────────────────────────────────────────────
    report_markdown = sanitize_text(report_markdown)

    return AnalysisResponse(
        sector=sector_clean,
        report=report_markdown,
        data_sources=sources,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/sectors/list", summary="List all valid sectors", tags=["Analysis"])
async def list_sectors():
    """Returns all valid sector identifiers."""
    return {"sectors": VALID_SECTORS}
