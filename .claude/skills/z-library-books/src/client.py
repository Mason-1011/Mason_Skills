#!/usr/bin/env python3
"""Small Z-Library eapi client for the z-library-books pi skill.

Search-only by default. The skill intentionally prints metadata, not download links.
"""

from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Optional progress bar for downloads
try:
    from tqdm import tqdm as _tqdm
except Exception:  # noqa: BLE001
    _tqdm = None

DEFAULT_API_BASE = "https://z-library.im"
API_BASE = os.getenv("ZLIBRARY_API_BASE", DEFAULT_API_BASE).rstrip("/")
AUTH_CACHE = Path(os.path.expanduser(os.getenv("ZLIBRARY_AUTH_CACHE", "~/.config/zlibrary-pi/auth.json")))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


class ZLibraryError(Exception):
    """Z-Library API/client error."""


@dataclass
class ZLibAuth:
    remix_userid: str
    remix_userkey: str
    email: str | None = None
    saved_at: float | None = None

    def as_cookies(self) -> dict[str, str]:
        return {"remix_userid": self.remix_userid, "remix_userkey": self.remix_userkey}


@dataclass
class ZLibBook:
    id: str
    title: str
    author: str
    year: int | str | None
    extension: str
    filesize: int
    filesize_str: str
    language: str | None
    cover_url: str | None
    hash: str
    quality: str | None

    @property
    def display_size(self) -> str:
        if self.filesize > 1_000_000:
            return f"{self.filesize / 1_000_000:.1f} MB"
        if self.filesize > 1_000:
            return f"{self.filesize / 1_000:.0f} KB"
        return f"{self.filesize} B"

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["display_size"] = self.display_size
        return data


def _request(
    url: str,
    fields: dict[str, Any] | None = None,
    cookies: dict[str, str] | None = None,
    timeout: float = 30.0,
    method: str = "POST",
) -> tuple[int, str, Any]:
    """Make a request and return (status_code, raw_text, parsed_json)."""
    data = None
    headers = dict(HEADERS)
    if fields is not None:
        data = urlencode(fields).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if cookies:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            status = getattr(resp, "status", 200)
    except HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        status = e.code
    except URLError as e:
        raise ZLibraryError(f"Network error: {e}") from e

    try:
        parsed = json.loads(text)
    except Exception as e:
        raise ZLibraryError(f"API returned non-JSON (HTTP {status}): {text[:200]}") from e
    return status, text, parsed


def _post_json(url: str, fields: dict[str, Any], cookies: dict[str, str] | None = None, timeout: float = 30.0) -> tuple[int, str, Any]:
    return _request(url, fields=fields, cookies=cookies, timeout=timeout, method="POST")


def save_auth(auth: ZLibAuth) -> None:
    AUTH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(auth)
    payload["saved_at"] = payload.get("saved_at") or time.time()
    AUTH_CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    AUTH_CACHE.chmod(stat.S_IRUSR | stat.S_IWUSR)


def load_auth(required: bool = True) -> ZLibAuth | None:
    env_userid = os.getenv("ZLIBRARY_REMIX_USERID")
    env_userkey = os.getenv("ZLIBRARY_REMIX_USERKEY")
    if env_userid and env_userkey:
        return ZLibAuth(remix_userid=env_userid, remix_userkey=env_userkey, email=os.getenv("ZLIBRARY_EMAIL"))

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
        return ZLibAuth(remix_userid=userid, remix_userkey=userkey, email=data.get("email"), saved_at=data.get("saved_at"))
    except Exception as e:
        raise ZLibraryError(f"Could not read auth cache {AUTH_CACHE}: {e}") from e


def login(email: str, password: str) -> ZLibAuth:
    status, text, data = _post_json(
        f"{API_BASE}/eapi/user/login",
        {"email": email, "password": password},
    )

    if data.get("success") != 1:
        raise ZLibraryError(f"Login failed: {data.get('error', 'Unknown error')}")

    user = data.get("user") or {}
    userid = str(user.get("id") or "")
    userkey = str(user.get("remix_userkey") or "")
    if not userid or not userkey:
        raise ZLibraryError(f"Login response missing auth fields. User keys: {list(user.keys())}")

    return ZLibAuth(remix_userid=userid, remix_userkey=userkey, email=email, saved_at=time.time())


def search(query: str, auth: ZLibAuth, limit: int = 10, extensions: list[str] | None = None) -> list[ZLibBook]:
    fields: dict[str, Any] = {"message": query, "limit": limit}
    if extensions:
        for i, ext in enumerate(extensions):
            fields[f"extensions[{i}]"] = ext

    status, text, data = _post_json(
        f"{API_BASE}/eapi/book/search",
        fields,
        cookies=auth.as_cookies(),
    )

    if data.get("success") != 1:
        raise ZLibraryError(f"Search failed: {data.get('error', 'Unknown error')}")

    books = []
    for b in data.get("books", []):
        try:
            books.append(ZLibBook(
                id=str(b.get("id", "")),
                title=b.get("title") or "Unknown Title",
                author=b.get("author") or "Unknown Author",
                year=b.get("year"),
                extension=(b.get("extension") or "").lower(),
                filesize=int(b.get("filesize") or 0),
                filesize_str=b.get("filesizeString") or "",
                language=b.get("language"),
                cover_url=b.get("cover"),
                hash=b.get("hash") or "",
                quality=b.get("quality"),
            ))
        except (TypeError, ValueError):
            continue
    return books


def get_download_url(id: str, hash: str, auth: ZLibAuth, timeout: float = 30.0) -> str:
    """Call Z-Library download endpoint and return the direct download URL."""
    status, text, data = _request(
        f"{API_BASE}/eapi/book/{id}/{hash}/file",
        cookies=auth.as_cookies(),
        timeout=timeout,
        method="GET",
    )

    if data.get("success") != 1:
        raise ZLibraryError(f"Download request failed: {data.get('error', 'Unknown error')}")

    # The eapi returns the download URL in a few possible shapes.
    payload = data.get("file") or data.get("data") or {}
    for key in ("download_url", "downloadLink", "file", "url", "link"):
        val = payload.get(key) if isinstance(payload, dict) else payload if isinstance(payload, str) and key == "downloadLink" else None
        if not val and isinstance(payload, dict):
            val = payload.get(key)
        if val and isinstance(val, str) and val.startswith("http"):
            return val

    raise ZLibraryError(f"Download response missing download URL. Keys: {list(payload.keys()) if isinstance(payload, dict) else type(payload)}")


def download_file(url: str, output_path: Path, cookies: dict[str, str] | None = None, timeout: float = 120.0, chunk_size: int = 8192) -> int:
    """Download a file and return the number of bytes written."""
    headers = dict(HEADERS)
    if cookies:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            total = resp.headers.get("Content-Length")
            total = int(total) if total else None
            output_path.parent.mkdir(parents=True, exist_ok=True)
            wrote = 0
            progress = _tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024, desc=output_path.name) if _tqdm and total else None
            with open(output_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    wrote += len(chunk)
                    if progress:
                        progress.update(len(chunk))
            if progress:
                progress.close()
            return wrote
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        raise ZLibraryError(f"Download HTTP error: {e.code} — {body}") from e
    except URLError as e:
        raise ZLibraryError(f"Download network error: {e}") from e


def logout() -> bool:
    if AUTH_CACHE.exists():
        AUTH_CACHE.unlink()
        return True
    return False
