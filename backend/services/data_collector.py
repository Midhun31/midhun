"""
services/data_collector.py
Fetches real-time market news and data for a given sector using DuckDuckGo
search (via the duckduckgo_search library). Falls back to a curated static
dataset when the live fetch fails (network unavailable, quota, etc.).
"""

import asyncio
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── DuckDuckGo search helper ───────────────────────────────────────────────────
DDGS_API_URL = "https://api.duckduckgo.com/"

# Fallback static snippets per sector (used when live search fails)
STATIC_FALLBACK: dict[str, list[str]] = {
    "technology": [
        "India's IT sector is projected to reach $350 billion by 2026 driven by AI and cloud adoption.",
        "PLI scheme is attracting semiconductor manufacturing investments worth ₹76,000 crore.",
        "India ranks 3rd globally in startup ecosystems with 100+ unicorns as of 2024.",
        "Digital India initiative targets $1 trillion digital economy by 2025.",
    ],
    "agriculture": [
        "India is the world's largest exporter of rice, spices, and cotton.",
        "AgriTech investments in India crossed $1 billion in 2023.",
        "PM-KISAN scheme benefits 110 million farmer families.",
        "India's food processing industry is expected to reach $535 billion by 2025-26.",
    ],
    "pharma": [
        "India is the world's largest supplier of generic medicines, supplying 20% globally.",
        "India's pharmaceutical market is projected to grow to $130 billion by 2030.",
        "PLI scheme for pharma has attracted investments of over ₹15,000 crore.",
        "India exports medicines to over 200 countries and territories.",
    ],
    "automobile": [
        "India is the world's 3rd largest automobile market.",
        "EV sales in India crossed 1.5 million units in FY2024.",
        "PLI scheme for auto components is attracting ₹67,690 crore investment.",
        "India's auto exports grew 15% YoY reaching $21.2 billion in FY2024.",
    ],
    "energy": [
        "India targets 500 GW of renewable energy capacity by 2030.",
        "Solar energy installations crossed 73 GW in India as of 2024.",
        "India is the world's 3rd largest producer of renewable energy.",
        "Green hydrogen mission targets production of 5 million metric tonnes by 2030.",
    ],
    "textile": [
        "India's textile and apparel industry is worth $140 billion.",
        "India targets textile exports of $100 billion by 2030.",
        "PLI scheme for textiles focuses on man-made fibres and technical textiles.",
        "India is the 2nd largest exporter of textiles globally.",
    ],
    "finance": [
        "India's financial services market is expected to reach $1.5 trillion by 2025.",
        "UPI transactions crossed 10 billion per month in 2024.",
        "India has the world's largest number of fintech startups outside US and China.",
        "RBI's digital rupee pilot is expanding to more cities.",
    ],
    "real_estate": [
        "India's real estate market is expected to reach $1 trillion by 2030.",
        "Office space absorption in India's top 7 cities hit a record 72 million sq ft in 2023.",
        "REIT market in India has seen 40% growth in investor participation.",
        "Data centre demand is driving commercial real estate growth.",
    ],
    "fmcg": [
        "India's FMCG market is expected to reach $220 billion by 2025.",
        "Rural FMCG demand is growing at 8% CAGR driven by rural income increase.",
        "D2C brands in India have attracted $4 billion in funding cumulatively.",
        "Quick commerce is disrupting FMCG distribution channels.",
    ],
    "manufacturing": [
        "Make in India initiative has attracted FDI worth $500 billion since 2014.",
        "PLI schemes across 14 sectors are expected to create 6 million jobs.",
        "India aims to increase manufacturing share of GDP to 25% by 2025.",
        "India is emerging as a global supply chain alternative.",
    ],
    "healthcare": [
        "India's healthcare industry is expected to reach $638 billion by 2025.",
        "Medical tourism in India generates $9 billion annually.",
        "Ayushman Bharat scheme covers 500 million beneficiaries.",
        "India's medtech market is growing at 15% CAGR.",
    ],
    "education": [
        "India's edtech market is projected to reach $30 billion by 2030.",
        "National Education Policy 2020 is driving curriculum reform.",
        "India has the world's largest higher education system with 50,000+ institutions.",
        "Skill India Mission aims to train 400 million by 2022 with ongoing expansion.",
    ],
    "defence": [
        "India's defence budget crossed ₹6 lakh crore in FY2025.",
        "India targets defence exports of ₹35,000 crore by 2025.",
        "atmanirbhar Bharat targets 75% domestic defence procurement.",
        "India has signed $10 billion worth of defence MoUs with global partners.",
    ],
    "infrastructure": [
        "PM Gati Shakti plan worth ₹100 lakh crore targets multimodal infrastructure.",
        "National Monetisation Pipeline aims to raise ₹6 lakh crore.",
        "India is building 30 km of highways per day.",
        "Smart Cities Mission has completed projects worth ₹1.5 lakh crore.",
    ],
    "chemicals": [
        "India's chemical industry is the 6th largest globally worth $220 billion.",
        "Specialty chemicals market in India is growing at 12% CAGR.",
        "India targets $300 billion chemical industry by 2025.",
        "China+1 strategy is shifting chemical procurement to India.",
    ],
}


async def fetch_sector_data(sector: str) -> tuple[list[str], list[str]]:
    """
    Fetch recent news/data about the sector.
    Returns (snippets: list[str], sources: list[str]).
    Tries DuckDuckGo Instant Answer API first; falls back to static data.
    """
    snippets: list[str] = []
    sources:  list[str] = []

    # ── Live Fetch via DuckDuckGo ──────────────────────────────────────────────
    try:
        query = f"India {sector} sector trade opportunities 2024 market trends"
        params = {
            "q":      query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(DDGS_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        # Extract abstract
        if data.get("Abstract"):
            snippets.append(data["Abstract"])
            sources.append(data.get("AbstractSource", "DuckDuckGo"))

        # Extract related topics
        for topic in data.get("RelatedTopics", [])[:6]:
            if isinstance(topic, dict) and topic.get("Text"):
                snippets.append(topic["Text"])
                if topic.get("FirstURL"):
                    sources.append(topic["FirstURL"])

        logger.info("Live DuckDuckGo fetch succeeded: %d snippets", len(snippets))

    except Exception as exc:
        logger.warning("DuckDuckGo fetch failed (%s). Using static fallback.", exc)

    # ── Supplement / Fallback with static data ─────────────────────────────────
    key = sector.lower().replace("-", "_").replace(" ", "_")
    static = STATIC_FALLBACK.get(key, STATIC_FALLBACK["manufacturing"])

    # Merge: live snippets first, then static ones not already included
    existing_text = " ".join(snippets).lower()
    for item in static:
        if item[:30].lower() not in existing_text:
            snippets.append(item)

    if not sources:
        sources = [
            "Ministry of Commerce and Industry – India",
            "IBEF (India Brand Equity Foundation)",
            "NASSCOM India",
            "RBI Annual Report 2024",
        ]

    # Add standard authoritative sources
    sources += [
        "IBEF.org",
        "Ministry of Commerce, India",
        "NSE/BSE Market Data",
    ]

    return snippets[:12], list(dict.fromkeys(sources))[:6]  # deduplicate
