#!/usr/bin/env bash
# Mac launchd installer for sec-scanner daily pull.
# Schedule: weekdays 09:30 local time (just before US market open ET).
# Idempotent: safe to re-run.
set -euo pipefail

# Resolve project root (one level above scripts/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

LABEL="com.peleg.sec-scanner"
PLIST_PATH="${HOME}/Library/LaunchAgents/${LABEL}.plist"
RUNNER_PATH="${SCRIPT_DIR}/launchd-runner.sh"
LOG_DIR="${PROJECT_DIR}/data/logs"
mkdir -p "${LOG_DIR}"
mkdir -p "$(dirname "${PLIST_PATH}")"

# Write a dedicated runner. This avoids embedding PROJECT_DIR (which may
# contain spaces or XML-special chars) into the plist ProgramArguments.
# The chain stops if live-pull fails: no point deriving alerts off stale data.
cat > "${RUNNER_PATH}" <<'RUNNER_EOF'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "${HERE}/.." && pwd)"
cd "${PROJECT}"
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi
python3 scripts/live-pull.py
python3 scripts/derive-alerts.py
RUNNER_EOF
chmod +x "${RUNNER_PATH}"

# XML-escape the runner path (& < > " ') before embedding in plist.
xml_escape() {
  local s="$1"
  s="${s//&/&amp;}"
  s="${s//</&lt;}"
  s="${s//>/&gt;}"
  s="${s//\"/&quot;}"
  s="${s//\'/&apos;}"
  printf '%s' "$s"
}

RUNNER_XML="$(xml_escape "${RUNNER_PATH}")"
PROJECT_XML="$(xml_escape "${PROJECT_DIR}")"
LOG_OUT_XML="$(xml_escape "${LOG_DIR}/launchd.out.log")"
LOG_ERR_XML="$(xml_escape "${LOG_DIR}/launchd.err.log")"

cat > "${PLIST_PATH}" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${RUNNER_XML}</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>30</integer></dict>
  </array>
  <key>WorkingDirectory</key>
  <string>${PROJECT_XML}</string>
  <key>StandardOutPath</key>
  <string>${LOG_OUT_XML}</string>
  <key>StandardErrorPath</key>
  <string>${LOG_ERR_XML}</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
PLIST_EOF

# Reload (idempotent).
launchctl unload "${PLIST_PATH}" >/dev/null 2>&1 || true
launchctl load "${PLIST_PATH}"

echo "התקנה הושלמה בהצלחה."
echo "הסקנר ירוץ אוטומטית בימי ראשון עד חמישי בשעה 09:30."
echo "פלט: ${LOG_DIR}/launchd.out.log"
echo "שגיאות: ${LOG_DIR}/launchd.err.log"
echo ""
echo "להסרה: ${SCRIPT_DIR}/uninstall-launchd.sh"
echo "או ידנית: launchctl unload ${PLIST_PATH} && rm ${PLIST_PATH}"
