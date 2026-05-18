"""WeChat MP platform QR code login - standalone implementation.

Source: WeChat_OA_Bot/driver/wx.py Wx.wxLogin() + Call_Success()
Flow:
1. Launch browser to mp.weixin.qq.com
2. Screenshot QR code -> save to data/wx_qrcode.png
3. Wait for user to scan (detect navigation to home page)
4. Extract cookies + token from browser
5. Calculate expiry from cookies
6. Save to data/wx.lic
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright_driver import PlaywrightController


WX_LOGIN_URL = "https://mp.weixin.qq.com/"
WX_HOME_URL = "https://mp.weixin.qq.com/cgi-bin/home"

# QR code image saved here for user to scan
DATA_DIR = Path(__file__).parent.parent / "data"
QR_IMAGE_PATH = DATA_DIR / "wx_qrcode.png"


def _extract_token_from_page(page) -> str:
    """Extract token from the current page URL, localStorage, sessionStorage, or cookies."""
    try:
        # From URL
        current_url = page.url
        token_match = re.search(r"token=([^&]+)", current_url)
        if token_match:
            return token_match.group(1)

        # From localStorage
        token = page.evaluate("() => localStorage.getItem('token')")
        if token:
            return token

        # From sessionStorage
        token = page.evaluate("() => sessionStorage.getItem('token')")
        if token:
            return token

        # From cookies
        cookies = page.context.cookies()
        for cookie in cookies:
            if "token" in cookie["name"].lower():
                return cookie["value"]

        return ""
    except Exception:
        return ""


def _calc_cookie_expiry(cookies: list) -> dict:
    """Calculate cookie expiry time from browser cookies.

    Source: WeChat_OA_Bot/driver/cookies.py expire()
    """
    priority_names = ["slave_sid", "slave_user", "bizuin", "uin", "pass_ticket"]

    def _extract_expiry(cookie: dict):
        for field in ["expires", "expiry", "expire"]:
            if field not in cookie:
                continue
            val = cookie[field]
            expiry_time = None
            try:
                if isinstance(val, (int, float)):
                    expiry_time = float(val)
                elif isinstance(val, str):
                    if val.isdigit():
                        expiry_time = float(val)
                    else:
                        for fmt in ["%Y-%m-%d %H:%M:%S", "%a, %d-%b-%Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %Z"]:
                            try:
                                expiry_time = datetime.strptime(val, fmt).timestamp()
                                break
                            except ValueError:
                                continue
            except (ValueError, TypeError):
                continue

            if expiry_time and expiry_time > time.time():
                return {
                    "expiry_timestamp": expiry_time,
                    "remaining_seconds": int(expiry_time - time.time()),
                    "expiry_time": datetime.fromtimestamp(expiry_time).strftime("%Y-%m-%d %H:%M:%S"),
                }
        return None

    # Try priority cookies first
    for name in priority_names:
        for cookie in cookies:
            if cookie.get("name") == name:
                result = _extract_expiry(cookie)
                if result:
                    return result

    # Try all cookies
    for cookie in cookies:
        result = _extract_expiry(cookie)
        if result:
            return result

    # Default: 2 hours
    default_expiry = time.time() + 7200
    return {
        "expiry_timestamp": default_expiry,
        "remaining_seconds": 7200,
        "expiry_time": datetime.fromtimestamp(default_expiry).strftime("%Y-%m-%d %H:%M:%S"),
    }


def _format_session(cookies: list, token: str = "") -> dict:
    """Format cookies and token into session data.

    Source: WeChat_OA_Bot/driver/wx.py Wx.format_token()
    """
    cookies_str = ""
    for cookie in cookies:
        cookies_str += f"{cookie['name']}={cookie['value']}; "
        if "token" in cookie["name"].lower() and not token:
            token = cookie["value"]

    cookie_expiry = _calc_cookie_expiry(cookies)

    return {
        "cookies": cookies,
        "cookies_str": cookies_str,
        "token": token,
        "expiry": cookie_expiry,
    }


def _save_token(session_data: dict) -> bool:
    """Save token data to data/wx.lic.

    Source: WeChat_OA_Bot/driver/token.py set_token() + _save_to_local()
    """
    import yaml

    token_data = {
        "token": session_data.get("token", ""),
        "cookie": session_data.get("cookies_str", ""),
        "fingerprint": "",
        "expiry": session_data.get("expiry", {}),
    }

    if not token_data["token"]:
        return False

    lic_path = DATA_DIR / "wx.lic"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = {"token_data": token_data}
    with open(lic_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    return True


def login(timeout_seconds: int = 300, headless: bool = True) -> dict:
    """Perform WeChat MP platform QR code login.

    1. Opens browser to mp.weixin.qq.com
    2. Saves QR code image to data/wx_qrcode.png
    3. Waits for user to scan
    4. Extracts and saves token

    Args:
        timeout_seconds: Max time to wait for QR code scan (default: 5 minutes)

    Returns:
        dict with: success, message, token_path, expiry, qr_image_path
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Clean up old QR code
    if QR_IMAGE_PATH.exists():
        QR_IMAGE_PATH.unlink()

    controller = PlaywrightController()

    try:
        # Start browser
        controller.start_browser(headless=headless)
        controller.open_url(WX_LOGIN_URL)
        page = controller.page

        print("Loading WeChat MP login page...", file=sys.stderr)
        page.wait_for_load_state("networkidle")

        # Locate and screenshot QR code
        qr_selector = ".login__type__container__scan__qrcode"
        qr_element = page.query_selector(qr_selector)
        if not qr_element:
            return {"success": False, "error": "Could not find QR code element on page", "code": "QR_NOT_FOUND"}

        qr_element.screenshot(path=str(QR_IMAGE_PATH))
        print(f"QR code saved to: {QR_IMAGE_PATH}", file=sys.stderr)
        print(f"Please scan the QR code with WeChat within {timeout_seconds} seconds.", file=sys.stderr)

        # Open the image for the user (Windows)
        if sys.platform == "win32":
            try:
                os.startfile(str(QR_IMAGE_PATH))
            except Exception:
                pass

        # Poll for login success - wait for URL to change to home page
        start_time = time.time()
        logged_in = False
        print("Waiting for QR code scan...", file=sys.stderr)

        while time.time() - start_time < timeout_seconds:
            try:
                current_url = page.url
                # Login page is https://mp.weixin.qq.com/ - any redirect means login happened
                if "mp.weixin.qq.com" in current_url and current_url != "https://mp.weixin.qq.com/":
                    logged_in = True
                    print(f"Login detected! Redirected to: {current_url}", file=sys.stderr)
                    break
                # Check for QR code element disappearing (means scan accepted)
                try:
                    qr_el = page.query_selector(".login__type__container__scan__qrcode")
                    if qr_el is None:
                        # QR code gone, check if we're on a new page
                        time.sleep(2)
                        new_url = page.url
                        if new_url != "https://mp.weixin.qq.com/":
                            logged_in = True
                            print(f"Login detected (QR gone)! URL: {new_url}", file=sys.stderr)
                            break
                except Exception:
                    pass
            except Exception:
                pass
            time.sleep(2)

        if not logged_in:
            return {"success": False, "error": f"Login timed out after {timeout_seconds}s. Please try again.", "code": "TIMEOUT"}

        print("Login detected! Extracting token...", file=sys.stderr)
        time.sleep(2)  # Wait for page to fully load

        # Extract token and cookies
        token = _extract_token_from_page(page)
        cookies = controller.context.cookies()

        if not cookies:
            return {"success": False, "error": "Failed to get cookies after login", "code": "NO_COOKIES"}

        session_data = _format_session(cookies, token)

        if not session_data.get("token"):
            return {"success": False, "error": "Failed to extract token from login session", "code": "NO_TOKEN"}

        # Save to wx.lic
        saved = _save_token(session_data)
        if not saved:
            return {"success": False, "error": "Failed to save token to wx.lic", "code": "SAVE_FAILED"}

        expiry = session_data.get("expiry", {})
        return {
            "success": True,
            "message": "Login successful! Token saved.",
            "token": session_data["token"],
            "expiry": expiry.get("expiry_time", ""),
            "remaining_seconds": expiry.get("remaining_seconds", 0),
            "token_path": str(DATA_DIR / "wx.lic"),
            "qr_image_path": str(QR_IMAGE_PATH),
        }

    except Exception as e:
        return {"success": False, "error": str(e), "code": "LOGIN_ERROR"}

    finally:
        controller.Close()
        # Clean up QR code image
        try:
            if QR_IMAGE_PATH.exists():
                QR_IMAGE_PATH.unlink()
        except Exception:
            pass
