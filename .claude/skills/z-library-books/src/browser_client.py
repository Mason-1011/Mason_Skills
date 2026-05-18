#!/usr/bin/env python3
"""Z-Library client using Playwright to bypass anti-bot protection."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, Browser, Page

DEFAULT_API_BASE = "https://z-library.im"
API_BASE = os.getenv("ZLIBRARY_API_BASE", DEFAULT_API_BASE).rstrip("/")
AUTH_CACHE = Path(os.path.expanduser(os.getenv("ZLIBRARY_AUTH_CACHE", "~/.config/zlibrary-pi/auth.json")))


class ZLibraryError(Exception):
    """Z-Library API/client error."""


def login_with_browser(email: str, password: str) -> dict[str, str]:
    """Login to Z-Library using browser automation and return cookies."""
    with sync_playwright() as p:
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        launch_args: dict = {"headless": True}
        if proxy:
            launch_args["proxy"] = {"server": proxy}
        browser = p.chromium.launch(**launch_args)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # Navigate to main page
            print(f"Navigating to {API_BASE}/...")
            page.goto(f"{API_BASE}/", wait_until="networkidle", timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)

            # Click "LOG IN" button in header to open login modal
            print("Clicking LOG IN button...")
            login_btn_selectors = [
                'a[href="/login"]',
                'a:has-text("LOG IN")',
                'a:has-text("Log in")',
                'button:has-text("LOG IN")',
                '.header-login',
                '.login-link',
            ]

            clicked = False
            for selector in login_btn_selectors:
                try:
                    btn = page.wait_for_selector(selector, timeout=3000)
                    if btn:
                        btn.click()
                        print(f"Clicked login button: {selector}")
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                # Try navigating directly to login page
                print("Trying direct navigation to /login...")
                page.goto(f"{API_BASE}/login", wait_until="networkidle", timeout=30000)
                time.sleep(2)

            # Wait for login form to appear
            time.sleep(3)
            page.screenshot(path="/tmp/zlibrary_after_login_click.png")

            # Try to find and fill login form
            print("Looking for login form...")

            email_selectors = [
                'input[name="email"]',
                'input[type="email"]',
                'input[placeholder*="email" i]',
                'input[placeholder*="Email"]',
                '#email',
            ]

            email_field = None
            for selector in email_selectors:
                try:
                    email_field = page.wait_for_selector(selector, timeout=5000)
                    if email_field and email_field.is_visible():
                        print(f"Found email field with selector: {selector}")
                        break
                    email_field = None
                except:
                    email_field = None
                    continue

            if not email_field:
                print("Could not find email field. Taking screenshot...")
                page.screenshot(path="/tmp/zlibrary_debug.png")
                raise ZLibraryError("Could not find email login field")

            # Fill email
            email_field.fill(email)
            print(f"Filled email: {email}")

            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="password" i]',
                '#password',
            ]

            password_field = None
            for selector in password_selectors:
                try:
                    password_field = page.wait_for_selector(selector, timeout=3000)
                    if password_field and password_field.is_visible():
                        print(f"Found password field with selector: {selector}")
                        break
                    password_field = None
                except:
                    password_field = None
                    continue

            if not password_field:
                print("Could not find password field. Taking screenshot...")
                page.screenshot(path="/tmp/zlibrary_debug.png")
                raise ZLibraryError("Could not find password login field")

            password_field.fill(password)
            print("Filled password")

            # Find and click submit button
            button_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("LOG IN")',
                'button:has-text("Log in")',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                '.login-button',
                '#login-button',
            ]

            login_button = None
            for selector in button_selectors:
                try:
                    login_button = page.wait_for_selector(selector, timeout=3000)
                    if login_button and login_button.is_visible():
                        print(f"Found login button with selector: {selector}")
                        break
                    login_button = None
                except:
                    login_button = None
                    continue

            if not login_button:
                print("Could not find login button. Taking screenshot...")
                page.screenshot(path="/tmp/zlibrary_debug.png")
                raise ZLibraryError("Could not find login button")

            # Intercept login API response to capture auth cookies
            login_response_data = {}

            def handle_response(response):
                nonlocal login_response_data
                url = response.url
                if "login" in url or "user" in url:
                    try:
                        body = response.json()
                        print(f"  Login API response from {url}: success={body.get('success', 'N/A')}")
                        if body.get("success") == 1:
                            login_response_data = body
                    except Exception:
                        pass

            page.on("response", handle_response)

            # Click via JavaScript to bypass modal overlay
            print("Clicking submit via JavaScript...")
            page.evaluate("document.querySelector('#zlibrary-modal-auth button[type=submit]').click()")
            print("Submitted login form")

            # Wait for navigation / page update
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(5)

            page.screenshot(path="/tmp/zlibrary_after_login.png")
            print(f"Current URL: {page.url}")

            # Get cookies
            cookies = context.cookies()
            print(f"Got {len(cookies)} cookies")

            remix_userid = None
            remix_userkey = None

            for cookie in cookies:
                if cookie["name"] == "remix_userid":
                    remix_userid = cookie["value"]
                elif cookie["name"] == "remix_userkey":
                    remix_userkey = cookie["value"]

            # Also try extracting from API response
            if not remix_userid and login_response_data:
                user = login_response_data.get("user") or login_response_data.get("data") or {}
                remix_userid = str(user.get("id") or user.get("remix_userid") or "")
                remix_userkey = str(user.get("remix_userkey") or "")
                if remix_userid and remix_userkey:
                    print("Extracted auth from API response")

            if not remix_userid or not remix_userkey:
                print("Could not find auth cookies. Taking screenshot...")
                page.screenshot(path="/tmp/zlibrary_debug.png")
                # Print all cookies for debugging
                for c in cookies:
                    print(f"  cookie: {c['name']} = {c['value'][:20]}...")
                raise ZLibraryError("Login failed - could not get auth cookies")

            print(f"Login successful! remix_userid: {remix_userid[:6]}...")
            return {
                "remix_userid": remix_userid,
                "remix_userkey": remix_userkey,
                "email": email,
            }

        except Exception as e:
            print(f"Error during login: {e}")
            page.screenshot(path="/tmp/zlibrary_error.png")
            raise
        finally:
            browser.close()


def search_with_browser(query: str, cookies: dict[str, str], limit: int = 10, extensions: list[str] | None = None) -> list[dict[str, Any]]:
    """Search Z-Library using browser automation."""
    with sync_playwright() as p:
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        launch_args: dict = {"headless": True}
        if proxy:
            launch_args["proxy"] = {"server": proxy}
        browser = p.chromium.launch(**launch_args)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )

        # Set cookies
        context.add_cookies([
            {"name": "remix_userid", "value": cookies["remix_userid"], "domain": ".z-library.im", "path": "/"},
            {"name": "remix_userkey", "value": cookies["remix_userkey"], "domain": ".z-library.im", "path": "/"},
        ])

        page = context.new_page()

        try:
            # Navigate to search page
            search_url = f"{API_BASE}/s/{query}"
            print(f"Navigating to {search_url}...")
            page.goto(search_url, wait_until="networkidle", timeout=30000)

            # Wait for results to load
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # Extract book data from page
            books = []

            # Try to find book elements
            book_elements = page.query_selector_all('.book-item, .bookRow, [class*="book"], [class*="Book"]')

            if not book_elements:
                print("Could not find book elements. Taking screenshot...")
                page.screenshot(path="/tmp/zlibrary_search_debug.png")
                # Try alternative approach - look for JSON in page source
                content = page.content()
                if '"books"' in content:
                    # Try to extract JSON from page
                    import re
                    json_match = re.search(r'\{.*"books".*\}', content, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group())
                            for b in data.get("books", [])[:limit]:
                                books.append({
                                    "id": str(b.get("id", "")),
                                    "title": b.get("title", "Unknown"),
                                    "author": b.get("author", "Unknown"),
                                    "year": b.get("year"),
                                    "extension": (b.get("extension") or "").lower(),
                                    "filesize": int(b.get("filesize") or 0),
                                    "hash": b.get("hash", ""),
                                })
                        except json.JSONDecodeError:
                            pass

            else:
                print(f"Found {len(book_elements)} book elements")
                for elem in book_elements[:limit]:
                    try:
                        # Try to extract book info from element
                        title_elem = elem.query_selector('.book-title, h3, h4, [class*="title"]')
                        author_elem = elem.query_selector('.book-author, [class*="author"]')
                        year_elem = elem.query_selector('.book-year, [class*="year"]')
                        ext_elem = elem.query_selector('.book-ext, [class*="extension"]')

                        title = title_elem.text_content().strip() if title_elem else "Unknown"
                        author = author_elem.text_content().strip() if author_elem else "Unknown"
                        year = year_elem.text_content().strip() if year_elem else None
                        ext = ext_elem.text_content().strip().lower() if ext_elem else "epub"

                        # Try to get book ID from link
                        link = elem.query_selector('a[href*="/book/"]')
                        book_id = ""
                        book_hash = ""
                        if link:
                            href = link.get_attribute("href")
                            parts = href.split("/")
                            if len(parts) >= 2:
                                book_id = parts[-2] if len(parts) > 1 else ""
                                book_hash = parts[-1] if parts else ""

                        books.append({
                            "id": book_id,
                            "title": title,
                            "author": author,
                            "year": year,
                            "extension": ext,
                            "filesize": 0,
                            "hash": book_hash,
                        })
                    except Exception as e:
                        print(f"Error extracting book: {e}")
                        continue

            # Filter by extension if specified
            if extensions:
                exts = [e.lower() for e in extensions]
                books = [b for b in books if b["extension"] in exts]

            return books[:limit]

        except Exception as e:
            print(f"Error during search: {e}")
            page.screenshot(path="/tmp/zlibrary_search_error.png")
            raise
        finally:
            browser.close()


def get_download_url_with_browser(book_id: str, book_hash: str, cookies: dict[str, str]) -> str:
    """Get download URL for a book by navigating to its page and finding the /dl/ link."""
    with sync_playwright() as p:
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        launch_args: dict = {"headless": True}
        if proxy:
            launch_args["proxy"] = {"server": proxy}
        browser = p.chromium.launch(**launch_args)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )

        context.add_cookies([
            {"name": "remix_userid", "value": cookies["remix_userid"], "domain": ".z-library.im", "path": "/"},
            {"name": "remix_userkey", "value": cookies["remix_userkey"], "domain": ".z-library.im", "path": "/"},
        ])

        page = context.new_page()

        try:
            book_url = f"{API_BASE}/book/{book_id}/{book_hash}"
            print(f"Navigating to {book_url}...")
            page.goto(book_url, wait_until="networkidle", timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # Find the /dl/ download link
            import re
            content = page.content()
            dl_links = re.findall(r'href="(/dl/[^"]+)"', content)

            if not dl_links:
                page.screenshot(path="/tmp/zlibrary_no_download.png")
                raise ZLibraryError("No download link found on book page")

            download_path = dl_links[0]
            print(f"Found download link: {download_path}")
            return f"{API_BASE}{download_path}"

        except Exception as e:
            print(f"Error getting download URL: {e}")
            page.screenshot(path="/tmp/zlibrary_download_error.png")
            raise
        finally:
            browser.close()


def download_book(book_id: str, book_hash: str, cookies: dict[str, str], output_dir: str = ".") -> str:
    """Download a book by clicking the download button on its page. Returns the saved file path."""
    with sync_playwright() as p:
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        launch_args: dict = {"headless": True}
        if proxy:
            launch_args["proxy"] = {"server": proxy}
        browser = p.chromium.launch(**launch_args)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            accept_downloads=True,
        )

        context.add_cookies([
            {"name": "remix_userid", "value": cookies["remix_userid"], "domain": ".z-library.im", "path": "/"},
            {"name": "remix_userkey", "value": cookies["remix_userkey"], "domain": ".z-library.im", "path": "/"},
        ])

        page = context.new_page()

        try:
            book_url = f"{API_BASE}/book/{book_id}/{book_hash}"
            print(f"Navigating to {book_url}...")
            page.goto(book_url, wait_until="networkidle", timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # Find the /dl/ download link
            dl_btn = page.query_selector('a[href*="/dl/"]')
            if not dl_btn:
                page.screenshot(path="/tmp/zlibrary_no_download.png")
                raise ZLibraryError("No download link found on book page")

            print("Clicking download button...")

            # Click and wait for download
            with page.expect_download(timeout=120000) as download_info:
                dl_btn.click(force=True)

            download = download_info.value
            filename = download.suggested_filename or f"{book_id}.pdf"
            print(f"Download started: {filename}")

            os.makedirs(output_dir, exist_ok=True)
            save_path = os.path.join(output_dir, filename)
            download.save_as(save_path)

            file_size = os.path.getsize(save_path)
            print(f"Saved: {save_path}")
            print(f"Size: {file_size:,} bytes ({file_size / 1_048_576:.2f} MB)")
            return save_path

        except Exception as e:
            print(f"Error downloading book: {e}")
            page.screenshot(path="/tmp/zlibrary_download_error.png")
            raise
        finally:
            browser.close()


def save_auth_browser(cookies: dict[str, str]) -> None:
    """Save auth cookies to cache file."""
    AUTH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "remix_userid": cookies["remix_userid"],
        "remix_userkey": cookies["remix_userkey"],
        "email": cookies.get("email"),
        "saved_at": time.time(),
    }
    AUTH_CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    import stat
    AUTH_CACHE.chmod(stat.S_IRUSR | stat.S_IWUSR)


def load_auth_browser(required: bool = True) -> dict[str, str] | None:
    """Load auth cookies from cache file."""
    env_userid = os.getenv("ZLIBRARY_REMIX_USERID")
    env_userkey = os.getenv("ZLIBRARY_REMIX_USERKEY")
    if env_userid and env_userkey:
        return {"remix_userid": env_userid, "remix_userkey": env_userkey, "email": os.getenv("ZLIBRARY_EMAIL")}

    if not AUTH_CACHE.exists():
        if required:
            raise ZLibraryError(f"Not authenticated. No auth cache found at {AUTH_CACHE}")
        return None

    try:
        data = json.loads(AUTH_CACHE.read_text(encoding="utf-8"))
        userid = str(data.get("remix_userid") or "")
        userkey = str(data.get("remix_userkey") or "")
        if not userid or not userkey:
            raise ValueError("missing remix_userid/remix_userkey")
        return {"remix_userid": userid, "remix_userkey": userkey, "email": data.get("email")}
    except Exception as e:
        raise ZLibraryError(f"Could not read auth cache {AUTH_CACHE}: {e}") from e


def logout_browser() -> bool:
    """Delete auth cache file."""
    if AUTH_CACHE.exists():
        AUTH_CACHE.unlink()
        return True
    return False
