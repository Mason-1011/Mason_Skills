#!/usr/bin/env python3
"""Search Z-Library EPUB book metadata for the z-library-books skill."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from client import (
    ZLibraryError,
    download_file,
    get_download_url,
    load_auth,
    search,
)


def print_table(books, show_ids: bool = False) -> None:
    if not books:
        print("No books found.")
        return

    print(f"Results: {len(books)}")
    print()
    for i, book in enumerate(books, 1):
        print(f"{i}. {book.title} — {book.author}")
        meta = []
        if book.year:
            meta.append(str(book.year))
        if book.language:
            meta.append(book.language)
        if book.extension:
            meta.append(book.extension.upper())
        meta.append(book.filesize_str or book.display_size)
        if book.quality:
            meta.append(f"quality={book.quality}")
        print("   " + " | ".join(meta))
        if show_ids:
            print(f"   id={book.id} hash={book.hash}")
        print()


def cmd_search(args: argparse.Namespace) -> int:
    auth = load_auth()
    extensions = None if args.all_formats else [args.extension]
    books = search(args.query, auth=auth, limit=args.limit, extensions=extensions)
    if args.json:
        print(json.dumps({"data": [b.public_dict() for b in books], "count": len(books)}, ensure_ascii=False, indent=2))
    else:
        print_table(books, show_ids=args.ids)
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    auth = load_auth()
    url = get_download_url(args.id, args.hash, auth=auth)

    output = args.output
    if not output:
        # Use a sensible default filename based on the provided title if any.
        stem = (args.title or f"zlibrary-{args.id}").replace(" ", "_")
        # Guess extension from hash/URL if possible, otherwise default to epub.
        ext = "epub"
        if "." in url.rsplit("/?", 1)[0]:
            ext = url.rsplit("/?", 1)[0].rsplit(".", 1)[-1]
        output = f"{stem}.{ext}"

    out_path = Path(output).expanduser().resolve()
    if out_path.exists() and not args.force:
        print(f"File already exists: {out_path}")
        print("Use --force to overwrite.")
        return 1

    print(f"Downloading book {args.id} …")
    print(f"URL: {url}")
    bytes_written = download_file(url, out_path)
    print()
    print(f"Saved to: {out_path}")
    print(f"Size: {bytes_written:,} bytes ({bytes_written / 1_048_576:.2f} MB)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Search and download Z-Library books")
    sub = parser.add_subparsers(dest="command")

    search_parser = sub.add_parser("search", help="Search for EPUB books")
    search_parser.add_argument("query", help="Title, author, or keywords to search")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum results")
    search_parser.add_argument("--extension", default="epub", help="Format filter; default epub")
    search_parser.add_argument("--all-formats", action="store_true", help="Disable extension filter")
    search_parser.add_argument("--ids", action="store_true", help="Show Z-Library ids and hashes")
    search_parser.add_argument("--json", action="store_true", help="Print JSON metadata")
    search_parser.set_defaults(func=cmd_search)

    dl_parser = sub.add_parser("download", help="Download a book by Z-Library id + hash")
    dl_parser.add_argument("id", help="Z-Library book id")
    dl_parser.add_argument("hash", help="Z-Library book hash")
    dl_parser.add_argument("-o", "--output", help="Output file path (auto if omitted)")
    dl_parser.add_argument("-t", "--title", help="Suggested title for default filename")
    dl_parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing file")
    dl_parser.set_defaults(func=cmd_download)

    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["search", *argv]

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ZLibraryError as e:
        print(str(e))
        raise SystemExit(1)
