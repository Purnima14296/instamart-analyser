# Railway API image — FastAPI + existing SQLite/JSON artifacts
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=src \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps used by some Python packages (and optional Selenium later)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# App code + pilot artifacts (data/ is ~7MB and needed for a working dashboard)
COPY src ./src
COPY schemas ./schemas
COPY data ./data
COPY .env.example ./.env.example

# Railway injects $PORT
EXPOSE 8000
CMD ["sh", "-c", "uvicorn instamart_analyser.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
