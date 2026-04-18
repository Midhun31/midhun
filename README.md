# TradeScope — India Trade Opportunities Analyzer

A production-ready **FastAPI + Vanilla JS** application that analyzes Indian market
sectors and returns AI-generated structured trade opportunity reports.

---

## Project Structure

```
trade-analyzer/
├── backend/
│   ├── main.py                    # App entry point, middleware, routes
│   ├── requirements.txt
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                # POST /auth/login
│   │   └── analyze.py             # GET  /analyze/{sector}
│   ├── services/
│   │   ├── __init__.py
│   │   ├── data_collector.py      # DuckDuckGo fetch + static fallback
│   │   └── ai_analyzer.py         # Gemini API + rule-based fallback
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                # JWT create / verify / dependency
│   │   └── rate_limiter.py        # Sliding-window rate limiter (ASGI)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic request/response models
│   └── utils/
│       ├── __init__.py
│       └── helpers.py             # normalize_sector, sanitize_text, etc.
├── frontend/
│   ├── index.html                 # Main dashboard
│   ├── login.html                 # Login page
│   ├── style.css                  # Complete design system
│   └── script.js                  # App logic, markdown renderer
└── README.md
```

---

## Quick Start

### 1. Clone & install backend dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. (Optional) Set Gemini API key

```bash
export GEMINI_API_KEY="your_key_here"
```

Get a free key at: https://aistudio.google.com/app/apikey

> Without a key the app uses a built-in rule-based report generator — fully functional, no external API needed.

### 3. Start the backend

```bash
cd backend
python main.py
# OR
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Open the frontend

Open your browser and go to:
```
http://localhost:8000/login.html
```

The FastAPI server serves the frontend as static files automatically.

---

## Demo Credentials

| Username | Password     |
|----------|-------------|
| admin    | password123 |
| analyst  | trade2024   |
| demo     | demo1234    |

---

## API Reference

### `POST /auth/login`

Authenticate and receive a JWT token.

**Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### `GET /analyze/{sector}`

Requires `Authorization: Bearer <token>` header.

**Valid sectors:**
`technology`, `agriculture`, `pharma`, `textile`, `automobile`, `energy`,
`finance`, `real_estate`, `fmcg`, `manufacturing`, `healthcare`, `education`,
`defence`, `infrastructure`, `chemicals`

**Response:**
```json
{
  "sector": "technology",
  "report": "# Sector Analysis: Technology\n\n## Overview\n...",
  "data_sources": ["IBEF.org", "Ministry of Commerce"],
  "generated_at": "2024-03-15T10:30:00+00:00"
}
```

**Error responses:**

| Code | Reason                    |
|------|---------------------------|
| 400  | Invalid sector name       |
| 401  | Missing / invalid JWT     |
| 429  | Rate limit exceeded (10/min) |
| 502  | Upstream API failure      |

---

### `GET /analyze/sectors/list`

Returns all valid sector identifiers.

---

### `GET /health`

Health check — no auth required.

---

## Security Features

| Feature            | Implementation                                      |
|--------------------|-----------------------------------------------------|
| JWT Authentication | PyJWT HS256, 1-hour expiry, session store           |
| Rate Limiting      | Sliding window, 10 req/60s per user, ASGI middleware |
| Input Validation   | Pydantic v2 models on all endpoints                 |
| Secure Headers     | X-Content-Type-Options, X-Frame-Options, XSS        |
| CORS               | Configurable, currently open for development        |
| Exception Handling | Global handler returns structured JSON errors       |

---

## Report Format

Every analysis returns this exact markdown structure:

```markdown
# Sector Analysis: Technology

## Overview
(2–3 sentences on current sector state)

## Market Trends
- Trend 1
- Trend 2
- Trend 3
- Trend 4

## Trade Opportunities
- Opportunity 1
- Opportunity 2
- Opportunity 3
- Opportunity 4

## Risks
- Risk 1
- Risk 2
- Risk 3

## Conclusion
(2–3 sentences with forward-looking recommendation)
```

---

## Backend Workflow

```
Request: GET /analyze/technology
         Authorization: Bearer <jwt>
         │
         ▼
    [1] JWT verification (middleware/auth.py)
         │
         ▼
    [2] Rate limit check (middleware/rate_limiter.py)
         │ 10 req/min sliding window per user
         ▼
    [3] Sector validation (models/schemas.py → VALID_SECTORS)
         │
         ▼
    [4] Market data fetch (services/data_collector.py)
         │ DuckDuckGo Instant Answer API
         │ → fallback: curated static snippets per sector
         ▼
    [5] AI Analysis (services/ai_analyzer.py)
         │ Gemini 1.5 Flash API (if GEMINI_API_KEY set)
         │ → fallback: rule-based markdown generator
         ▼
    [6] Response: AnalysisResponse (sector, report, sources, timestamp)
```

---

## Frontend Features

- **Login page** with JWT storage in `sessionStorage`
- **Auth guard** — auto-redirects to login if token expired
- **15 sector chips** for quick selection
- **Animated loading steps** showing pipeline progress
- **Markdown renderer** (no external library — pure vanilla JS)
- **Copy to clipboard** button for the raw markdown report
- **Session stats** bar (requests used, last sector, response time)
- **Rate limit error** handling with reset timer display
- **Responsive design** — works on mobile and desktop

---

## Configuration

All configuration is in source files (move to `.env` for production):

| Setting          | File                     | Default                        |
|------------------|--------------------------|--------------------------------|
| `SECRET_KEY`     | `middleware/auth.py`     | Change before deploying        |
| `TOKEN_TTL`      | `middleware/auth.py`     | 3600 seconds                   |
| `MAX_REQUESTS`   | `middleware/rate_limiter.py` | 10                         |
| `WINDOW_SECONDS` | `middleware/rate_limiter.py` | 60                         |
| `GEMINI_API_KEY` | Environment variable     | Empty (uses fallback)          |
| `GEMINI_MODEL`   | `services/ai_analyzer.py`| gemini-1.5-flash               |

---

## Interactive API Docs

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:**       http://localhost:8000/redoc

---

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Backend    | Python 3.10+, FastAPI, Uvicorn          |
| Auth       | PyJWT (HS256)                           |
| HTTP       | httpx (async)                           |
| Validation | Pydantic v2                             |
| AI         | Google Gemini 1.5 Flash API             |
| Data       | DuckDuckGo Instant Answer API           |
| Frontend   | HTML5, CSS3, Vanilla JavaScript         |
| Storage    | In-memory Python dicts                  |
