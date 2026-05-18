# Mason's Skills

个人 [Claude Code Skills](https://code.claude.com/docs/en/skills) 合集，遵循 [Agent Skills](https://agentskills.io) 开放标准。

安装方式：将 `.claude/skills/` 下的 skill 目录复制到目标机器的 `.claude/skills/` 即可。

## Skills

### content-creation

1. 第一步：获取信息（权重 30%） — 关键原则：跨领域获取，像管理投资组合一样管理信息源。
2. 第二步：找角度（权重 60%） — 这是三步里最重要的一步。角度决定一篇内容的生死。
3. 第三步：创作（权重 10%） — 创作权重最小，但决定生死。信息拿到了、角度找到了，讲不好故事就全白费。

**完整文档：** `.claude/skills/content-creation/SKILL.md`

### wechat-article

1. 搜索公众号 — 按名称搜索公众号，返回 fakeid、名称、别名。fakeid 用于获取文章列表。
2. 获取文章列表 — 分页获取公众号历史文章，每页约5篇。返回标题、链接、封面、摘要、时间戳。
3. 获取文章全文 — 提取文章完整内容，返回标题、作者、描述、正文(HTML)、发布时间、公众号信息。无需 token，直接打开文章 URL。
4. 手动登录 — 手动触发扫码登录，用于 token 失效时重新获取。
5. 检查 Token — 检查当前 token 是否有效，过期时需重新登录。

**完整文档：** `.claude/skills/wechat-article/SKILL.md`