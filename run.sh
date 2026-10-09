#!/usr/bin/env bash
# ============================================================
# SingleCellX startup script
# ------------------------------------------------------------
# 1. Verifies Python >= 3.10 is available
# 2. Installs backend dependencies (idempotent)
# 3. Launches Uvicorn with auto-reload
# ------------------------------------------------------------
# Usage:
#   chmod +x run.sh
#   ./run.sh                 # default port 8000
#   PORT=8080 ./run.sh       # override port
#   ./run.sh --no-install    # skip dependency installation
# ============================================================

set -euo pipefail

# ----- Configuration -----
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
SKIP_INSTALL=0
RELOAD="--reload"

for arg in "$@"; do
  case "$arg" in
    --no-install)  SKIP_INSTALL=1 ;;
    --no-reload)   RELOAD="" ;;
    --prod)        RELOAD="" ;;
    *)             echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

cd "$(dirname "$0")"
PROJECT_ROOT="$(pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

# ----- Colour helpers -----
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${CYAN}▸${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}!${NC} $1"; }
err()   { echo -e "${RED}✗${NC} $1" >&2; }

# ----- Python check -----
if ! command -v python3 >/dev/null 2>&1; then
  err "python3 not found on PATH. Install Python 3.10 or newer."
  exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  err "Python $PY_VERSION detected; need Python >= 3.10."
  exit 1
fi
ok "Python $PY_VERSION"

# ----- Dependencies -----
if [ "$SKIP_INSTALL" -eq 0 ]; then
  info "Installing backend dependencies (this may take a minute on first run)…"
  if python3 -m pip install -q -r "$BACKEND_DIR/requirements.txt" 2>/dev/null; then
    ok "Dependencies installed"
  elif python3 -m pip install -q --break-system-packages -r "$BACKEND_DIR/requirements.txt" 2>/dev/null; then
    ok "Dependencies installed (system-wide)"
  else
    warn "pip install reported issues. Trying to start anyway…"
  fi
else
  info "Skipping dependency install (--no-install)"
fi

# ----- Create runtime directories -----
mkdir -p "$BACKEND_DIR/data" "$BACKEND_DIR/uploads" "$BACKEND_DIR/storage"
ok "Runtime directories ready"

# ----- Launch -----
echo ""
info "Starting SingleCellX on http://$HOST:$PORT"
info "Interactive API docs: http://$HOST:$PORT/docs"
echo ""

cd "$BACKEND_DIR"
exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT" $RELOAD
