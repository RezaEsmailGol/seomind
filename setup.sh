#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "====================================================="
echo "  SeoMind Setup - Linux / macOS"
echo "====================================================="
echo

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then PYTHON_BIN="python3"; elif command -v python >/dev/null 2>&1; then PYTHON_BIN="python"; else echo "[ERROR] Python 3.11+ was not found."; exit 1; fi
command -v node >/dev/null 2>&1 || { echo "[ERROR] Node.js 20+ was not found."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "[ERROR] npm was not found."; exit 1; }

echo "[1/6] Checking Python..."
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' || { echo "[ERROR] Python 3.11+ is required."; exit 1; }

echo "[2/6] Checking Node.js..."
node -e 'const m=Number(process.versions.node.split(".")[0]); process.exit(m >= 20 ? 0 : 1)' || { echo "[ERROR] Node.js 20+ is required."; exit 1; }

echo "[3/6] Creating Python environment..."
[ -d .venv ] || "$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
[ -f .env ] || cp .env.example .env

echo "[4/6] Installing web interface..."
cd apps/web
[ -f .env.local ] || cp .env.local.example .env.local
npm install

echo "[5/6] Building web interface..."
npm run build
cd ../..

echo "[6/6] Setup complete."
./run.sh
