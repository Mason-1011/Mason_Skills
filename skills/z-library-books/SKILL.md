---
name: z-library-books
description: "Authenticate to Z-Library and search/download books using browser automation. Use when the user wants to search Z-Library, download books from Z-Library, find ebooks, or manage Z-Library authentication."
license: MIT
metadata:
  author: Mason-1011
  compatibility: claude-code
---

# Z-Library Books

Search and download books from Z-Library using browser automation to bypass anti-bot protection.

## Prerequisites

- Python 3.11+
- Playwright: `pip install playwright && python3 -m playwright install chromium`
- Network proxy: set `HTTPS_PROXY` and `HTTP_PROXY` environment variables

## Scripts

All scripts are in this skill's `scripts/` directory:

```
<script_dir>/browser_client.py   # Playwright-based client
<script_dir>/browser_search.py   # CLI tool
```

Define a variable for convenience:

```bash
SCRIPT_DIR="<this_skill_dir>/scripts"
```

## Commands

### Login

```bash
HTTPS_PROXY="$HTTPS_PROXY" HTTP_PROXY="$HTTP_PROXY" python3 "$SCRIPT_DIR/browser_search.py" login --email "user@email.com" --password "password"
```

### Check auth status

```bash
python3 "$SCRIPT_DIR/browser_search.py" status
```

### Search books

```bash
HTTPS_PROXY="$HTTPS_PROXY" HTTP_PROXY="$HTTP_PROXY" python3 "$SCRIPT_DIR/browser_search.py" search "book title" --limit 10
```

Options: `--json` (JSON output), `--ids` (show book IDs)

### Download a book

```bash
HTTPS_PROXY="$HTTPS_PROXY" HTTP_PROXY="$HTTP_PROXY" python3 "$SCRIPT_DIR/browser_search.py" download <id> <hash> -o ./downloads
```

### Logout

```bash
python3 "$SCRIPT_DIR/browser_search.py" logout
```

### Find working domain

Scan known Z-Library mirror domains and find which ones are accessible:

```bash
HTTPS_PROXY="$HTTPS_PROXY" HTTP_PROXY="$HTTP_PROXY" python3 "$SCRIPT_DIR/browser_search.py" find-domain
```

Options: `--timeout` (seconds per domain, default 10)

### Check site access

Test if the current Z-Library domain is reachable:

```bash
HTTPS_PROXY="$HTTPS_PROXY" HTTP_PROXY="$HTTP_PROXY" python3 "$SCRIPT_DIR/browser_search.py" check-access
```

Options: `--domain` (override domain), `--timeout` (seconds, default 10)

### Check environment credentials

Verify that `ZLIBRARY_EMAIL` and `ZLIBRARY_PASSWORD` are set:

```bash
python3 "$SCRIPT_DIR/browser_search.py" check-env
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
