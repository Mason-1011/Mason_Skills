# Mason's Skills

个人 [Claude Code Skills](https://code.claude.com/docs/en/skills) 合集，遵循 [Agent Skills](https://agentskills.io) 开放标准。

安装方式：将 `.claude/skills/` 下的 skill 目录复制到目标机器的 `.claude/skills/` 即可。

## Skills

### wechat-article

微信公众号文章获取工具。支持搜索公众号、获取文章列表、提取文章全文。

**功能：**
- 搜索公众号（返回 fakeid、名称、头像）
- 获取公众号文章列表（分页）
- 提取文章完整内容（标题、作者、正文HTML、图片、公众号信息）
- 扫码登录（token 过期时自动触发）

**依赖：**
```bash
pip install requests PyYAML beautifulsoup4 lxml playwright
python -m playwright install firefox
```

**用法：** 参见 `.claude/skills/wechat-article/SKILL.md`
