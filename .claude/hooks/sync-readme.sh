#!/bin/bash
# Sync skills from .claude/skills/ to README.md Skills section
# Extracts ### headers + first description line as "name - description"
set -e

PROJECT_ROOT="/Users/mason_yu/Projects/Mason_Skills"
SKILLS_DIR="$PROJECT_ROOT/.claude/skills"
README="$PROJECT_ROOT/README.md"

[ ! -d "$SKILLS_DIR" ] && exit 0

skip_section() {
  case "$1" in
    "Setup"*|"Error Handling"|"Notes"|"Token Auto-Login"|"Commands") return 0 ;;
  esac
  return 1
}

SKILLS_BODY=""
for skill_dir in "$SKILLS_DIR"/*/; do
  [ ! -d "$skill_dir" ] && continue
  skill_md="$skill_dir/SKILL.md"
  [ ! -f "$skill_md" ] && continue

  skill_name=$(basename "$skill_dir")
  SKILLS_BODY="${SKILLS_BODY}### ${skill_name}"$'\n\n'

  in_header=false
  in_code=false
  header=""
  desc=""
  item_num=0

  while IFS= read -r line; do
    # Toggle code block state
    if [[ "$line" =~ ^\`\`\` ]]; then
      in_code=$in_code  # toggle
      if $in_code; then in_code=false; else in_code=true; fi
      continue
    fi
    # Skip everything inside code blocks
    $in_code && continue

    # ### headers = features
    if [[ "$line" =~ ^###[[:space:]]+(.*) ]]; then
      # Flush previous item
      if [ -n "$header" ]; then
        skip_section "$header" && { header=""; desc=""; continue; }
        item_num=$((item_num + 1))
        if [ -n "$desc" ]; then
          SKILLS_BODY="${SKILLS_BODY}${item_num}. ${header} — ${desc}"$'\n'
        else
          SKILLS_BODY="${SKILLS_BODY}${item_num}. ${header}"$'\n'
        fi
      fi
      header="${BASH_REMATCH[1]}"
      desc=""
      in_header=true
    # Collect first non-empty, non-code, non-html line as description
    elif $in_header && [[ -z "$desc" && -n "$line" && ! "$line" =~ ^# && ! "$line" =~ ^\< && ! "$line" =~ ^\! && ! "$line" =~ ^\[ ]]; then
      clean=$(echo "$line" | sed 's/`//g; s/\*\*//g; s/^ *//')
      [ -n "$clean" ] && desc="$clean" && in_header=false
    # New ## section starts
    elif [[ "$line" =~ ^##[^#] ]]; then
      # Flush last item
      if [ -n "$header" ]; then
        skip_section "$header" || {
          item_num=$((item_num + 1))
          if [ -n "$desc" ]; then
            SKILLS_BODY="${SKILLS_BODY}${item_num}. ${header} — ${desc}"$'\n'
          else
            SKILLS_BODY="${SKILLS_BODY}${item_num}. ${header}"$'\n'
          fi
        }
      fi
      header=""
      desc=""
      in_header=false
    fi
  done < "$skill_md"

  # Flush last item
  if [ -n "$header" ]; then
    skip_section "$header" || {
      item_num=$((item_num + 1))
      if [ -n "$desc" ]; then
        SKILLS_BODY="${SKILLS_BODY}${item_num}. ${header} — ${desc}"$'\n'
      else
        SKILLS_BODY="${SKILLS_BODY}${item_num}. ${header}"$'\n'
      fi
    }
  fi

  SKILLS_BODY="${SKILLS_BODY}"$'\n'"**完整文档：** \`.claude/skills/${skill_name}/SKILL.md\`"$'\n\n'
done

# Replace Skills section in README
SKILLS_BODY="$SKILLS_BODY" README="$README" python -c "
import re, os
readme_path = os.environ['README']
skills_body = os.environ['SKILLS_BODY']

with open(readme_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_section = '## Skills\n\n' + skills_body

pattern = r'## Skills.*?(?=\n## [^#]|\Z)'
if re.search(pattern, content, re.DOTALL):
    content = re.sub(pattern, new_section.rstrip(), content, flags=re.DOTALL)
else:
    content = content.rstrip() + '\n\n' + new_section

with open(readme_path, 'w', encoding='utf-8') as f:
    f.write(content)
"

echo '{"systemMessage":"README.md skills section synced"}'
