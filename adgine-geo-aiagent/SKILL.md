---
name: adgine/geo-aiagent
description: Deep drill-down tracking for AI bot crawls and AI-driven human traffic
  — 27 endpoints covering per-bot/per-platform/per-UA breakdowns, Sankey flows,
  raw event logs, and per-page deep dives (KPI / logs / platforms / PageSpeed).
  Use when the user wants detail-level data: AI 爬虫追踪 / which specific AI bots
  crawl my site / GPTBot ClaudeBot PerplexityBot / 某个页面被哪些 AI 爬虫访问过 /
  page detail / page sankey / Core Web Vitals / AI 真人访问来源明细.
  NOT for high-level traffic summary — use adgine-geo-analytics for that.
  NOT for running citation tests — use adgine-geo-citation.
  NOT for page AI-optimization health scores — use adgine-geo-performance.
  For brand/topic visibility metrics use adgine-geo-visibility.
---

# GEO AI-Agent Tracking

The biggest analytics skill — 27 endpoints under `/api/projects/{id}/ai-agent/*`.
Grouped into 4 scripts by user intent:

- **bot_traffic.py** — which AI bots crawl my site, how often, what kind
- **human_traffic.py** — what real human traffic AI platforms send me
- **page_analytics.py** — site-wide page rankings, Sankey flow, logs
- **page_detail.py** — deep-dive analytics for a specific page path

## 触发条件

当用户说出以下意图时使用本 skill：
- “哪些 AI 爬虫访问了我的网站” / “GPTBot/ClaudeBot/PerplexityBot” / “AI bot tracking”
- “某个页面被哪些 AI 爬虫访问过” / “页面爬虫日志” / “page detail”
- “AI 真人访问” / “AI 引荐来源明细” / “AI referral breakdown”
- “Sankey 图” / “页面流量流向” / “爬虫访问日志”

**⛔ 以下意图不属于本 skill：**
- “流量概览” / “流量汇总”（不涉及具体 bot 明细）→ **adgine-geo-analytics**
- “某个页面的 AI 优化健康度” / “页面可爬取性” → **adgine-geo-performance**
- “运行引用测试” / “品牌被引用了吗” → **adgine-geo-citation**
- “可见性得分” / “声量份额” → **adgine-geo-visibility**

## Output rules — IDs (apply to every reply)

These rules apply to **every list, table, and confirmation message** in this skill. Their goal: keep user-facing output friendly while preserving the IDs the agent needs internally.

1. **Lists & tables — never show raw UUIDs in cells.** Use a 1-based `#` index column instead. Keep a private mental mapping of `#N → actual UUID` so that follow-up commands like *"delete #3"*, *"run citation test on #1 #2"*, *"show details of the 2nd one"* resolve to the right entity.
   - Index numbers restart from 1 in each new list — they are not stable across calls.
   - If the user references *"the topic about X"* / *"that Poki vs CrazyGames prompt"*, match by visible content (name / title / domain / prompt text), not by ID.

2. **Single-item operations — prefer a human name over an ID.**
   - ✅ *"Project **Poki vs Competitors** deleted."*
   - ✅ *"Topic **Brand mentions in 2024** updated — name → 'Brand mentions 2025'."*
   - ❌ *"Project `a4305b57-1c79-4cec-a17c-16eb1d959ea6` deleted."*
   - If the entity has **no human-readable name** (e.g. an anonymous prompt or a job), use a short 8-character prefix: *"Prompt `2a2a8f4f…` deleted."* Never paste the full UUID.

3. **Always exception: `--json` mode.** When the user passes `--json` to a script or explicitly asks for raw JSON / debug output, print the script output verbatim — do not strip IDs.

4. **Internally, the agent still uses full UUIDs** for every API call (`--project-id`, `--topic-id`, `--prompt-id`, etc.). The display rules only affect what is shown back to the user.

---

## Step 1: Make sure GEO_API_KEY is configured

Scripts auto-load `GEO_API_KEY` from `<skills-root>/.env` on import — **no `export` needed, no shell restart needed**. To check the configuration, run any script (it prints the exact `.env` path if the key is missing).

- ✅ Key already in `<skills-root>/.env` → proceed.
- ❌ Key missing, or user just gave you a new key → go to the **adgine-geo-projects** skill, **Step 0**, which runs `python3 <skills-root>/setup.py <KEY>` to write the key into the correct `.env` file. **Never** write the key to `~/.zshrc`, `~/.bashrc`, Hermes global config, or any user-secrets store.

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as `$GEO_API_KEY` (the environment variable). Never hardcode the literal value.

## Project selection

```bash
export GEO_PROJECT_ID=<project-id>
```

## Scripts

### bot_traffic.py — AI bot/crawler tracking

```bash
python3 scripts/bot_traffic.py overview          # 5 KPI: citation/training/index/agent/total
python3 scripts/bot_traffic.py platforms         # ranking: which AI platforms crawl most
python3 scripts/bot_traffic.py by-platform       # bots grouped by AI platform
python3 scripts/bot_traffic.py types             # index/training/assistant/agent split
python3 scripts/bot_traffic.py useragents        # by specific UA (GPTBot, ClaudeBot...)
python3 scripts/bot_traffic.py pages-by-bot      # per-bot top pages
```

### human_traffic.py — humans driven by AI platforms

```bash
python3 scripts/human_traffic.py overview        # 3 KPI: UTM / referral / share
python3 scripts/human_traffic.py platforms       # human visits by AI platform
python3 scripts/human_traffic.py pages           # human visits per page
python3 scripts/human_traffic.py platform-flow   # Sankey: AI platform → landing page
python3 scripts/human_traffic.py referral        # referral-only by source

# GA4-backed (requires GA4 connected):
python3 scripts/human_traffic.py ga-overview
python3 scripts/human_traffic.py ga-platforms
python3 scripts/human_traffic.py ga-landing-pages
python3 scripts/human_traffic.py ga-landing-flow
```

### page_analytics.py — site-wide

```bash
python3 scripts/page_analytics.py overview-kpi             # citation/index/training/agent/referral
python3 scripts/page_analytics.py pages                    # top AI-referenced pages
python3 scripts/page_analytics.py pages-detail             # 5-metric table per page
python3 scripts/page_analytics.py pages-export --format csv > pages.csv
python3 scripts/page_analytics.py platform-flow            # Sankey
python3 scripts/page_analytics.py logs                     # raw AI event logs
```

### page_detail.py — specific page path

All commands require `--path /your/page/path`.

```bash
python3 scripts/page_detail.py kpi       --path /blog/article
python3 scripts/page_detail.py logs      --path /blog/article --limit 20
python3 scripts/page_detail.py platforms --path /blog/article
python3 scripts/page_detail.py related   --path /blog/article
python3 scripts/page_detail.py health    --path /blog/article
python3 scripts/page_detail.py health-refresh --path /blog/article   # 15–60s blocking
```

## Metric vocabulary

| Code           | Meaning |
|---|---|
| `ai_citation`  | AI quoted / cited this page in an answer |
| `ai_index`     | AI search index crawler hit |
| `ai_training`  | AI training data crawler hit |
| `ai_agent`     | AI agent (assistant tool-use) hit |
| `ai_referral`  | A real human arrived on the site via an AI platform |
| `total_bots`   | Sum of all AI bot requests |

## Platform codes

`openai` · `google_aio` · `perplexity` · `gemini` · `anthropic` · `meta`
(see `/api/projects/{id}/ai-agent/platforms` for the live list).

## Output Format

ASCII tables only inside fenced code blocks. Numeric formatting: integer
counts with thousands separator; "%" suffix only on percentage metrics;
"--" for null. Change-from-previous-period shown with explicit sign.

## Related endpoints

| Method | Path |
|---|---|
| GET    | `/api/projects/{id}/ai-agent/bot-platforms` |
| GET    | `/api/projects/{id}/ai-agent/bot-traffic-overview` |
| GET    | `/api/projects/{id}/ai-agent/bot-types` |
| GET    | `/api/projects/{id}/ai-agent/bot-useragents` |
| GET    | `/api/projects/{id}/ai-agent/ga-landing-pages` |
| GET    | `/api/projects/{id}/ai-agent/ga-overview` |
| GET    | `/api/projects/{id}/ai-agent/ga-platform-landing-flow` |
| GET    | `/api/projects/{id}/ai-agent/ga-platforms` |
| GET    | `/api/projects/{id}/ai-agent/human-pages` |
| GET    | `/api/projects/{id}/ai-agent/human-platform-flow` |
| GET    | `/api/projects/{id}/ai-agent/human-platforms` |
| GET    | `/api/projects/{id}/ai-agent/human-traffic-overview` |
| GET    | `/api/projects/{id}/ai-agent/logs` |
| GET    | `/api/projects/{id}/ai-agent/overview-kpi` |
| GET    | `/api/projects/{id}/ai-agent/pages` |
| GET    | `/api/projects/{id}/ai-agent/pages-by-bot` |
| GET    | `/api/projects/{id}/ai-agent/pages-detail` |
| GET    | `/api/projects/{id}/ai-agent/pages-detail/export` |
| GET    | `/api/projects/{id}/ai-agent/pages-platform-flow` |
| GET    | `/api/projects/{id}/ai-agent/pages/by-path/health` |
| POST   | `/api/projects/{id}/ai-agent/pages/by-path/health/refresh` |
| GET    | `/api/projects/{id}/ai-agent/pages/by-path/kpi` |
| GET    | `/api/projects/{id}/ai-agent/pages/by-path/logs` |
| GET    | `/api/projects/{id}/ai-agent/pages/by-path/platforms` |
| GET    | `/api/projects/{id}/ai-agent/pages/by-path/related` |
| GET    | `/api/projects/{id}/ai-agent/platforms` |
| GET    | `/api/projects/{id}/ai-agent/referral-traffic` |

---

## Post-task recommendations

After AI traffic analysis, suggest next analytical or action steps:

| What you analyzed | Suggest |
|---|---|
| Bot traffic overview | `adgine-geo-aiagent` — 深入查看具体 bot 详情或 page detail |
| Specific page traffic | `adgine-geo-performance` — 检查该页面的 AI 优化健康度 |
| Human referral traffic | `adgine-geo-analytics` — 查看 GA4 流量总览 |
| Sankey / platform flow | `adgine-geo-content` — 针对高流量入口页生成优化内容 |
| PageSpeed / Core Web Vitals | `adgine-geo-site-audit` — 对整个网站做全面 GEO 审计 |
| Low AI bot activity | `adgine-geo-integrations` — 检查 Cloudflare Worker 是否正常部署 |

> 💡 **建议下一步：**
> 1. **[action]** → `skill-name`
> 2. **[action]** → `skill-name`
