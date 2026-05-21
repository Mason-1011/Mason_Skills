"""Simplified HTML cleaning for WeChat article content.

Combines fix_images() from wxarticle.py with basic HTML cleaning from htmltools.py.
No database or filter_rule dependencies.
"""

import re
from bs4 import BeautifulSoup


def fix_images(content: str) -> str:
    """Fix image URLs in article content (data-src -> src, width normalization)."""
    if not content:
        return ""
    try:
        soup = BeautifulSoup(content, "html.parser")
        soup.attrs.pop("style", None)
        for img in soup.find_all("img"):
            if "data-src" in img.attrs:
                img["src"] = img["data-src"]
                del img["data-src"]
            if "style" in img.attrs:
                img["style"] = re.sub(r"width\s*:\s*\d+\s*px", "width: 1080px", img["style"])
        return soup.prettify()
    except Exception:
        return content


def clean_article_content(html_content: str) -> str:
    """Clean article HTML: fix images, remove script/style tags and non-content elements."""
    if not html_content:
        return ""

    html_content = fix_images(html_content)

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style tags
        for tag in soup.find_all(["script", "style", "link", "head"]):
            tag.decompose()

        # Remove elements by ID
        remove_ids = [
            "content_bottom_interaction",
            "activity-name",
            "meta_content",
            "js_article_bottom_bar",
            "js_pc_weapp_code",
            "js_novel_card",
            "js_pc_qr_code",
        ]
        for rid in remove_ids:
            for el in soup.find_all(id=rid):
                el.decompose()

        # Remove hidden elements
        for el in soup.find_all(style=re.compile(r"display\s*:\s*none")):
            el.decompose()
        for el in soup.find_all(attrs={"aria-hidden": "true"}):
            el.decompose()

        return str(soup)
    except Exception:
        return html_content


def get_description(content: str, length: int = 200) -> str:
    """Extract plain text description from HTML content."""
    if not content:
        return ""
    try:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text().strip().strip("\n").replace("\n", " ").replace("\r", " ")
        return text[:length] + "..." if len(text) > length else text
    except Exception:
        return ""
