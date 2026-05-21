"""CLI entry point for WeChat Article Fetcher.

Usage:
    python __main__.py login [--timeout N]
    python __main__.py check-token
    python __main__.py search <keyword> [--limit N] [--offset N]
    python __main__.py list <fakeid> [--name NAME] [--pages N] [--interval N]
    python __main__.py fetch <url> [--headed]

All output is JSON to stdout.
"""

import argparse
import io
import json
import os
import sys

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure scripts directory is on sys.path for sibling imports
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)


def output(data: dict):
    """Print JSON result to stdout."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _ensure_token(timeout: int = 300) -> dict | None:
    """Check token validity, auto-trigger login if expired/missing.

    Returns:
        None if token is valid (proceed normally),
        dict with error result if login failed (caller should output and exit).
    """
    from wx_token import check_token_valid
    result = check_token_valid()
    if result["valid"]:
        return None

    # Token expired or missing - auto login
    print(f"Token invalid: {result['message']}", file=sys.stderr)
    print("Starting QR code login...", file=sys.stderr)

    from login import login
    login_result = login(timeout_seconds=timeout)
    if login_result.get("success"):
        print(f"Login successful! Token: {login_result.get('token', '')[:20]}...", file=sys.stderr)
        return None  # proceed with original command

    return login_result  # login failed, return error


def cmd_login(args):
    from login import login
    result = login(timeout_seconds=args.timeout, headless=not args.headed)
    output(result)


def cmd_check_token(args):
    from wx_token import check_token_valid
    result = check_token_valid()
    output({"success": result["valid"], "message": result["message"], "expiry": result["expiry"], "token_path": result["token_path"]})


def cmd_search(args):
    # Auto-login if token expired
    err = _ensure_token()
    if err:
        output(err)
        return

    from search import search_accounts
    result = search_accounts(args.keyword, limit=args.limit, offset=args.offset)
    output(result)


def cmd_list(args):
    # Auto-login if token expired
    err = _ensure_token()
    if err:
        output(err)
        return

    from article_list import get_article_list
    result = get_article_list(
        fakeid=args.fakeid,
        mp_name=args.name,
        max_pages=args.pages,
        interval=args.interval,
    )
    output(result)


def cmd_fetch(args):
    # fetch uses Playwright to directly open the article URL, no token needed
    from article_content import get_article_content
    result = get_article_content(args.url, headless=not args.headed)
    output(result)


def main():
    parser = argparse.ArgumentParser(
        prog="wechat_article",
        description="WeChat Official Account Article Fetcher - standalone CLI tool",
    )
    subparsers = parser.add_subparsers(dest="command")

    # login
    sp_login = subparsers.add_parser("login", help="Login via QR code to get a new token")
    sp_login.add_argument("--timeout", type=int, default=300, help="Seconds to wait for QR scan (default: 300)")
    sp_login.add_argument("--headed", action="store_true", help="Show browser window (default: headless)")

    # check-token
    subparsers.add_parser("check-token", help="Check if WeChat MP token is valid")

    # search
    sp_search = subparsers.add_parser("search", help="Search official accounts by name")
    sp_search.add_argument("keyword", help="Account name to search")
    sp_search.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    sp_search.add_argument("--offset", type=int, default=0, help="Pagination offset (default: 0)")

    # list
    sp_list = subparsers.add_parser("list", help="Get article list for an account")
    sp_list.add_argument("fakeid", help="Account fakeid (from search results)")
    sp_list.add_argument("--name", default="", help="Account display name (for logging)")
    sp_list.add_argument("--pages", type=int, default=1, help="Number of pages to fetch (default: 1, each page = 5 articles)")
    sp_list.add_argument("--interval", type=int, default=5, help="Max seconds between page requests (default: 5)")

    # fetch
    sp_fetch = subparsers.add_parser("fetch", help="Fetch full article content")
    sp_fetch.add_argument("url", help="WeChat article URL (https://mp.weixin.qq.com/s/...)")
    sp_fetch.add_argument("--headed", action="store_true", help="Show browser window (default: headless)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "login": cmd_login,
        "check-token": cmd_check_token,
        "search": cmd_search,
        "list": cmd_list,
        "fetch": cmd_fetch,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        output({"success": False, "error": str(e), "code": "UNEXPECTED_ERROR"})
        sys.exit(1)


if __name__ == "__main__":
    main()
