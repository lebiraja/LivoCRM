# ── Backend Dockerfile ──
FROM python:3.12-slim AS base

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1

# Unprivileged runtime user (SEC-17)
RUN useradd --system --uid 10001 --no-create-home app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt

# ── Test image: runtime deps + pytest/ruff/mypy ──
FROM base AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 120 -r requirements-dev.txt

# Tests write .coverage into /app
COPY --chown=app:app . .
RUN chown app /app
USER app
RUN python ml/generate_data.py && python ml/train_scorer.py

CMD ["pytest"]

# ── Runtime image ──
FROM base AS runtime

# Copy source
COPY . .

# Generate ML model at build time
RUN python ml/generate_data.py && python ml/train_scorer.py

# Code and model stay root-owned, read-only to the app user (SEC-17, SEC-24)
USER app

# Run migrations then start server
# --proxy-headers: client IP comes from nginx's X-Forwarded-For (backend is reachable only via nginx)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
