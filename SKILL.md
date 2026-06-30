---
name: adgine/geo
description: >
  Adgine GEO 平台完整技能套件，包含 18 个专项技能，覆盖生成式引擎优化（GEO）全流程：
  网站技术审计、AI 引用测试、AI 可见性分析、内容生成、品牌画像、主题词管理、
  WordPress 发布、GA4/Cloudflare 集成、域名管理、项目管理、账单查询、使用手册等。
  触发词：GEO / Adgine / AI visibility / AI citation / 生成式引擎优化 / AI 可见性 /
  引用测试 / 内容生成 / 网站审计 / 品牌画像 / WordPress 发布 / 流量分析 /
  AI 爬虫追踪 / 优化机会 / 页面健康度 / 域名 / 账单 / 积分 / 项目管理.
version: "1.1.0"
---

## 版本检测（每次对话开始时执行一次）

```bash
python3 <SKILL_DIR>/scripts/check_version.py
```

处理规则：
- 脚本失败 / 超时 / 输出为空：静默忽略，继续正常响应
- `update_available=false`：不输出任何版本相关内容
- `update_available=true`：完成用户当前请求后，在回复末尾追加如下更新提示（根据 install_type 选择对应版本）：

**install_type="git" 时的提示模板：**

---
💡 **adgine-geo-skills 有新版本 {latest}**（当前 {current}）

发给我下面这句话，我来帮你一键更新：
> 请帮我更新 adgine-geo-skills 到最新版本
---

**install_type="package" 时的提示模板：**

---
💡 **adgine-geo-skills 有新版本 {latest}**（当前 {current}）

请前往以下地址下载最新版本，然后在平台 Skill 管理界面重新安装：
{release_url}
---

## 更新处理（当用户说"请帮我更新 adgine-geo-skills"时触发）

执行：
```bash
{update_command}
```
成功后回复：「✅ 已更新到最新版本，当前版本已是 {latest}，重新开始对话即可使用新版功能。」
失败则输出错误信息供用户排查。

---

# Adgine GEO Skills Suite

本套件包含 18 个专项技能，覆盖 Adgine GEO 平台全流程。根据用户意图路由到对应子技能。

## 子技能路由表

| 子技能 | 用于 |
|---|---|
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
| adgine/geo-saas | 检查子域名可用性、创建并追踪 SaaS 托管网站部署任务 |
| adgine/geo-billing | 查询订阅套餐、订阅状态、积分余额和充值明细（只读，不执行购买） |
| adgine/geo-domains | 按关键词搜索可注册域名、列出已注册域名、查看域名详情 |
| adgine/geo-site-audit | 对任意公开 URL 做独立 GEO 技术审计（5 大维度 / 30 项检测 / 导出 PDF），**无需 API Key** |
| adgine/geo-docs | Adgine 平台使用手册、帮助文档、操作指南，**无需 API Key** |

## 工作流说明

部分功能需要多个子技能协作：

- **内容发布**：`geo-content`（生成文章）→ `geo-wordpress`（发布到 WordPress）
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
