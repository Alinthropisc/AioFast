# ============================================================
# AioFast — Production Image
# Multi-stage: build → runtime
# ============================================================

# ── Stage 1: Builder ─────────────────────────────────────
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1

WORKDIR /build

COPY pyproject.toml uv.lock ./
COPY core/ core/

RUN uv sync --frozen --no-dev && \
    find /usr/local/lib/python3.12 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true


# ── Stage 2: Runtime ─────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="AioFast Team" \
      description="AioFast Application" \
      version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_ENV=production \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8000 \
    SERVER_WORKERS=4 \
    TZ=UTC

RUN groupadd -r aiofast && \
    useradd -r -g aiofast -d /app -s /sbin/nologin aiofast

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY core/ core/
COPY app/ app/
COPY config/ config/
COPY routes/ routes/
COPY database/ database/
COPY bootstrap/ bootstrap/
COPY main.py aiocraft.py aiocraft ./
COPY docker/entrypoint.sh /entrypoint.sh

RUN mkdir -p storage/logs storage/cache storage/locks bootstrap/cache && \
    chown -R aiofast:aiofast /app

RUN chmod +x /entrypoint.sh /app/aiocraft

USER aiofast

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["tini", "--", "/entrypoint.sh"]
CMD ["serve"]