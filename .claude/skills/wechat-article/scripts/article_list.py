"""Get article list for a WeChat Official Account.

Source: WeChat_OA_Bot/core/wx/model/web.py MpsWeb.get_Articles()
API: GET https://mp.weixin.qq.com/cgi-bin/appmsgpublish
"""

import json
import random
import time
import requests
import wx_token as token


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
]


def _parse_publish_page(publish_page: dict) -> list:
    """Parse the nested publish_page structure into a flat article list."""
    articles = []
    for item in publish_page.get("publish_list", []):
        publish_info_raw = item.get("publish_info", "")
        if isinstance(publish_info_raw, str):
            try:
                publish_info = json.loads(publish_info_raw)
            except json.JSONDecodeError:
                continue
        else:
            publish_info = publish_info_raw

        for appmsg in publish_info.get("appmsgex", []):
            articles.append({
                "id": appmsg.get("aid", ""),
                "title": appmsg.get("title", ""),
                "link": appmsg.get("link", ""),
                "cover": appmsg.get("cover", ""),
                "digest": appmsg.get("digest", ""),
                "update_time": appmsg.get("update_time", ""),
                "create_time": appmsg.get("create_time", ""),
                "item_show_type": appmsg.get("item_show_type", 0),
                "copyright_stat": appmsg.get("copyright_stat", 0),
                "is_deleted": appmsg.get("is_deleted", False),
            })
    return articles


def get_article_list(
    fakeid: str,
    mp_name: str = "",
    max_pages: int = 1,
    interval: int = 5,
) -> dict:
    """Get article list for a specific official account.

    Args:
        fakeid: Account fakeid (from search_accounts)
        mp_name: Display name for logging
        max_pages: Number of pages to fetch (each page = 5 articles)
        interval: Max seconds to wait between page requests

    Returns:
        dict with: success, articles (list), count, error
    """
    tk = token.get("token", "")
    cookies = token.get("cookie", "")

    if not tk:
        return {"success": False, "error": "Token not found. Please login to WeChat MP platform first.", "code": "NO_TOKEN"}

    url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
    count = 5
    all_articles = []

    session = requests.Session()

    for page_idx in range(max_pages):
        begin = page_idx * count
        params = {
            "sub": "list",
            "sub_action": "list_ex",
            "begin": begin,
            "count": count,
            "fakeid": fakeid,
            "token": tk,
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1,
        }
        headers = {
            "Cookie": cookies,
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        # Random delay between pages
        if page_idx > 0:
            delay = random.randint(1, interval)
            time.sleep(delay)

        try:
            resp = session.get(url, headers=headers, params=params, verify=False, timeout=(10, 30))
            msg = resp.json()
        except requests.exceptions.RequestException as e:
            if page_idx == 0:
                return {"success": False, "error": f"Request failed: {e}", "code": "REQUEST_ERROR"}
            break
        except json.JSONDecodeError:
            if page_idx == 0:
                return {"success": False, "error": "Invalid JSON response", "code": "PARSE_ERROR"}
            break

        base_resp = msg.get("base_resp", {})
        ret = base_resp.get("ret", -1)

        if ret == 200013:
            return {"success": False, "error": "Rate limited by WeChat", "code": "RATE_LIMITED", "articles": all_articles, "count": len(all_articles)}
        if ret == 200003:
            return {"success": False, "error": "Session expired. Please re-login.", "code": "INVALID_SESSION", "articles": all_articles, "count": len(all_articles)}
        if ret != 0:
            return {"success": False, "error": f"API error: {base_resp.get('err_msg', 'unknown')}", "code": f"API_ERROR_{ret}", "articles": all_articles, "count": len(all_articles)}

        if "publish_page" not in msg:
            break

        publish_page_raw = msg["publish_page"]
        if isinstance(publish_page_raw, str):
            try:
                publish_page = json.loads(publish_page_raw)
            except json.JSONDecodeError:
                break
        else:
            publish_page = publish_page_raw

        page_articles = _parse_publish_page(publish_page)
        all_articles.extend(page_articles)

        # If fewer articles than expected, no more pages
        if len(page_articles) < count:
            break

    return {"success": True, "articles": all_articles, "count": len(all_articles)}
