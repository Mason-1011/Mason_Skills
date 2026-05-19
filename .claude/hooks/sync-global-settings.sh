#!/bin/bash
# Sync project skills to global Claude settings via symlinks in ~/.claude/skills/
set -e

PROJECT_ROOT="/Users/mason_yu/Projects/Mason_Skills"
SKILLS_DIR="$PROJECT_ROOT/.claude/skills"
GLOBAL_SKILLS="$HOME/.claude/skills"

[ ! -d "$SKILLS_DIR" ] && exit 0
mkdir -p "$GLOBAL_SKILLS"

# Symlink each project skill to global ~/.claude/skills/
for skill_dir in "$SKILLS_DIR"/*/; do
  [ ! -d "$skill_dir" ] && continue
  skill_name=$(basename "$skill_dir")
  target="$GLOBAL_SKILLS/$skill_name"

  # Skip if already points to the right place
  if [ -L "$target" ]; then
    current=$(readlink "$target" 2>/dev/null || true)
    if [ "$current" = "$skill_dir" ] || [ "$current" = "${skill_dir%/}" ]; then
      continue
    fi
  fi

  # Remove existing (non-symlink directory or broken link)
  if [ -e "$target" ] || [ -L "$target" ]; then
    rm -rf "$target"
  fi

  # Create symlink
  ln -s "$skill_dir" "$target"
done

echo '{"systemMessage":"Skills synced to global ~/.claude/skills/"}'
