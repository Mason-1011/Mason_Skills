# Mason's Skills

A collection of [Claude Code Skills](https://code.claude.com/docs/en/skills) following the [Agent Skills](https://agentskills.io) open standard.

## Installation

Install all skills at once:

```bash
npx skills add Mason-1011/Mason_Skills -g -y
```

Or install individual skills:

```bash
npx skills add Mason-1011/Mason_Skills@content-creation -g -y
npx skills add Mason-1011/Mason_Skills@perrow-system-safety -g -y
npx skills add Mason-1011/Mason_Skills@macos-app-store-readiness -g -y
npx skills add Mason-1011/Mason_Skills@wechat-article -g -y
npx skills add Mason-1011/Mason_Skills@z-library-books -g -y
```

## Skills

| Skill | Description |
|-------|-------------|
| [content-creation](skills/content-creation/) | Content creation methodology — finding angles, designing rhythm, avoiding information aggregation |
| [macos-app-store-readiness](skills/macos-app-store-readiness/) | macOS App Store submission audit with severity-scored HTML reports |
| [perrow-system-safety](skills/perrow-system-safety/) | Charles Perrow's Normal Accident Theory for system safety analysis |
| [wechat-article](skills/wechat-article/) | WeChat Official Account article search and full-text fetch |
| [z-library-books](skills/z-library-books/) | Z-Library book search and download via browser automation |

## Setup Notes

Some skills require additional setup:

### wechat-article

Requires Python dependencies and Playwright:

```bash
pip install requests PyYAML beautifulsoup4 lxml playwright
python -m playwright install firefox
```

Login is handled automatically via QR code scan when needed.

### z-library-books

Requires Python and Playwright:

```bash
pip install playwright
python3 -m playwright install chromium
```

Set your Z-Library credentials as environment variables:

```bash
export ZLIBRARY_EMAIL="your-email@example.com"
export ZLIBRARY_PASSWORD="your-password"
```

A network proxy may be required — set `HTTPS_PROXY` and `HTTP_PROXY`.

## License

MIT
