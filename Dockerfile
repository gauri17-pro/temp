# ── Stage 1: Build ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Entrypoint script
COPY --chmod=755 entrypoint.sh /entrypoint.sh

EXPOSE 5000

ENV FLASK_APP=app.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
