---
name: wechat-article
description: Search WeChat Official Accounts, list their articles, and fetch full article content. Includes auto-login via QR code.
trigger: User asks to search WeChat accounts, find WeChat articles, fetch WeChat article content, or work with WeChat Official Account (公众号) articles.
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

### Search Official Accounts

```bash
cd "${CLAUDE_SKILL_DIR}/scripts" && python __main__.py search "ACCOUNT_NAME" --limit 10
```

Returns `fakeid`, `nickname`, `alias`. `fakeid` is needed for listing articles.

**When `search` returns multiple accounts, use `AskUserQuestion` to let the user pick which account to use.** Present each account as an option with `nickname` (and `alias` if available) as the label, and `fakeid` as the value. Then use the selected `fakeid` for the subsequent `list` command.

### Get Article List

```bash
cd "${CLAUDE_SKILL_DIR}/scripts" && python __main__.py list "FAKEID" --name "ACCOUNT_NAME" --pages 2
```

Each page = ~5 articles. Returns `title`, `link`, `cover`, `digest`, timestamps.

### Fetch Full Article Content

```bash
cd "${CLAUDE_SKILL_DIR}/scripts" && python __main__.py fetch "https://mp.weixin.qq.com/s/ARTICLE_ID"
```

Returns `title`, `author`, `description`, `content` (HTML), `publish_time`, `mp_info`.
Does NOT need a token — opens article URL directly in browser.

### Manual Login

```bash
cd "${CLAUDE_SKILL_DIR}/scripts" && python __main__.py login
```

### Check Token

```bash
cd "${CLAUDE_SKILL_DIR}/scripts" && python __main__.py check-token
```

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
