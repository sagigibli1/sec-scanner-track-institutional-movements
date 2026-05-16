#!/usr/bin/env bash
# setup.sh
# Top-level installer for SEC Scanner.
# Runs install/01-edgartools-mcp.sh and install/02-flow-tracker-skill.sh.
# Idempotent: each child script handles its own "already installed" case.

set -euo pipefail

# Resolve the build/ root regardless of where this script is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_DIR="${BUILD_ROOT}/install"

echo ""
echo "==========================================="
echo "  התקנת SEC Scanner - מעקב SEC + מוסדיים"
echo "==========================================="
echo ""

# --- Prerequisite checks -----------------------------------------------------

prereqs_ok=true

if ! command -v claude >/dev/null 2>&1; then
  echo "חסר: Claude Code CLI (פקודת claude). תתקין מ-https://claude.com/code"
  prereqs_ok=false
else
  echo "נמצא: Claude Code CLI"
fi

if ! command -v git >/dev/null 2>&1; then
  echo "חסר: git. תתקין עם xcode-select --install"
  prereqs_ok=false
else
  echo "נמצא: git"
fi

# uvx is used by the local Path B flavor of EdgarTools. The default course path
# (hosted MCP) does NOT need it, but we warn so power users know.
if ! command -v uvx >/dev/null 2>&1; then
  echo "אזהרה: לא נמצא uvx. זה לא חוסם, צריך רק אם תרצה לעבור ל-EdgarTools המקומי."
else
  echo "נמצא: uvx"
fi

if [ "${prereqs_ok}" != "true" ]; then
  echo ""
  echo "התקן את החסרים ונסה שוב."
  exit 1
fi

echo ""
echo "-------------------------------------------"
echo "  שלב 1/2 - EdgarTools MCP"
echo "-------------------------------------------"
bash "${INSTALL_DIR}/01-edgartools-mcp.sh"

echo ""
echo "-------------------------------------------"
echo "  שלב 2/2 - Institutional Flow Tracker"
echo "-------------------------------------------"
bash "${INSTALL_DIR}/02-flow-tracker-skill.sh"

# --- Final instructions ------------------------------------------------------

echo ""
echo "==========================================="
echo "  ההתקנה הסתיימה. מה עכשיו?"
echo "==========================================="
echo ""
echo "1. תפתח את הקובץ install/03-env-setup.md ותעבור על השלבים שם."
echo "   קודם הרשמה ל-FMP, העתקת המפתח, והוספה ל-~/.zshrc."
echo "2. אחרי שהוספת את המפתח, הרץ: source ~/.zshrc"
echo "3. בדוק שהכל תקין: bash scripts/verify.sh"
echo "4. הפעם הראשונה שתשאל את קלוד שאלה שמשתמשת ב-EdgarTools - יפתח דפדפן."
echo "   תתחבר עם גוגל פעם אחת ויסגר."
echo ""
echo "כל ה-skill מופעל אוטומטית כשתכתוב משהו כמו:"
echo "  screen for stocks with significant institutional ownership changes"
echo ""
