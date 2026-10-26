# ── Backend Dockerfile ──
FROM python:3.12-slim AS base

WORKDIR /app
ENV PYTHONPATH=/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt

# ── Test image: runtime deps + pytest/ruff/mypy ──
FROM base AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 120 -r requirements-dev.txt

COPY . .
RUN python ml/generate_data.py && python ml/train_scorer.py

CMD ["pytest"]

# ── Runtime image ──
FROM base AS runtime

# Copy source
COPY . .

# Generate ML model at build time
RUN python ml/generate_data.py && python ml/train_scorer.py

# Run migrations then start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
