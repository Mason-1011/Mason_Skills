#!/usr/bin/env python3
"""Search and download Z-Library books using browser automation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from browser_client import (
    ZLibraryError,
    download_book,
    load_auth_browser,
    login_with_browser,
    logout_browser,
    save_auth_browser,
    search_with_browser,
)


def print_table(books: list[dict], show_ids: bool = False) -> None:
    """Print books in a table format."""
    if not books:
        print("No books found.")
        return

    print(f"Results: {len(books)}")
    print()
    for i, book in enumerate(books, 1):
        print(f"{i}. {book['title']} — {book['author']}")
        meta = []
        if book.get('year'):
            meta.append(str(book['year']))
        if book.get('extension'):
            meta.append(book['extension'].upper())
        if book.get('filesize') and book['filesize'] > 0:
            if book['filesize'] > 1_000_000:
                meta.append(f"{book['filesize'] / 1_000_000:.1f} MB")
            elif book['filesize'] > 1_000:
                meta.append(f"{book['filesize'] / 1_000:.0f} KB")
        print("   " + " | ".join(meta))
        if show_ids and book.get('id'):
            print(f"   id={book['id']} hash={book.get('hash', '')}")
        print()


def cmd_login(args: argparse.Namespace) -> int:
    """Login to Z-Library."""
    email = args.email or os.getenv("ZLIBRARY_EMAIL") or input("Z-Library email: ").strip()
    password = args.password or os.getenv("ZLIBRARY_PASSWORD") or input("Z-Library password: ")

    print("Z-Library login (browser mode)")
    print(f"API base: {args.api_base}")
    print(f"Email:    {email}")
    print()

    cookies = login_with_browser(email, password)
    save_auth_browser(cookies)
    print(f"Saved auth cookies to: {args.auth_cache}")
    print("remix_userid preview:", cookies["remix_userid"][:6] + "...")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Check authentication status."""
    try:
        cookies = load_auth_browser(required=False)
        if cookies is None:
            print(f"Not authenticated. No auth cache found at {args.auth_cache}")
            print("Run: python3 src/browser_search.py login")
            return 1

        print("Authenticated to Z-Library.")
        print(f"remix_userid preview: {cookies['remix_userid'][:6]}...")
        return 0
    except ZLibraryError as e:
        print(str(e))
        return 1


def cmd_search(args: argparse.Namespace) -> int:
    """Search for books."""
    cookies = load_auth_browser()
    books = search_with_browser(args.query, cookies, limit=args.limit)

    if args.json:
        print(json.dumps({"data": books, "count": len(books)}, ensure_ascii=False, indent=2))
    else:
        print_table(books, show_ids=args.ids)
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    """Download a book."""
    cookies = load_auth_browser()

    output_dir = args.output or "."
    save_path = download_book(args.id, args.hash, cookies, output_dir=output_dir)
    print(f"Download complete: {save_path}")
    return 0


def cmd_logout(args: argparse.Namespace) -> int:
    """Logout and delete cached auth."""
    if logout_browser():
        print(f"Deleted auth cache: {args.auth_cache}")
    else:
        print(f"No auth cache at: {args.auth_cache}")
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Search and download Z-Library books (browser mode)")
    parser.add_argument("--api-base", default=os.getenv("ZLIBRARY_API_BASE", "https://z-library.im"),
                        help="Z-Library API base URL")
    parser.add_argument("--auth-cache", default=os.getenv("ZLIBRARY_AUTH_CACHE", "~/.config/zlibrary-pi/auth.json"),
                        help="Auth cache file path")

    sub = parser.add_subparsers(dest="command")

    # Login command
    login_parser = sub.add_parser("login", help="Login and cache Z-Library cookies")
    login_parser.add_argument("--email", help="Z-Library account email")
    login_parser.add_argument("--password", help="Z-Library password")
    login_parser.set_defaults(func=cmd_login)

    # Status command
    status_parser = sub.add_parser("status", help="Verify cached auth")
    status_parser.set_defaults(func=cmd_status)

    # Search command
    search_parser = sub.add_parser("search", help="Search for books")
    search_parser.add_argument("query", help="Title, author, or keywords to search")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum results")
    search_parser.add_argument("--ids", action="store_true", help="Show Z-Library ids and hashes")
    search_parser.add_argument("--json", action="store_true", help="Print JSON metadata")
    search_parser.set_defaults(func=cmd_search)

    # Download command
    dl_parser = sub.add_parser("download", help="Download a book by Z-Library id + hash")
    dl_parser.add_argument("id", help="Z-Library book id")
    dl_parser.add_argument("hash", help="Z-Library book hash")
    dl_parser.add_argument("-o", "--output", help="Output file path (auto if omitted)")
    dl_parser.add_argument("-t", "--title", help="Suggested title for default filename")
    dl_parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing file")
    dl_parser.set_defaults(func=cmd_download)

    # Logout command
    logout_parser = sub.add_parser("logout", help="Delete cached auth")
    logout_parser.set_defaults(func=cmd_logout)

    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["search", *argv]

    args = parser.parse_args(argv)

    # Set defaults for auth cache path
    args.auth_cache = Path(os.path.expanduser(args.auth_cache))

    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ZLibraryError as e:
        print(str(e))
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130)
