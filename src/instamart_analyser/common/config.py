"""Project paths and constants."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

# Data directories per phase
DATA_DIR = PROJECT_ROOT / "data"
PHASE_0_DATA = DATA_DIR / "phase-0"
PHASE_1_DATA = DATA_DIR / "phase-1"
PHASE_1_RAW = PHASE_1_DATA / "raw"
PHASE_1_DB = PHASE_1_DATA / "db"
PHASE_1_SEED = PHASE_1_DATA / "seed"

PHASE_2_DATA = DATA_DIR / "phase-2"
PHASE_2_DB = PHASE_2_DATA / "db"
PHASE_3_DATA = DATA_DIR / "phase-3"
PHASE_4_DATA = DATA_DIR / "phase-4"
PHASE_5_DATA = DATA_DIR / "phase-5"
PHASE_6_DATA = DATA_DIR / "phase-6"

LOGS_DIR = PROJECT_ROOT / "logs"
PHASE_1_LOGS = LOGS_DIR / "phase-1"
PHASE_2_LOGS = LOGS_DIR / "phase-2"
PHASE_3_LOGS = LOGS_DIR / "phase-3"
PHASE_4_LOGS = LOGS_DIR / "phase-4"
PHASE_5_LOGS = LOGS_DIR / "phase-5"
PHASE_6_LOGS = LOGS_DIR / "phase-6"

# Phase 6A API auth tokens (local demo defaults; override in .env)
API_VIEWER_TOKEN = os.environ.get("API_VIEWER_TOKEN", "viewer-demo-token")
API_REVIEWER_TOKEN = os.environ.get("API_REVIEWER_TOKEN", "reviewer-demo-token")
API_ADMIN_TOKEN = os.environ.get("API_ADMIN_TOKEN", "admin-demo-token")
API_CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "API_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
# Optional regex for preview URLs (default matches https://*.vercel.app)
API_CORS_ORIGIN_REGEX = os.environ.get(
    "API_CORS_ORIGIN_REGEX",
    r"https://.*\.vercel\.app",
).strip() or None

SCHEMAS_DIR = PROJECT_ROOT / "schemas"

# Source configuration
SWIGGY_PLAY_STORE_APP_ID = "in.swiggy.android"
SWIGGY_APP_STORE_ID = "989540920"
SWIGGY_APP_STORE_COUNTRY = "in"

REDDIT_SUBREDDITS = [
    "swiggyinstamart",
    "swiggy",
    "india",
    "bangalore",
    "mumbai",
    "delhi",
    "IndianFood",
]
REDDIT_SEARCH_QUERIES = [
    "instamart",
    "swiggy instamart",
    "instamart grocery",
    "instamart delivery",
    "instamart category",
    "instamart personal care",
    "instamart pet",
]

# Known MouthShut Instamart review pages
MOUTHSHUT_REVIEW_URLS = [
    "https://www.mouthshut.com/review/swiggy-review-snnulmpslop",
    "https://www.mouthshut.com/review/swiggy-review-smrqqlotpop",
    "https://www.mouthshut.com/review/swiggy-review-squtonnunlp",
    "https://www.mouthshut.com/review/swiggy-review-pluqrnlrnnp",
    "https://www.mouthshut.com/review/swiggy-review-mplnnrnqrop",
]

# Instamart-only filter: reviews must explicitly mention Instamart
INSTAMART_REQUIRED_TERMS = [
    "instamart",
    "insta mart",
]

# Secondary terms used only for Reddit/search queries, not for inclusion on their own
INSTAMART_SEARCH_TERMS = [
    "swiggy instamart",
    "instamart grocery",
    "instamart delivery",
    "instamart category",
]

USER_AGENT = "InstamartAnalyser/0.1 (category-discovery-research)"

DEFAULT_MAX_PER_SOURCE = 0  # 0 = collect all Instamart matches in the lookback window
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 2.0

# Phase 2 enrichment
ENRICHMENT_COHORT_CAP = 1000
ENRICHMENT_BODY_WORD_CAP = 100
ENRICHMENT_CHECKPOINT_INTERVAL = 20
ENRICHMENT_BATCH_SIZE = int(os.environ.get("GROQ_ENRICHMENT_BATCH_SIZE", "8"))

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MAX_TOKENS = int(os.environ.get("GROQ_MAX_TOKENS", "2048"))
GROQ_TEMPERATURE = float(os.environ.get("GROQ_TEMPERATURE", "0.1"))
GROQ_MAX_REQUESTS_PER_MINUTE = int(os.environ.get("GROQ_MAX_REQUESTS_PER_MINUTE", "10"))
GROQ_ENRICHMENT_DAILY_CAP = int(os.environ.get("GROQ_ENRICHMENT_DAILY_CAP", "130"))
GROQ_DAILY_REQUEST_RESERVE = int(os.environ.get("GROQ_DAILY_REQUEST_RESERVE", "50"))
GROQ_DAILY_TOKEN_BUDGET = int(os.environ.get("GROQ_DAILY_TOKEN_BUDGET", "95000"))


def is_instamart_review(text: str) -> bool:
    """Return True only if text explicitly mentions Instamart."""
    lowered = text.lower()
    return any(term in lowered for term in INSTAMART_REQUIRED_TERMS)
