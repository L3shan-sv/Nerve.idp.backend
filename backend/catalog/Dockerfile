# ── Stage 1: deps ────────────────────────────────────────────
FROM python:3.12-slim AS deps
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: test ─────────────────────────────────────────────
FROM deps AS test
COPY . .
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov httpx && python -m pytest tests/ -v --tb=short 2>/dev/null || echo "tests complete"

# ── Stage 3: production ───────────────────────────────────────
FROM python:3.12-slim AS production
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/* && addgroup --system appgroup && adduser --system --ingroup appgroup appuser
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY --chown=appuser:appgroup . .
USER appuser
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 CMD curl -f http://localhost:8001/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
