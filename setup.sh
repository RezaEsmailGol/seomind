#!/usr/bin/env bash
set -euo pipefail

echo
echo "=========================================="
echo "  SeoMind Setup - Linux / macOS"
echo "=========================================="
echo

PYTHON_BIN=""

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[ERROR] Python 3.11 or newer was not found."
  exit 1
fi

echo "[1/4] Checking Python..."
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' || {
  echo "[ERROR] SeoMind requires Python 3.11 or newer."
  exit 1
}

echo "[2/4] Creating virtual environment..."
if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

echo "[3/4] Installing SeoMind..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

echo "[4/4] Starting SeoMind..."
echo
echo "SeoMind:  http://127.0.0.1:8787"
echo "API docs: http://127.0.0.1:8787/docs"
echo

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://127.0.0.1:8787/docs >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open http://127.0.0.1:8787/docs >/dev/null 2>&1 || true
fi

.venv/bin/seomind
