#!/usr/bin/env bash
# Aegis dev launcher (macOS / Linux).
#
# Starts the backend (FastAPI / ADK) and the frontend (Next.js) together,
# streams interleaved logs with [backend] / [frontend] prefixes, and
# cleans up both processes on Ctrl-C.
#
# Usage:
#   ./scripts/dev.sh              # both
#   ./scripts/dev.sh backend      # backend only
#   ./scripts/dev.sh frontend     # frontend only
#
# Env overrides:
#   BACKEND_PORT   default 8000
#   FRONTEND_PORT  default 3000
#   BACKEND_HOST   default 127.0.0.1
#   SKIP_BACKEND=1 / SKIP_FRONTEND=1 to skip one side without arg

set -u
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"

target="${1:-both}"
case "$target" in
  both|backend|frontend) ;;
  *) echo "usage: $0 [both|backend|frontend]" >&2; exit 2 ;;
esac

# --- Color prefix helpers --------------------------------------------------

# Colors are applied only to the prefix label, never to the underlying log
# stream (so framework colors pass through cleanly).
if [ -t 1 ]; then
  C_BACKEND="$(printf '\033[38;5;108m')"   # sage-ish for backend
  C_FRONTEND="$(printf '\033[38;5;215m')"  # warm clay for frontend
  C_INFO="$(printf '\033[38;5;245m')"
  C_ERR="$(printf '\033[38;5;167m')"
  C_RESET="$(printf '\033[0m')"
else
  C_BACKEND=""; C_FRONTEND=""; C_INFO=""; C_ERR=""; C_RESET=""
fi

info()  { printf "%s[dev]%s %s\n" "$C_INFO" "$C_RESET" "$*" >&2; }
warn()  { printf "%s[dev]%s %s\n" "$C_ERR"  "$C_RESET" "$*" >&2; }

prefix_stream() {
  # Reads stdin, prefixes each line with a colored tag.
  local label="$1" color="$2"
  awk -v label="$label" -v color="$color" -v reset="$C_RESET" \
    '{ printf "%s[%s]%s %s\n", color, label, reset, $0; fflush() }'
}

# --- Tool checks -----------------------------------------------------------

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    warn "missing required tool: $1"
    return 1
  fi
}

needs_backend()  { [ "$target" = "both" ] || [ "$target" = "backend" ]; }
needs_frontend() { [ "$target" = "both" ] || [ "$target" = "frontend" ]; }

if [ "${SKIP_BACKEND:-0}"  = "1" ]; then target="frontend"; fi
if [ "${SKIP_FRONTEND:-0}" = "1" ]; then target="backend";  fi

if needs_backend && [ ! -d "$BACKEND_DIR" ]; then
  warn "backend dir not found at $BACKEND_DIR — skipping backend"
  target="frontend"
fi
if needs_frontend && [ ! -d "$FRONTEND_DIR" ]; then
  warn "frontend dir not found at $FRONTEND_DIR — skipping frontend"
  target="backend"
fi

if needs_backend; then
  require uv || { warn "Install: https://docs.astral.sh/uv/getting-started/"; exit 1; }
fi
if needs_frontend; then
  require pnpm || { warn "Install: brew install pnpm"; exit 1; }
fi

# --- Process bookkeeping ---------------------------------------------------

BACKEND_PID=""
FRONTEND_PID=""

CLEANED_UP=0
cleanup() {
  if [ "$CLEANED_UP" = "1" ]; then return; fi
  CLEANED_UP=1
  trap '' INT TERM
  info "shutting down…"
  for pid in "$BACKEND_PID" "$FRONTEND_PID"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done
  # Give them up to 5s to exit gracefully, then SIGKILL.
  local deadline=$(( $(date +%s) + 5 ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    local alive=0
    for pid in "$BACKEND_PID" "$FRONTEND_PID"; do
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then alive=1; fi
    done
    [ "$alive" = "0" ] && break
    sleep 0.2
  done
  for pid in "$BACKEND_PID" "$FRONTEND_PID"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  done
  info "stopped"
}

trap cleanup INT TERM EXIT

# --- Launchers -------------------------------------------------------------

start_backend() {
  info "starting backend on http://$BACKEND_HOST:$BACKEND_PORT (uvicorn, --reload)"
  (
    cd "$BACKEND_DIR" || exit 1
    # Load .env from repo root if present, then pass through.
    if [ -f "$ROOT/.env" ]; then
      # Source .env but skip empty assignments — an empty
      # GOOGLE_APPLICATION_CREDENTIALS= would shadow the gcloud ADC chain.
      while IFS='=' read -r key val; do
        key="$(echo "$key" | xargs)"
        case "$key" in ''|\#*) continue ;; esac
        [ -n "$val" ] || continue
        export "$key=$val"
      done < "$ROOT/.env"
    fi
    exec uv run uvicorn app.fast_api_app:app \
      --host "$BACKEND_HOST" \
      --port "$BACKEND_PORT" \
      --reload
  ) 2>&1 | prefix_stream "backend" "$C_BACKEND" &
  BACKEND_PID=$!
}

start_frontend() {
  info "starting frontend on http://localhost:$FRONTEND_PORT (next dev)"
  (
    cd "$FRONTEND_DIR" || exit 1
    export NEXT_PUBLIC_BACKEND_URL="${NEXT_PUBLIC_BACKEND_URL:-http://$BACKEND_HOST:$BACKEND_PORT}"
    export PORT="$FRONTEND_PORT"
    exec pnpm dev
  ) 2>&1 | prefix_stream "frontend" "$C_FRONTEND" &
  FRONTEND_PID=$!
}

case "$target" in
  both)
    start_backend
    start_frontend
    ;;
  backend)
    start_backend
    ;;
  frontend)
    start_frontend
    ;;
esac

# --- Readiness probes ------------------------------------------------------

# Wait up to 30s for the backend /health endpoint to respond.
# ADK initialization can be slow on first run.
if needs_backend && [ -n "$BACKEND_PID" ]; then
  health_url="http://$BACKEND_HOST:$BACKEND_PORT/health"
  deadline=$(( $(date +%s) + 30 ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    if curl -sf "$health_url" >/dev/null 2>&1; then
      info "backend ready ✓  $health_url"
      break
    fi
    sleep 1
  done
  if ! curl -sf "$health_url" >/dev/null 2>&1; then
    warn "backend did not become ready within 30s (check logs above)"
  fi
fi

if needs_frontend && [ -n "$FRONTEND_PID" ]; then
  info "frontend starting on http://localhost:$FRONTEND_PORT"
fi

info "press Ctrl-C to stop"

# Wait for any child to exit; if one dies, take the other down.
while :; do
  if [ -n "$BACKEND_PID" ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    warn "backend exited"
    BACKEND_PID=""
    break
  fi
  if [ -n "$FRONTEND_PID" ] && ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    warn "frontend exited"
    FRONTEND_PID=""
    break
  fi
  sleep 0.5
done
