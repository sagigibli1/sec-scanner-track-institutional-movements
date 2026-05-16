#!/usr/bin/env bash
# pdf.sh - one-shot: live pull → dashboard render → Chrome-headless PDF.
# Uses Chrome headless instead of weasyprint (no system-lib dependency).
# Requires: Google Chrome installed at /Applications/Google Chrome.app,
# http.server running on 127.0.0.1:8080 (started separately), .env sourced.

set -euo pipefail
cd "$(dirname "$0")/.."

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DATE="$(date +%Y-%m-%d)"
PORT="${SEC_SCANNER_PORT:-8080}"
OUT="data/reports/sec-scanner-dashboard-${DATE}.pdf"

if [ ! -x "$CHROME" ]; then
  echo "Chrome לא נמצא ב-$CHROME. תתקין Google Chrome." >&2
  exit 1
fi

# Load env if .env exists and FMP_API_KEY not already set
if [ -f .env ] && [ -z "${FMP_API_KEY:-}" ]; then
  set -a; source .env; set +a
fi

if [ -z "${FMP_API_KEY:-}" ]; then
  echo "FMP_API_KEY חסר. הרץ: source .env" >&2
  exit 1
fi

# Check server is up
if ! curl -fs -o /dev/null "http://127.0.0.1:${PORT}/index.html"; then
  echo "השרת לא רץ על ${PORT}. הפעל: python3 -m http.server ${PORT} --directory outputs/dashboard --bind 127.0.0.1" >&2
  exit 1
fi

echo "1/3 שולף נתונים חיים מ-FMP + SEC..."
python3 scripts/live-pull.py

echo "2/3 מרענן את ה-JSON של הדשבורד..."
python3 outputs/dashboard/render.py

echo "3/3 מייצר PDF דרך Chrome..."
mkdir -p data/reports
"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-pdf-header-footer \
  --print-to-pdf-no-header \
  --virtual-time-budget=4000 \
  --print-to-pdf="${OUT}" \
  "http://127.0.0.1:${PORT}" 2>&1 | grep -v -E "Trying to load|externally_managed_app|Web Apps not enabled" || true

if [ -s "${OUT}" ]; then
  SIZE=$(ls -lh "${OUT}" | awk '{print $5}')
  echo ""
  echo "בוצע. ${OUT} (${SIZE})"
  open "${OUT}"
else
  echo "כשלון - PDF לא נוצר" >&2
  exit 1
fi
