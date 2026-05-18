---
name: z-library-books
description: Authenticate to Z-Library and search/download books. Use when the user asks to search Z-Library, download books from Z-Library, or manage Z-Library authentication.
---

# Z-Library Books

Use this skill to authenticate to Z-Library, search for books, and download PDF/EPUB files.

> **Original repo:** [FlashLit/z-library-books](https://github.com/FlashLit/z-library-books)

## Safety and Privacy

- Never print full `remix_userid`, `remix_userkey`, passwords, or other credentials unless the user explicitly asks.
- Auth cookies are cached at `~/.config/zlibrary-pi/auth.json` with `0600` permissions.
- Prefer prompting securely for passwords; do not store the Z-Library password.
- This skill is search/metadata oriented. Do not download or redistribute copyrighted books. Use results only for lawful/public-domain/user-owned content workflows.

## Configuration

The scripts are located in the project directory under `src/`:

- `src/browser_client.py` - Playwright-based client for login, search, download
- `src/browser_search.py` - CLI tool for browser-based operations

Defaults:

- Z-Library base: `https://z-library.im`
- Auth cache: `~/.config/zlibrary-pi/auth.json`

## Prerequisites

- Python 3.11+
- Playwright: `pip install playwright && python3 -m playwright install chromium`
- Network proxy (if needed): set `HTTPS_PROXY` and `HTTP_PROXY`

## Commands

All commands require the proxy environment variable if network access needs it.

### Login

```bash
HTTPS_PROXY="http://127.0.0.1:7897" python3 <skill_dir>/src/browser_search.py login --email "you@example.com" --password "yourpassword"
```

### Check auth status

```bash
python3 <skill_dir>/src/browser_search.py status
```

### Search books

```bash
HTTPS_PROXY="http://127.0.0.1:7897" python3 <skill_dir>/src/browser_search.py search "plato republic" --limit 10
```

Options:

```bash
--json        # Output as JSON
--ids         # Show Z-Library book IDs and hashes
--limit N     # Max results (default 10)
```

### Download a book

```bash
HTTPS_PROXY="http://127.0.0.1:7897" python3 <skill_dir>/src/browser_search.py download <id> <hash> -o ./downloads
```

### Logout

```bash
python3 <skill_dir>/src/browser_search.py logout
```

## Workflow

When the user asks to search or download from Z-Library:

1. Run `python3 <skill_dir>/src/browser_search.py status` to check auth.
2. If not authenticated, run `login` and let the user provide credentials securely.
3. Run `search "<query>" --limit <n>` to find books.
4. Summarize the results: title, author, year, extension, file size.
5. If the user wants to download, run `download <id> <hash> -o <path>`.

## Known Issues

- Z-Library has anti-bot protection requiring JavaScript execution. The `browser_client.py` uses Playwright to bypass this.
- Connection may be intermittent. Retry if `ERR_CONNECTION_CLOSED` occurs.
