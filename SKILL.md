---
name: adgine/geo
description: >
  Adgine GEO 平台完整技能套件，包含 20 个专项技能，覆盖生成式引擎优化（GEO）全流程：
  网站技术审计、AI 引用测试、AI 可见性分析、内容生成、品牌画像、主题词管理、
  WordPress 发布、GA4/Cloudflare 集成、域名管理、项目管理、账单查询、使用手册等。
  触发词：GEO / Adgine / AI visibility / AI citation / 生成式引擎优化 / AI 可见性 /
  引用测试 / 内容生成 / 网站审计 / 品牌画像 / WordPress 发布 / 流量分析 /
  AI 爬虫追踪 / 优化机会 / 页面健康度 / HTML 报告 / 我的账号信息 / 姓名 / 手机号 /
  邮箱 / 域名 / 账单 / 积分 / 项目管理.
---

## 版本检测（路由到任何子技能之前的第一步，必须执行）

在将用户请求路由到任何子技能之前，**先单独运行**版本检测（必须是本轮第一个 bash 命令）：

```bash
python3 <skills-root>/scripts/check_version.py --human
```

`<skills-root>` 是本仓库根目录（含 `VERSION`、`setup.py` 及所有 `adgine-geo-*` 文件夹）。

**WorkBuddy 特别注意：** WorkBuddy 会改写业务脚本的终端输出，可能丢掉嵌入的 `_notice` 或页脚。
因此 **必须** 用上面的 `--human` 命令做独立检测；若输出不为空，**在用户回复的最后一段原文包含该句**，禁止只展示业务结果而省略版本信息。

处理规则：
- 脚本失败 / 超时 / 输出为空：静默忽略，继续路由和响应
- `update_available=false`（`--human` 无输出）：不输出任何版本相关内容
- 有更新（`--human` 有输出）或 JSON 模式 `update_available=true`：完成用户当前请求后，在回复末尾追加更新提示（见下方模板）。同一轮对话只提示一次。

## 版本更新提示（脚本自动 + 必须处理）

本套件的**每个脚本**在运行时也会自动做版本检查（对比 GitHub 上的
`VERSION`）。如果有新版本，脚本会在**工具输出（stdout）第一行**打印
`_notice`，格式为：

```
_notice: {"update": {"current": "1.1.5", "latest": "1.2.0", "message": "..."}}
```

**处理规则（每次对话都适用）：**
- 主动版本检测 **或** 任何一次工具调用的输出里出现 `_notice`，且判定有更新
  → 先正常完成用户当前请求，然后在回复末尾追加一条更新提示（见下方模板）。
  同一轮对话只提示一次。
- 脚本还会在输出**末尾**打印人类可读页脚（以 `---` 和 `⚠️ adgine-geo-skills` 开头）。
  **WorkBuddy 等会改写工具输出的 Agent 也必须把这段页脚原样展示给用户**，不得省略。
- 两条途径均未检测到更新 → 不输出任何版本相关内容。

**更新提示模板（`message` 里含「Tell me:」= git 安装）：**

> 💡 **adgine-geo-skills 有新版本 {latest}**（当前 {current}）
> 发给我下面这句话，我来帮你一键更新：
> `请帮我更新 adgine-geo-skills 到最新版本`

**更新提示模板（`message` 里含「Download:」= 打包安装）：**

> 💡 **adgine-geo-skills 有新版本 {latest}**（当前 {current}）
> 请前往 {下载地址} 下载最新版本，在平台 Skill 管理界面重新安装。

## 更新处理（当用户说"请帮我更新 adgine-geo-skills"时触发）

运行 `python3 <SKILL_DIR>/scripts/check_version.py` 拿到 `update_command`，
然后执行它（git 安装形如 `git -C <repo_root> pull`）。
成功后回复：「✅ 已更新到最新版本 {latest}，重新开始对话即可使用新版功能。」
失败则输出错误信息供用户排查。

---

# Adgine GEO Skills Suite

本套件包含 20 个专项技能，覆盖 Adgine GEO 平台全流程。根据用户意图路由到对应子技能。

## 数据查询门面（必须优先）

凡是“查看、查询、分析、对比、盘点、状态、趋势、报告、导出”等只读数据请求，优先路由到
`adgine/geo-reports`，并由它生成离线 HTML 报告。专项技能中的读取脚本仅用于低层排障，
不得在报告完成后重复调用同一批接口做二次摘要。

用户询问“我的账号、账号基本信息、创建时间、姓名、手机号、邮箱”时，使用
`adgine/geo-reports account-info`。所有分页查询默认每页 40 条；下一页继续使用 40 条页长。
高频 Topic、Prompt、综合流量、页面、内容与运营报告优先使用 GEO-Api `/report-data` 聚合接口；
仅 capabilities 在本地缓存 2 小时，报表业务数据不缓存；只有接口缺失/未启用/版本不兼容时才回退旧读取接口。

创建、修改、删除、连接、同步、刷新、生成、发布、部署等写操作仍路由到对应专项技能。

## 子技能路由表

| 子技能 | 用于 |
|---|---|
| adgine/geo-reports | **所有只读数据查询的默认门面**：账号基本信息、场景化分析、目录/详情/状态报告、GA4/Cloudflare/AI Bot/页面机会、离线 HTML 输出 |
| adgine/geo-projects | 创建/列出/切换项目、管理竞争对手、配置 API Key（`GEO_API_KEY`）、验证鉴权 |
| adgine/geo-dashboard | 项目总览快照、7 天趋势、集成连接状态（首页指标 / Dashboard 概览） |
| adgine/geo-analytics | GA4 流量概览、活跃用户、AI 引荐汇总（不含爬虫明细） |
| adgine/geo-aiagent | AI 爬虫深度追踪：GPTBot / ClaudeBot / PerplexityBot、Sankey 流图、原始日志、页面级下钻 |
| adgine/geo-visibility | 读取 AI 可见性得分、Share of Voice、平均排名、竞品矩阵、历史 AI 回答 |
| adgine/geo-citation | 向 ChatGPT / Perplexity / Google AIO / Gemini 提交真实提示，测量品牌引用率 |
| adgine/geo-brand | 查看/生成/编辑 AI 品牌画像（ICP / 竞品分析 / 语气风格 / 写作规范）及生成任务管理 |
| adgine/geo-topics | 创建主题、批量生成 AI 搜索提示词、管理主题-提示词结构 |
| adgine/geo-content | 生成文章大纲和完整 GEO 文章、管理内容库、查看/重试内容生成任务 |
| adgine/geo-performance | 单页面 AI 优化健康度：可爬取性、AI 优化评分、内容健康（移动/桌面） |
| adgine/geo-opportunities | 发现 AI 识别的内容缺口和优化机会，按影响力（相关性/流量/竞争度/紧迫性）排序 |
| adgine/geo-integrations | 连接 GA4（OAuth）和 Cloudflare、部署 AI 爬虫追踪 Worker、触发数据同步 |
| adgine/geo-wordpress | 发布 GEO 文章到 WordPress、管理站点凭证和分类、查看发布历史、更新已发布文章 |
| adgine/geo-media-publish | 发布文章到本机浏览器已登录的社媒草稿箱（知乎/微信公众号/百家号/头条号/CSDN/小红书…），经 Chrome 扩展桥接，需桌面端 |
| adgine/geo-saas | 检查子域名可用性、创建并追踪 SaaS 托管网站部署任务 |
| adgine/geo-billing | 查询订阅套餐、订阅状态、积分余额和充值明细（只读，不执行购买） |
| adgine/geo-domains | 按关键词搜索可注册域名、列出已注册域名、查看域名详情 |
| adgine/geo-site-audit | 对任意公开 URL 做独立 GEO 技术审计（5 大维度 / 30 项检测 / 导出 PDF），**无需 API Key** |
| adgine/geo-docs | Adgine 平台使用手册、帮助文档、操作指南，**无需 API Key** |

## 工作流说明

部分功能需要多个子技能协作：

- **内容发布（WordPress）**：`geo-content`（生成文章）→ `geo-wordpress`（发布到 WordPress）
- **内容发布（社媒草稿箱）**：`geo-content`（生成文章）→ `geo-media-publish`（发布到知乎/公众号/头条等本机已登录平台）
- **引用测试**：`geo-topics`（创建提示词）→ `geo-citation`（运行测试）→ `geo-visibility`（查看结果）
- **所有平台功能**：先用 `geo-projects` 配置 API Key 并选定项目，再使用其他子技能

## 安装配置

git clone 后运行一次：

```bash
python3 setup.py <YOUR_GEO_API_KEY>
```

或交互式：`python3 setup.py`

## 更多信息

- 平台官网：[adgine.ai](https://adgine.ai/)
- GitHub：https://github.com/adgine-ai/adgine-geo-skills
