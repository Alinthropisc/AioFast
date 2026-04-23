#!/bin/bash
set -euo pipefail

# ── Colors ────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${BLUE}[AioFast]${NC} $1"; }
warn() { echo -e "${YELLOW}[AioFast]${NC} $1"; }
ok() { echo -e "${GREEN}[AioFast]${NC} $1"; }

# ── Wait for services ────────────────────────────────────
wait_for_service() {
    local host="$1"
    local port="$2"
    local service="$3"
    local max_attempts="${4:-30}"
    local attempt=1

    log "Waiting for ${service} at ${host}:${port}..."
    while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('${host}', ${port}))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; do
        if [ "$attempt" -ge "$max_attempts" ]; then
            warn "${service} not available after ${max_attempts} attempts"
            return 1
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    ok "${service} is ready!"
}

# ── Wait for database ────────────────────────────────────
if [ -n "${DATABASE_URL:-}" ]; then
    if echo "$DATABASE_URL" | grep -q "postgresql"; then
        DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
        DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        wait_for_service "${DB_HOST:-localhost}" "${DB_PORT:-5432}" "PostgreSQL"
    fi
fi

# ── Wait for Redis ────────────────────────────────────────
if [ -n "${REDIS_URL:-}" ]; then
    REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    REDIS_PORT=$(echo "$REDIS_URL" | sed -n 's/.*:\([0-9]*\).*/\1/p')
    wait_for_service "${REDIS_HOST:-localhost}" "${REDIS_PORT:-6379}" "Redis"
fi

# ── Run command ───────────────────────────────────────────
case "${1:-serve}" in
    serve)
        ok "Starting AioFast server..."
        ok "Workers: ${SERVER_WORKERS:-4}"
        ok "Host: ${SERVER_HOST:-0.0.0.0}:${SERVER_PORT:-8000}"
        exec python main.py
        ;;

    worker)
        ok "Starting queue worker..."
        # shellcheck disable=SC2068
        exec python -m aiocraft queue:work ${@:2}
        ;;

    scheduler)
        ok "Starting scheduler..."
        exec python -m aiocraft schedule:run
        ;;

    migrate)
        ok "Running migrations..."
        exec python -m aiocraft migrate:run --force
        ;;

    shell)
        ok "Starting Python shell..."
        exec python -i -c "
import asyncio
from core.foundation.application import Application
print('AioFast Shell — use asyncio.run() for async calls')
"
        ;;

    aiocraft)
        # shellcheck disable=SC2068
        exec python -m aiocraft ${@:2}
        ;;

    *)
        exec "$@"
        ;;
esac