# Contributing

Contributions are welcome! Here's how to add or improve skills.

## Adding a New Skill

1. Create a directory under `skills/` with your skill name (lowercase, hyphens only)
2. Add a `SKILL.md` with valid YAML frontmatter:
   - `name` — must match directory name
   - `description` — include trigger phrases like "Use when the user wants to..."
   - `license` — MIT
   - `metadata.author` — your GitHub username
3. Add `evals/evals.json` with at least 2 test prompts
4. Run `bash validate-skills.sh` to verify
5. Submit a pull request

## SKILL.md Guidelines

- Keep SKILL.md under 500 lines and 5,000 tokens
- Put detailed content in a `references/` subdirectory
- For tool skills, put scripts in a `scripts/` subdirectory
- Use trigger-phrase-rich descriptions for better discovery

## Skill Name Rules

- 1-64 characters
- Lowercase `a-z`, numbers, hyphens only
- No leading/trailing/consecutive hyphens
- Must match the directory name

## Code of Conduct

Be respectful and constructive. We're all learning.
