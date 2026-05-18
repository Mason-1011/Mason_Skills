#!/usr/bin/env python3
"""Authenticate to Z-Library for the z-library-books skill."""

from __future__ import annotations

import argparse
import getpass
import os
import time

from client import API_BASE, AUTH_CACHE, ZLibraryError, load_auth, login, logout, save_auth, search


def _preview(value: str) -> str:
    return value[:6] + "..." if value else "<none>"


def cmd_login(args: argparse.Namespace) -> int:
    email = args.email or os.getenv("ZLIBRARY_EMAIL") or input("Z-Library email: ").strip()
    password = args.password or os.getenv("ZLIBRARY_PASSWORD") or getpass.getpass("Z-Library password: ")

    print("Z-Library login")
    print(f"API base: {API_BASE}")
    print(f"Email:    {email}")
    print()

    auth = login(email, password)
    save_auth(auth)
    print(f"Saved auth cookies to: {AUTH_CACHE}")
    print("remix_userid preview:", _preview(auth.remix_userid))
    print("remix_userkey preview:", _preview(auth.remix_userkey))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    auth = load_auth(required=False)
    if auth is None:
        print(f"Not authenticated. No auth cache found at {AUTH_CACHE}")
        print("Run: python3 src/auth.py login")
        return 1

    # Verify auth with a tiny EPUB search. This avoids printing sensitive cookie values.
    search("test", auth=auth, limit=1, extensions=["epub"])
    print("Authenticated to Z-Library.")
    source = "ZLIBRARY_REMIX_USERID/ZLIBRARY_REMIX_USERKEY env vars" if os.getenv("ZLIBRARY_REMIX_USERID") else str(AUTH_CACHE)
    print(f"Auth source: {source}")
    if auth.email:
        print(f"Email: {auth.email}")
    if auth.saved_at:
        print(f"Saved: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(auth.saved_at))}")
    print("remix_userid preview:", _preview(auth.remix_userid))
    print("remix_userkey preview:", _preview(auth.remix_userkey))
    return 0


def cmd_logout(args: argparse.Namespace) -> int:
    if logout():
        print(f"Deleted auth cache: {AUTH_CACHE}")
    else:
        print(f"No auth cache at: {AUTH_CACHE}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Authenticate to Z-Library")
    sub = parser.add_subparsers(dest="command", required=True)

    login_parser = sub.add_parser("login", help="Login and cache Z-Library remix cookies")
    login_parser.add_argument("--email", help="Z-Library account email; defaults to ZLIBRARY_EMAIL or prompt")
    login_parser.add_argument("--password", help="Z-Library password; defaults to ZLIBRARY_PASSWORD or secure prompt")
    login_parser.set_defaults(func=cmd_login)

    status_parser = sub.add_parser("status", help="Verify cached auth")
    status_parser.set_defaults(func=cmd_status)

    logout_parser = sub.add_parser("logout", help="Delete cached auth")
    logout_parser.set_defaults(func=cmd_logout)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ZLibraryError as e:
        print(str(e))
        raise SystemExit(1)
