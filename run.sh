#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/seomind ] || { echo "SeoMind is not installed. Run ./setup.sh first."; exit 1; }
[ -d apps/web/node_modules ] || { echo "Web dependencies are missing. Run ./setup.sh first."; exit 1; }

cleanup() {
  kill "${API_PID:-}" "${WEB_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

.venv/bin/seomind & API_PID=$!
(cd apps/web && npm start) & WEB_PID=$!

sleep 2
if command -v xdg-open >/dev/null 2>&1; then xdg-open http://127.0.0.1:3000 >/dev/null 2>&1 || true; elif command -v open >/dev/null 2>&1; then open http://127.0.0.1:3000 >/dev/null 2>&1 || true; fi

echo "SeoMind Web: http://127.0.0.1:3000"
echo "SeoMind API: http://127.0.0.1:8787"
wait
