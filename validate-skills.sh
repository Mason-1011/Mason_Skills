#!/bin/bash
# Validate all skills in the skills/ directory
# Checks SKILL.md format, required frontmatter fields, and name conventions
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"
ERRORS=0

if [ ! -d "$SKILLS_DIR" ]; then
  echo "ERROR: skills/ directory not found"
  exit 1
fi

for skill_dir in "$SKILLS_DIR"/*/; do
  [ ! -d "$skill_dir" ] && continue
  skill_name=$(basename "$skill_dir")
  skill_md="$skill_dir/SKILL.md"

  echo -n "Checking $skill_name... "

  # Check SKILL.md exists
  if [ ! -f "$skill_md" ]; then
    echo "FAIL: missing SKILL.md"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  # Check name format: lowercase, numbers, hyphens only
  if ! echo "$skill_name" | grep -qE '^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z][a-z0-9]$'; then
    echo "WARN: directory name '$skill_name' may not match naming rules"
  fi

  # Check required frontmatter fields
  content=$(cat "$skill_md")

  if ! echo "$content" | head -20 | grep -q "^name:"; then
    echo "FAIL: missing 'name' in frontmatter"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  if ! echo "$content" | head -20 | grep -q "^description:"; then
    echo "FAIL: missing 'description' in frontmatter"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  # Check description has trigger phrases
  desc=$(echo "$content" | head -20 | grep "^description:" | head -1)
  if ! echo "$desc" | grep -qi "use when\|when the user\|invoke"; then
    echo "WARN: description may lack trigger phrases"
  fi

  # Check name matches directory
  frontmatter_name=$(echo "$content" | head -20 | grep "^name:" | head -1 | sed 's/^name: *//')
  if [ "$frontmatter_name" != "$skill_name" ]; then
    echo "FAIL: frontmatter name '$frontmatter_name' doesn't match directory '$skill_name'"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  # Check line count
  lines=$(wc -l < "$skill_md")
  if [ "$lines" -gt 500 ]; then
    echo "WARN: $lines lines (recommended < 500)"
  else
    echo "OK ($lines lines)"
  fi
done

echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "FAILED: $ERRORS skill(s) have errors"
  exit 1
else
  echo "All skills validated successfully"
fi
