# ── Backend Dockerfile ──
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Generate ML model at build time
RUN python ml/generate_data.py && python ml/train_scorer.py

# Run migrations then start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
