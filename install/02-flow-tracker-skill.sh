#!/usr/bin/env bash
# 02-flow-tracker-skill.sh
# Clones the Institutional Flow Tracker skill from tradermonty/claude-trading-skills
# and copies the relevant subfolder into ~/.claude/skills/institutional-flow-tracker/
# Idempotent: skips if the skill folder already exists.

set -euo pipefail

REPO_URL="https://github.com/tradermonty/claude-trading-skills.git"
SKILL_SUBPATH="skills/institutional-flow-tracker"
SKILLS_DIR="${HOME}/.claude/skills"
SKILL_TARGET="${SKILLS_DIR}/institutional-flow-tracker"

echo ""
echo "מתקין את Institutional Flow Tracker Skill"
echo "------------------------------------------"

# Check prereqs
if ! command -v git >/dev/null 2>&1; then
  echo "שגיאה: לא נמצא git. תתקין git ונסה שוב."
  exit 1
fi

# Idempotency check: if the skill already exists and has SKILL.md, we're done
if [ -d "${SKILL_TARGET}" ] && [ -f "${SKILL_TARGET}/SKILL.md" ]; then
  echo "ה-Skill כבר קיים בנתיב ${SKILL_TARGET}, מדלגים."
  echo "אם אתה רוצה להחליף לגרסה חדשה, מחק את התיקייה ידנית והרץ שוב."
  exit 0
fi

# Make sure parent skills dir exists
mkdir -p "${SKILLS_DIR}"

# Clone to a temp dir we control. mktemp -d works on Mac bash 3.2.
tmp_clone_dir=$(mktemp -d -t cts-clone-XXXXXX)
trap 'rm -rf "${tmp_clone_dir}"' EXIT

echo "מוריד את הריפו של tradermonty/claude-trading-skills..."
clone_output=""
if ! clone_output=$(git clone --depth 1 "${REPO_URL}" "${tmp_clone_dir}/repo" 2>&1); then
  echo "שגיאה: git clone נכשל. הפלט:"
  echo "${clone_output}"
  exit 1
fi

src="${tmp_clone_dir}/repo/${SKILL_SUBPATH}"
if [ ! -d "${src}" ] || [ ! -f "${src}/SKILL.md" ]; then
  echo "שגיאה: לא מצאתי את תיקיית ה-skill בריפו (${SKILL_SUBPATH}). יכול להיות שהריפו עבר ארגון מחדש."
  exit 1
fi

echo "מעתיק את ה-skill ל-${SKILL_TARGET}..."
cp -R "${src}" "${SKILL_TARGET}"

echo ""
echo "בוצע. ה-skill הותקן ב-${SKILL_TARGET}."
echo "סגור את Claude Code ופתח מחדש כדי שיזהה את ה-skill."
echo "כדי להפעיל, תכתוב בקלוד קוד: screen for stocks with significant institutional ownership changes"
