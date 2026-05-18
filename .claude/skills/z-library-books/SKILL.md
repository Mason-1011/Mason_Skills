---
name: z-library-books
description: Authenticate to Z-Library and search/download books. Use when the user asks to search Z-Library, download books from Z-Library, find ebooks, or manage Z-Library authentication.
---

# Z-Library Books

Search and download books from Z-Library using browser automation to bypass anti-bot protection.

## Prerequisites

- Python 3.11+
- Playwright: `pip install playwright && python3 -m playwright install chromium`
- Network proxy: set `HTTPS_PROXY` and `HTTP_PROXY` environment variables

## Script Location

The scripts are in the project's `src/` directory (relative to this SKILL.md):

```
<project_root>/src/browser_client.py   # Playwright-based client
<project_root>/src/browser_search.py   # CLI tool
```

Define a variable for convenience:

```bash
SKILL_DIR="<path_to_this_skill_directory>"
SCRIPT="$SKILL_DIR/../../src/browser_search.py"
```

## Commands

### Login

```bash
HTTPS_PROXY="$HTTPS_PROXY" HTTP_PROXY="$HTTP_PROXY" python3 "$SCRIPT" login --email "user@email.com" --password "password"
```

### Check auth status

```bash
python3 "$SCRIPT" status
```

### Search books

```bash
HTTPS_PROXY="$HTTPS_PROXY" HTTP_PROXY="$HTTP_PROXY" python3 "$SCRIPT" search "book title" --limit 10
```

Options: `--json` (JSON output), `--ids` (show book IDs)

### Download a book

```bash
HTTPS_PROXY="$HTTPS_PROXY" HTTP_PROXY="$HTTP_PROXY" python3 "$SCRIPT" download <id> <hash> -o ./downloads
```

### Logout

```bash
python3 "$SCRIPT" logout
```

## Workflow

1. Run `status` to check auth.
2. If not authenticated, run `login` and let the user provide credentials securely.
3. Run `search "<query>" --limit <n>` to find books.
4. Summarize: title, author, year, extension, file size.
5. If download requested, run `download <id> <hash> -o <path>`.

## Safety

- Never print full `remix_userid`, `remix_userkey`, or passwords unless explicitly asked.
- Auth cookies cached at `~/.config/zlibrary-pi/auth.json` (0600 permissions).
- Do not download or redistribute copyrighted books. Use only for lawful/public-domain/user-owned content.
