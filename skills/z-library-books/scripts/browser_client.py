#!/usr/bin/env python3
"""Z-Library client using Playwright to bypass anti-bot protection."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, Browser, Page
from urllib.parse import urlparse

DEFAULT_API_BASE = "https://z-library.im"
API_BASE = os.getenv("ZLIBRARY_API_BASE", DEFAULT_API_BASE).rstrip("/")
AUTH_CACHE = Path(os.path.expanduser(os.getenv("ZLIBRARY_AUTH_CACHE", "~/.config/zlibrary-pi/auth.json")))


def _cookie_domain() -> str:
    """Derive cookie domain from API_BASE (e.g. https://z-lib.id -> .z-lib.id)."""
    from urllib.parse import urlparse
    host = urlparse(API_BASE).hostname or ""
    return f".{host}" if host else ".z-library.im"


# Domains that can provide Cloudflare clearance for z-library.im
CLEARANCE_DOMAINS = ["https://z-lib.id", "https://singlelogin.re"]


def _setup_browser(p, cookies: dict[str, str], accept_downloads: bool = False):
    """Create a browser with proxy, Cloudflare clearance, and auth cookies.

    Visits a clearance domain first to get cf_clearance, then sets auth cookies
    on the target domain. Returns (browser, context, page).
    """
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    launch_args: dict = {"headless": True}
    if proxy:
        launch_args["proxy"] = {"server": proxy}
    browser = p.chromium.launch(**launch_args)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        accept_downloads=accept_downloads,
    )
    page = context.new_page()

    # Step 1: Visit a clearance domain to get cf_clearance
    for clear_domain in CLEARANCE_DOMAINS:
        try:
            page.goto(clear_domain, wait_until="networkidle", timeout=20000)
            time.sleep(2)
            # Check if we got cf_clearance
            all_cookies = context.cookies()
            has_clearance = any(c["name"] == "cf_clearance" for c in all_cookies)
            if has_clearance:
                # Copy cf_clearance to target domain
                target_host = urlparse(API_BASE).hostname or ""
                for c in all_cookies:
                    if c["name"] == "cf_clearance":
                        context.add_cookies([{
                            "name": "cf_clearance",
                            "value": c["value"],
                            "domain": f".{target_host}",
                            "path": "/",
                        }])
                        print(f"Got Cloudflare clearance from {clear_domain}")
                        break
                break
        except Exception:
            continue

    # Step 2: Set auth cookies
    target_host = urlparse(API_BASE).hostname or ""
    cookie_domain = f".{target_host}"
    context.add_cookies([
        {"name": "remix_userid", "value": cookies["remix_userid"], "domain": cookie_domain, "path": "/"},
        {"name": "remix_userkey", "value": cookies["remix_userkey"], "domain": cookie_domain, "path": "/"},
    ])

    return browser, context, page


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

            # Click submit button - try multiple strategies
            print("Submitting login form...")
            submitted = False

            # Strategy 1: Click the found login_button directly
            if login_button and not submitted:
                try:
                    login_button.click()
                    submitted = True
                    print("Submitted via button click")
                except Exception as e:
                    print(f"Button click failed: {e}")

            # Strategy 2: Try modal submit button
            if not submitted:
                try:
                    modal_btn = page.query_selector('#zlibrary-modal-auth button[type=submit]')
                    if modal_btn:
                        modal_btn.click()
                        submitted = True
                        print("Submitted via modal button")
                except Exception:
                    pass

            # Strategy 3: Press Enter on the password field
            if not submitted:
                try:
                    password_field.press("Enter")
                    submitted = True
                    print("Submitted via Enter key")
                except Exception:
                    pass

            # Strategy 4: JS form submit
            if not submitted:
                try:
                    page.evaluate("document.querySelector('form')?.submit()")
                    submitted = True
                    print("Submitted via form.submit()")
                except Exception:
                    pass

            if not submitted:
                raise ZLibraryError("Could not submit login form")

            # Wait for navigation - use shorter timeout and domcontentloaded
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                pass
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
        browser, context, page = _setup_browser(p, cookies)

        try:
            # Navigate to search page (use ?q= format for compatibility across domains)
            from urllib.parse import quote
            search_url = f"{API_BASE}/s/?q={quote(query)}"
            print(f"Navigating to {search_url}...")
            page.goto(search_url, wait_until="networkidle", timeout=30000)

            # Wait for results to load
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # Extract book data from page
            books = []
            import re

            # Strategy 1: Find all links to /book/ pages (works across all Z-Library domains)
            book_links = page.query_selector_all('a[href*="/book/"]')
            seen_ids = set()

            if book_links:
                print(f"Found {len(book_links)} book links")
                for link in book_links:
                    try:
                        href = link.get_attribute("href") or ""
                        # Extract book ID and hash from URL like /book/ID/HASH.html
                        match = re.search(r'/book/([^/]+)/([^/.]+)', href)
                        if not match:
                            continue
                        book_id = match.group(1)
                        book_hash = match.group(2)

                        if book_id in seen_ids:
                            continue
                        seen_ids.add(book_id)

                        # Get parent container for metadata
                        container = link.evaluate_handle("el => el.closest('.bookRow, .book-item, [class*=\"book\"], [class*=\"Book\"], .row, .item, li, tr') || el.parentElement")
                        container_elem = container.as_element()

                        title = "Unknown"
                        author = "Unknown"
                        year = None
                        ext = "epub"

                        if container_elem:
                            # Try to extract title
                            title_elem = container_elem.query_selector('.book-title, h3, h4, [class*="title"], a[href*="/book/"]')
                            if title_elem:
                                t = title_elem.text_content().strip()
                                if t and t != "Unknown":
                                    title = t

                            # Try to extract author
                            author_elem = container_elem.query_selector('.book-author, [class*="author"], .author')
                            if author_elem:
                                a = author_elem.text_content().strip()
                                if a and a != "Unknown":
                                    author = a

                            # Try to extract year
                            year_elem = container_elem.query_selector('.book-year, [class*="year"], .year')
                            if year_elem:
                                y = year_elem.text_content().strip()
                                if y and y.isdigit():
                                    year = int(y)

                            # Try to extract extension
                            ext_elem = container_elem.query_selector('.book-ext, [class*="extension"], .extension, [class*="ext"]')
                            if ext_elem:
                                e = ext_elem.text_content().strip().lower()
                                if e:
                                    ext = e

                        # If title is still unknown, try link text
                        if title == "Unknown":
                            link_text = link.text_content().strip()
                            if link_text:
                                title = link_text

                        books.append({
                            "id": book_id,
                            "title": title,
                            "author": author,
                            "year": year,
                            "extension": ext,
                            "filesize": 0,
                            "hash": book_hash,
                        })

                        if len(books) >= limit:
                            break
                    except Exception as e:
                        print(f"Error extracting book: {e}")
                        continue

            # Strategy 2: If no book links found, try CSS selectors
            if not books:
                book_elements = page.query_selector_all('.book-item, .bookRow, [class*="book"], [class*="Book"]')
                if book_elements:
                    print(f"Found {len(book_elements)} book elements (CSS fallback)")
                    for elem in book_elements[:limit]:
                        try:
                            title_elem = elem.query_selector('.book-title, h3, h4, [class*="title"]')
                            author_elem = elem.query_selector('.book-author, [class*="author"]')
                            year_elem = elem.query_selector('.book-year, [class*="year"]')
                            ext_elem = elem.query_selector('.book-ext, [class*="extension"]')

                            title = title_elem.text_content().strip() if title_elem else "Unknown"
                            author = author_elem.text_content().strip() if author_elem else "Unknown"
                            year = year_elem.text_content().strip() if year_elem else None
                            ext = ext_elem.text_content().strip().lower() if ext_elem else "epub"

                            link = elem.query_selector('a[href*="/book/"]')
                            book_id = ""
                            book_hash = ""
                            if link:
                                href = link.get_attribute("href")
                                m = re.search(r'/book/([^/]+)/([^/.]+)', href)
                                if m:
                                    book_id = m.group(1)
                                    book_hash = m.group(2)

                            books.append({
                                "id": book_id,
                                "title": title,
                                "author": author,
                                "year": int(year) if year and year.isdigit() else None,
                                "extension": ext,
                                "filesize": 0,
                                "hash": book_hash,
                            })
                        except Exception as e:
                            print(f"Error extracting book: {e}")
                            continue

            # Strategy 3: Try JSON in page source
            if not books:
                print("Trying JSON extraction from page source...")
                page.screenshot(path="/tmp/zlibrary_search_debug.png")
                content = page.content()
                if '"books"' in content or '"id"' in content:
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

            if not books:
                print("No books found. Taking screenshot...")
                page.screenshot(path="/tmp/zlibrary_search_debug.png")

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
            {"name": "remix_userid", "value": cookies["remix_userid"], "domain": _cookie_domain(), "path": "/"},
            {"name": "remix_userkey", "value": cookies["remix_userkey"], "domain": _cookie_domain(), "path": "/"},
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
        browser, context, page = _setup_browser(p, cookies, accept_downloads=True)

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


# Known Z-Library mirror domains to try
KNOWN_DOMAINS = [
    "https://z-library.im",
    "https://z-library.se",
    "https://z-lib.org",
    "https://zlibrary.to",
    "https://singlelogin.re",
    "https://singlelogin.app",
    "https://z-lib.id",
    "https://zlibrary.ws",
    "https://z-lib.gs",
    "https://zlibrary.at",
]


def find_working_domain(timeout: int = 10) -> list[dict[str, Any]]:
    """Try known Z-Library domains and return which ones are accessible.

    Returns a list of dicts with keys: domain, status_code, accessible, latency_ms, is_real.
    Sorted by accessible+real first, then by latency.
    """
    import urllib.request
    import urllib.error
    import ssl
    import re as _re

    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    results = []

    for domain in KNOWN_DOMAINS:
        result = {"domain": domain, "status_code": None, "accessible": False, "latency_ms": None, "is_real": False}
        try:
            req = urllib.request.Request(domain, method="GET")
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

            import socket
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)

            start = time.time()
            try:
                if proxy:
                    proxy_handler = urllib.request.ProxyHandler({"https": proxy, "http": proxy})
                    opener = urllib.request.build_opener(proxy_handler)
                else:
                    opener = urllib.request.build_opener()

                resp = opener.open(req, timeout=timeout)
                result["status_code"] = resp.status
                result["accessible"] = True
                result["latency_ms"] = round((time.time() - start) * 1000)

                # Check if it's a real Z-Library by looking for known markers in the response
                body = resp.read(5000).decode("utf-8", errors="ignore")
                real_markers = ["z-library", "zlibrary", "Z-Library", "remix_userid", "/s/", "/book/"]
                fake_markers = ["Scribd Downloader", "allepub.com", "Click Here To Proceed"]
                result["is_real"] = any(m in body for m in real_markers) and not any(m in body for m in fake_markers)

            finally:
                socket.setdefaulttimeout(old_timeout)

        except urllib.error.HTTPError as e:
            result["status_code"] = e.code
            # 403/503 may still mean the domain is alive (just blocking bots)
            result["accessible"] = e.code < 500
            result["latency_ms"] = round((time.time() - start) * 1000)
            # If 503, it's likely real Z-Library rate-limiting
            result["is_real"] = e.code == 503
        except Exception:
            result["accessible"] = False

        results.append(result)

    # Sort: accessible+real first, then by latency
    results.sort(key=lambda r: (not (r["accessible"] and r["is_real"]), not r["accessible"], r["latency_ms"] or 99999))
    return results


def check_site_access(domain: str | None = None, timeout: int = 10) -> dict[str, Any]:
    """Check if a specific Z-Library domain is accessible.

    Returns dict with: domain, accessible, status_code, latency_ms, proxy_used, error.
    """
    import urllib.request
    import urllib.error
    import ssl
    import socket

    target = domain or API_BASE
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")

    result = {
        "domain": target,
        "accessible": False,
        "status_code": None,
        "latency_ms": None,
        "proxy_used": proxy or "(none)",
        "error": None,
    }

    try:
        req = urllib.request.Request(target, method="GET")
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)

        start = time.time()
        try:
            if proxy:
                proxy_handler = urllib.request.ProxyHandler({"https": proxy, "http": proxy})
                opener = urllib.request.build_opener(proxy_handler)
            else:
                opener = urllib.request.build_opener()

            resp = opener.open(req, timeout=timeout)
            result["status_code"] = resp.status
            result["accessible"] = True
            result["latency_ms"] = round((time.time() - start) * 1000)
        finally:
            socket.setdefaulttimeout(old_timeout)

    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        result["accessible"] = e.code < 500
        result["latency_ms"] = round((time.time() - start) * 1000)
    except Exception as e:
        result["error"] = str(e)

    return result


def check_env_credentials() -> dict[str, Any]:
    """Check if Z-Library credentials are available in environment variables.

    Returns dict with: email_set, password_set, email_preview, auth_cache_exists.
    """
    email = os.getenv("ZLIBRARY_EMAIL")
    password = os.getenv("ZLIBRARY_PASSWORD")

    return {
        "email_set": bool(email),
        "password_set": bool(password),
        "email_preview": (email[:3] + "***" + email.split("@")[0][-2:] + "@" + email.split("@")[1]) if email and "@" in email else "(not set)",
        "auth_cache_exists": AUTH_CACHE.exists(),
    }
