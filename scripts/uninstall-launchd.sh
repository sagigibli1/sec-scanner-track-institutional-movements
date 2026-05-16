#!/usr/bin/env bash
# Mac launchd uninstaller for sec-scanner daily pull.
# Idempotent: safe to run even if not installed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LABEL="com.peleg.sec-scanner"
PLIST_PATH="${HOME}/Library/LaunchAgents/${LABEL}.plist"
RUNNER_PATH="${SCRIPT_DIR}/launchd-runner.sh"

if [ -f "${PLIST_PATH}" ]; then
  launchctl unload "${PLIST_PATH}" >/dev/null 2>&1 || true
  rm -f "${PLIST_PATH}"
  echo "הוסר: ${PLIST_PATH}"
else
  echo "לא הותקן: ${PLIST_PATH} לא קיים."
fi

if [ -f "${RUNNER_PATH}" ]; then
  rm -f "${RUNNER_PATH}"
  echo "הוסר: ${RUNNER_PATH}"
fi

echo "הסרה הושלמה."
