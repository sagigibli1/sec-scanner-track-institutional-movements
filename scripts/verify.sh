#!/usr/bin/env bash
# verify.sh
# Sanity-check that the SEC Scanner install actually worked.
# Pass/fail per check, non-zero exit only on hard failures.

# We intentionally do NOT use `set -e` here, because we want to keep running
# all checks even if one fails, then report a summary.
set -u
set -o pipefail

# Resolve the build/ root regardless of cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WATCHLIST_PATH="${BUILD_ROOT}/data/watchlist.json"
SKILL_PATH="${HOME}/.claude/skills/institutional-flow-tracker"
MCP_NAME="edgar_tools"

PASS_MARK="[PASS]"
FAIL_MARK="[FAIL]"
WARN_MARK="[WARN]"

fail_count=0

mark_fail() {
  fail_count=$((fail_count + 1))
}

echo ""
echo "==========================================="
echo "  בדיקת התקנה - SEC Scanner"
echo "==========================================="
echo ""

# --- Check 1: claude CLI present ---------------------------------------------
if command -v claude >/dev/null 2>&1; then
  echo "${PASS_MARK} פקודת claude נמצאה ב-PATH"
else
  echo "${FAIL_MARK} פקודת claude לא נמצאה. תתקין את Claude Code CLI."
  mark_fail
fi

# --- Check 2: edgar-tools MCP registered -------------------------------------
if command -v claude >/dev/null 2>&1; then
  mcp_list_output=""
  if mcp_list_output=$(claude mcp list 2>&1); then
    if printf '%s\n' "${mcp_list_output}" | grep -E -q "^${MCP_NAME}([[:space:]]|:)"; then
      echo "${PASS_MARK} ה-MCP ${MCP_NAME} רשום בקלוד קוד"
    else
      echo "${FAIL_MARK} ה-MCP ${MCP_NAME} לא רשום. הרץ: bash install/01-edgartools-mcp.sh"
      mark_fail
    fi
  else
    echo "${FAIL_MARK} claude mcp list נכשל. הפלט:"
    echo "${mcp_list_output}"
    mark_fail
  fi
else
  echo "${WARN_MARK} מדלגים על בדיקת MCP כי claude לא זמין"
fi

# --- Check 3: skill folder exists --------------------------------------------
if [ -d "${SKILL_PATH}" ] && [ -f "${SKILL_PATH}/SKILL.md" ]; then
  echo "${PASS_MARK} ה-skill קיים בנתיב ${SKILL_PATH}"
else
  echo "${FAIL_MARK} ה-skill חסר. הרץ: bash install/02-flow-tracker-skill.sh"
  mark_fail
fi

# --- Check 4: FMP_API_KEY env var --------------------------------------------
if [ -n "${FMP_API_KEY:-}" ]; then
  echo "${PASS_MARK} משתנה FMP_API_KEY מוגדר"
else
  echo "${FAIL_MARK} FMP_API_KEY לא מוגדר. הוסף ל-~/.zshrc והרץ source ~/.zshrc"
  mark_fail
fi

# --- Check 5: watchlist.json exists and is valid JSON ------------------------
if [ ! -f "${WATCHLIST_PATH}" ]; then
  echo "${FAIL_MARK} watchlist.json חסר בנתיב ${WATCHLIST_PATH}"
  mark_fail
else
  if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import json, sys; json.load(open(sys.argv[1]))" "${WATCHLIST_PATH}" >/dev/null 2>&1; then
      echo "${PASS_MARK} watchlist.json תקין"
    else
      echo "${FAIL_MARK} watchlist.json לא JSON תקין"
      mark_fail
    fi
  else
    echo "${WARN_MARK} python3 לא זמין, מדלגים על אימות JSON"
  fi
fi

# --- Summary -----------------------------------------------------------------
echo ""
echo "-------------------------------------------"
if [ "${fail_count}" -eq 0 ]; then
  echo "כל הבדיקות עברו. SEC Scanner מוכן להפעלה."
  exit 0
else
  echo "${fail_count} בדיקות נכשלו. תקן את מה שמסומן ב-${FAIL_MARK} ונסה שוב."
  exit 1
fi
