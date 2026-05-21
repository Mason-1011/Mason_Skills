"""Fetch full content of a single WeChat article using Playwright.

Source: WeChat_OA_Bot/driver/wxarticle.py WXArticleFetcher.get_article_content()
"""

import base64
import re
from datetime import datetime
from playwright_driver import PlaywrightController
from html_clean import clean_article_content, get_description


DELETED_MARKERS = [
    "该内容已被发布者删除",
    "The content has been deleted by the author.",
    "内容审核中",
    "该内容暂时无法查看",
    "违规无法查看",
    "发送失败无法查看",
    "Unable to view this content because it violates regulation",
]

ENV_ERROR_MARKER = "当前环境异常，完成验证后即可继续访问"


def _extract_id_from_url(url: str) -> str:
    """Extract article ID from WeChat article URL."""
    try:
        match = re.search(r"/s/([A-Za-z0-9_-]+)", url)
        if not match:
            return ""
        id_str = match.group(1)
        padding = 4 - len(id_str) % 4
        if padding != 4:
            id_str += "=" * padding
        try:
            return base64.b64decode(id_str).decode("utf-8")
        except Exception:
            return id_str
    except Exception:
        return ""


def _extract_biz_from_url(url: str) -> str:
    """Extract biz parameter from URL."""
    match = re.search(r"[?&]__biz=([^&]+)", url)
    if match:
        return match.group(1)
    return ""


def _convert_publish_time(time_str: str) -> int:
    """Convert publish time string to timestamp."""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y年%m月%d日 %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y年%m月%d日",
        "%m月%d日",
    ]
    for fmt in formats:
        try:
            if fmt == "%m月%d日":
                current_date = datetime.now()
                full_str = f"{current_date.year}年{time_str}"
                dt = datetime.strptime(full_str, "%Y年%m月%d日")
                if dt > current_date:
                    dt = dt.replace(year=current_date.year - 1)
            else:
                dt = datetime.strptime(time_str, fmt)
            return int(dt.timestamp())
        except ValueError:
            continue
    return int(datetime.now().timestamp())


def get_article_content(url: str, headless: bool = True) -> dict:
    """Fetch full content of a single WeChat article.

    Args:
        url: WeChat article URL (https://mp.weixin.qq.com/s/XXXX)
        headless: Run browser in headless mode

    Returns:
        dict with: success, title, author, description, content (HTML),
                    publish_time, mp_info, mp_id, error
    """
    info = {
        "id": _extract_id_from_url(url),
        "title": "",
        "author": "",
        "description": "",
        "topic_image": "",
        "publish_time": "",
        "content": "",
        "images": [],
        "mp_info": {"mp_name": "", "logo": "", "biz": ""},
        "mp_id": "",
        "fetch_error": "",
    }

    controller = PlaywrightController()
    body = ""

    try:
        controller.start_browser(headless=headless)
        page = controller.page
        controller.open_url(url)

        body = page.locator("body").text_content().strip()

        # Check for environment error
        if ENV_ERROR_MARKER in body:
            return {"success": False, "error": "Environment verification required. IP may be temporarily blocked.", "code": "ENV_ERROR"}

        # Check for deleted/unavailable content
        for marker in DELETED_MARKERS:
            if marker in body:
                return {"success": True, "content": "DELETED", "title": info["title"], "error": marker, "code": "DELETED"}

        # Extract metadata
        try:
            info["title"] = page.locator('meta[property="og:title"]').get_attribute("content") or ""
        except Exception:
            info["title"] = page.evaluate("() => document.title") or ""

        try:
            info["author"] = page.locator('meta[property="og:article:author"]').get_attribute("content") or ""
        except Exception:
            pass

        try:
            info["description"] = page.locator('meta[property="og:description"]').get_attribute("content") or ""
        except Exception:
            pass

        try:
            info["topic_image"] = page.locator('meta[property="twitter:image"]').get_attribute("content") or ""
        except Exception:
            pass

        # Extract article body content
        try:
            content_el = page.locator("#js_content")
            content = content_el.inner_html()
            if not content:
                content_el = page.locator("#js_article")
                content = content_el.inner_html()
            info["content"] = clean_article_content(content)
        except Exception:
            info["content"] = ""

        # Extract images
        try:
            images = [
                img.get_attribute("data-src") or img.get_attribute("src")
                for img in page.locator("#js_content img").all()
                if img.get_attribute("data-src") or img.get_attribute("src")
            ]
            info["images"] = images
        except Exception:
            pass

        # Extract publish time
        try:
            publish_time_str = page.locator("#publish_time").text_content().strip()
            info["publish_time"] = _convert_publish_time(publish_time_str)
        except Exception:
            info["publish_time"] = ""

        # Extract MP info
        try:
            logo_el = page.locator("#js_like_profile_bar .wx_follow_avatar img")
            logo_src = logo_el.get_attribute("src")
            mp_name = page.evaluate('() => $("#js_wx_follow_nickname").text()')
            biz = page.evaluate("() => window.biz")
            if not biz:
                biz = _extract_biz_from_url(url)

            info["mp_info"] = {
                "mp_name": mp_name or "",
                "logo": logo_src or "",
                "biz": biz or "",
            }
            if biz:
                try:
                    info["mp_id"] = "MP_WXS_" + base64.b64decode(biz).decode("utf-8")
                except Exception:
                    info["mp_id"] = ""
        except Exception:
            pass

        # Generate description from content if not available
        if not info["description"] and info["content"]:
            info["description"] = get_description(info["content"])

        return {"success": True, **info}

    except Exception as e:
        body_preview = body[:100] if body else "N/A"
        return {"success": False, "error": str(e), "body_preview": body_preview, "code": "FETCH_ERROR"}

    finally:
        controller.Close()
