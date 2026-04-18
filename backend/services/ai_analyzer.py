"""
services/ai_analyzer.py
Sends collected market data to Google Gemini API and parses the structured
markdown report. Falls back to a rule-based report generator if Gemini is
unavailable (no API key, quota exceeded, network error).
"""

import os
import re
import httpx
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Gemini Config ──────────────────────────────────────────────────────────────
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL    = "gemini-1.5-flash"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# ── Prompt Template ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior trade analyst specializing in the Indian market.
Analyze the provided market data and generate a STRUCTURED trade opportunity report.
Follow the EXACT markdown format below — do not deviate from it.

## Output Format

# Sector Analysis: {sector}

## Overview
(2-3 sentences summarizing the sector's current state in India)

## Market Trends
- (trend 1)
- (trend 2)
- (trend 3)
- (trend 4)

## Trade Opportunities
- (opportunity 1)
- (opportunity 2)
- (opportunity 3)
- (opportunity 4)

## Risks
- (risk 1)
- (risk 2)
- (risk 3)

## Conclusion
(2-3 sentences with forward-looking insights and recommendation)

Be specific, data-driven, and focused on actionable trade insights for investors
and businesses looking at India's {sector} sector.
"""

USER_PROMPT_TEMPLATE = """Analyze the following market data and generate a structured
trade opportunity report for the {sector} sector in India.
Include trends, opportunities, risks, and a conclusion.

Market Data:
{data_points}

Generate the report now in the exact markdown format specified."""


async def generate_analysis(sector: str, data_points: list[str]) -> str:
    """
    Main entry point. Tries Gemini API first; falls back to static generator.
    Returns a markdown string.
    """
    formatted_data = "\n".join(f"• {p}" for p in data_points)

    if GEMINI_API_KEY:
        try:
            report = await _call_gemini(sector, formatted_data)
            logger.info("Gemini API report generated for sector: %s", sector)
            return report
        except Exception as exc:
            logger.warning("Gemini call failed (%s). Using fallback generator.", exc)

    # Use rule-based fallback
    logger.info("Using fallback report generator for sector: %s", sector)
    return _fallback_report(sector, data_points)


async def _call_gemini(sector: str, formatted_data: str) -> str:
    """
    Calls Google Gemini API and returns the generated text.
    """
    system_text = SYSTEM_PROMPT.replace("{sector}", sector.title())
    user_text   = USER_PROMPT_TEMPLATE.format(
        sector=sector.title(),
        data_points=formatted_data,
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": system_text + "\n\n" + user_text}
                ],
            }
        ],
        "generationConfig": {
            "temperature":    0.4,
            "topP":           0.9,
            "maxOutputTokens": 1200,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            GEMINI_ENDPOINT,
            params={"key": GEMINI_API_KEY},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    # Extract text from response
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini returned no candidates.")

    parts = candidates[0].get("content", {}).get("parts", [])
    text  = "".join(p.get("text", "") for p in parts).strip()

    if not text:
        raise ValueError("Gemini returned empty text.")

    return text


def _fallback_report(sector: str, data_points: list[str]) -> str:
    """
    Rule-based markdown report built from collected data points.
    Used when Gemini is unavailable.
    """
    title = sector.replace("_", " ").title()
    now   = datetime.now(timezone.utc).strftime("%B %Y")

    # Split data points into categories heuristically
    trends       = data_points[:4]  if len(data_points) >= 4  else data_points
    opportunities= data_points[4:8] if len(data_points) >= 8  else data_points[:4]
    risks_pool   = [
        f"Global market volatility may impact {title} export demand.",
        f"Regulatory changes and compliance requirements in the {title} sector.",
        f"Currency fluctuation risks affecting {title} trade competitiveness.",
        f"Supply chain disruptions could affect {title} sector growth targets.",
        "Geopolitical tensions may limit foreign direct investment inflows.",
    ]

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    report = f"""# Sector Analysis: {title}

## Overview
India's {title} sector is experiencing robust growth driven by government-led initiatives, 
increasing domestic demand, and expanding global trade partnerships as of {now}. 
The sector presents compelling trade and investment opportunities for both domestic 
and international stakeholders.

## Market Trends
{bullets(trends[:4])}

## Trade Opportunities
{bullets(opportunities[:4])}

## Risks
{bullets(risks_pool[:3])}

## Conclusion
The {title} sector in India remains one of the most promising areas for trade and investment, 
backed by strong policy support and a growing consumer base of 1.4 billion people. 
Investors and businesses should monitor policy developments closely and consider establishing 
early-mover advantage in this rapidly evolving market.
"""
    return report.strip()
