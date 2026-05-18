"""Search WeChat Official Accounts by name/keyword.

Source: WeChat_OA_Bot/core/wx/base.py WxGather.search_Biz()
API: GET https://mp.weixin.qq.com/cgi-bin/searchbiz
"""

import json
import random
import requests
import wx_token as token


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
]


def search_accounts(keyword: str, limit: int = 10, offset: int = 0) -> dict:
    """Search WeChat official accounts by name/keyword.

    Args:
        keyword: Search term (account name or partial name)
        limit: Number of results (max 10)
        offset: Pagination offset

    Returns:
        dict with: success, accounts (list), total, error
    """
    tk = token.get("token", "")
    cookies = token.get("cookie", "")

    if not tk:
        return {"success": False, "error": "Token not found. Please login to WeChat MP platform first.", "code": "NO_TOKEN"}

    url = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
    params = {
        "action": "search_biz",
        "begin": offset,
        "count": limit,
        "query": keyword,
        "token": tk,
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
    }
    headers = {
        "Cookie": cookies,
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=(5, 15))
        resp.raise_for_status()
        msg = resp.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {e}", "code": "REQUEST_ERROR"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON response from WeChat API", "code": "PARSE_ERROR"}

    base_resp = msg.get("base_resp", {})
    ret = base_resp.get("ret", -1)

    if ret == 200013:
        return {"success": False, "error": "Rate limited by WeChat. Please wait and retry.", "code": "RATE_LIMITED"}
    if ret == 200003:
        return {"success": False, "error": "Session expired. Please re-login to WeChat MP platform.", "code": "INVALID_SESSION"}
    if ret != 0:
        return {"success": False, "error": f"WeChat API error: {base_resp.get('err_msg', 'unknown')}", "code": f"API_ERROR_{ret}"}

    accounts = msg.get("list", [])
    result = []
    for acc in accounts:
        result.append({
            "fakeid": acc.get("fakeid", ""),
            "nickname": acc.get("nickname", ""),
            "alias": acc.get("alias", ""),
            "round_head_img": acc.get("round_head_img", ""),
            "service_type": acc.get("service_type", -1),
            "qrcode_url": acc.get("qrcode_url", ""),
        })

    return {"success": True, "accounts": result, "total": len(result)}
