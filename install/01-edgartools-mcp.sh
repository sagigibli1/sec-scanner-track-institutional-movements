#!/usr/bin/env bash
# 01-edgartools-mcp.sh
# Installs the remote EdgarTools MCP server (hosted, OAuth, free 100 calls/day)
# into the local Claude Code CLI.
# Idempotent: re-running does nothing if the MCP is already registered.

set -euo pipefail

MCP_NAME="edgar_tools"
MCP_URL="https://app.edgar.tools/mcp/"

echo ""
echo "מתקין את EdgarTools MCP (הגישה ל-SEC EDGAR)"
echo "---------------------------------------------"

# Check claude CLI exists
if ! command -v claude >/dev/null 2>&1; then
  echo "שגיאה: לא נמצאה הפקודה claude. תתקין קודם את Claude Code CLI ואז תריץ שוב."
  exit 1
fi

# Check if MCP already installed (parse `claude mcp list` for the name)
mcp_list_output=""
if ! mcp_list_output=$(claude mcp list 2>&1); then
  echo "שגיאה: לא הצלחתי להריץ את claude mcp list. הפלט היה:"
  echo "${mcp_list_output}"
  exit 1
fi

if printf '%s\n' "${mcp_list_output}" | grep -E -q "^${MCP_NAME}([[:space:]]|:)"; then
  echo "ה-MCP בשם ${MCP_NAME} כבר מותקן, מדלגים."
  echo "אם משהו לא עובד, הסר אותו ידנית עם: claude mcp remove ${MCP_NAME}"
  exit 0
fi

echo "מוסיף את ה-MCP לקלוד קוד..."
add_output=""
if add_output=$(claude mcp add "${MCP_NAME}" --transport http "${MCP_URL}" 2>&1); then
  echo "${add_output}"
  echo ""
  echo "בוצע. ה-MCP נוסף בהצלחה."
  echo "בפעם הראשונה שתקרא לכלי שלו - יפתח דפדפן עם התחברות גוגל. סוגרים את הטאב אחרי שנכנסים."
else
  echo "שגיאה: ההתקנה נכשלה. הפלט של claude mcp add היה:"
  echo "${add_output}"
  echo "בדוק שיש לך גרסת Claude Code עדכנית והרץ שוב."
  exit 1
fi
