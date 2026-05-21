---
name: wechat-article
description: "Search WeChat Official Accounts, list their articles, and fetch full article content with auto-login via QR code. Use when the user wants to search WeChat accounts, find WeChat articles, fetch WeChat article content, or work with WeChat Official Account (公众号) articles."
license: MIT
metadata:
  author: Mason-1011
  compatibility: claude-code
---

# WeChat Article Fetcher

Fetches articles from WeChat Official Accounts (微信公众号).

All scripts are in `${CLAUDE_SKILL_DIR}/scripts/`. Run commands from that directory.

## Setup (first time on a new machine)

```bash
pip install requests PyYAML beautifulsoup4 lxml playwright
python -m playwright install firefox
```

## Token Auto-Login

**`search` and `list` commands automatically check the token. If expired or missing, they trigger QR code login — no manual check/login needed.**

When auto-login triggers:
1. QR code image is saved and opened (Windows) automatically
2. Tell the user: "请用微信扫描二维码登录公众平台"
3. Wait for the command to complete (up to 5 minutes)
4. Login succeeds → original command proceeds automatically
5. Login fails → tell user "扫码登录失败，请重试" and suggest running the command again

## Commands

### 搜索公众号

```bash
cd "${CLAUDE_SKILL_DIR}/scripts" && python __main__.py search "ACCOUNT_NAME" --limit 10
```

按名称搜索公众号，返回 fakeid、名称、别名。fakeid 用于获取文章列表。

**When `search` returns multiple accounts, use `AskUserQuestion` to let the user pick which account to use.** Present each account as an option with `nickname` (and `alias` if available) as the label, and `fakeid` as the value. Then use the selected `fakeid` for the subsequent `list` command.

### 获取文章列表

```bash
cd "${CLAUDE_SKILL_DIR}/scripts" && python __main__.py list "FAKEID" --name "ACCOUNT_NAME" --pages 2
```

分页获取公众号历史文章，每页约5篇。返回标题、链接、封面、摘要、时间戳。

### 获取文章全文

```bash
cd "${CLAUDE_SKILL_DIR}/scripts" && python __main__.py fetch "https://mp.weixin.qq.com/s/ARTICLE_ID"
```

提取文章完整内容，返回标题、作者、描述、正文(HTML)、发布时间、公众号信息。无需 token，直接打开文章 URL。

### 手动登录

```bash
cd "${CLAUDE_SKILL_DIR}/scripts" && python __main__.py login
```

手动触发扫码登录，用于 token 失效时重新获取。

### 检查 Token

```bash
cd "${CLAUDE_SKILL_DIR}/scripts" && python __main__.py check-token
```

检查当前 token 是否有效，过期时需重新登录。

## Error Handling

- Auto-login succeeds → original command proceeds, no extra action
- Auto-login fails → tell user to try the command again
- `search` returns `RATE_LIMITED` → wait 30-60s, retry
- `fetch` returns `ENV_ERROR` → IP blocked, wait and retry
- `fetch` returns `DELETED` → article removed by author
- `fetch` returns `FETCH_ERROR` → may retry once

## Notes

- Add 3-10 second delays between API requests
- `fetch` takes 10-30s per article (headless Playwright/Firefox)
- All commands output JSON to stdout
- `content` from `fetch` is HTML
- Start with `--pages 1` for article lists
