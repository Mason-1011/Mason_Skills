"""Simplified token management for WeChat MP platform.

Reads token/cookie from wx.lic YAML file. No Redis dependency.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime


def _get_token_path() -> str:
    """Return path to wx.lic token file.

    Search order:
    1. WX_LIC_PATH environment variable
    2. ./data/wx.lic relative to scripts directory (skill bundled data)
    3. ./data/wx.lic relative to cwd
    """
    env_path = os.environ.get("WX_LIC_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Skill's own data directory
    scripts_dir = Path(__file__).parent
    skill_data = scripts_dir.parent / "data" / "wx.lic"
    if skill_data.is_file():
        return str(skill_data)

    # CWD data
    cwd_data = Path.cwd() / "data" / "wx.lic"
    if cwd_data.is_file():
        return str(cwd_data)

    return str(skill_data)  # return expected path even if not found


def load_token_data() -> dict | None:
    """Load and return the full token_data dict from wx.lic."""
    path = _get_token_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            return None
        if isinstance(data, dict) and "token_data" in data:
            return data["token_data"]
        return data
    except Exception:
        return None


def get(key: str, default: str = "") -> str:
    """Get a specific field from stored token data."""
    data = load_token_data()
    if data is None:
        return default
    value = data.get(key, default)
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value) if value is not None else default


def check_token_valid() -> dict:
    """Check if token exists and is not expired.

    Returns:
        dict with keys: valid (bool), message (str), expiry (str), token_path (str)
    """
    path = _get_token_path()
    if not os.path.isfile(path):
        return {
            "valid": False,
            "message": f"Token file not found: {path}",
            "expiry": "",
            "token_path": path,
        }

    data = load_token_data()
    if data is None:
        return {
            "valid": False,
            "message": "Failed to parse token file",
            "expiry": "",
            "token_path": path,
        }

    token = data.get("token", "")
    if not token:
        return {
            "valid": False,
            "message": "Token is empty in wx.lic",
            "expiry": "",
            "token_path": path,
        }

    expiry_info = data.get("expiry", {})
    expiry_time = ""
    if isinstance(expiry_info, dict):
        expiry_time = expiry_info.get("expiry_time", "")
        expiry_ts = expiry_info.get("expiry_timestamp")
        if expiry_ts:
            try:
                expiry_dt = datetime.fromtimestamp(float(expiry_ts))
                if expiry_dt < datetime.now():
                    return {
                        "valid": False,
                        "message": f"Token expired at {expiry_time}",
                        "expiry": expiry_time,
                        "token_path": path,
                    }
            except (ValueError, TypeError, OSError):
                pass

    return {
        "valid": True,
        "message": "Token is valid",
        "expiry": expiry_time,
        "token_path": path,
    }
