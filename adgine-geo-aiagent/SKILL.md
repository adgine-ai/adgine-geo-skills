---
name: adgine/geo-aiagent
description: Tracks how AI bots (AI bot, AI 机器人, AI 爬虫, AI crawler, ChatGPT/Perplexity/Gemini 爬虫, GPTBot, ClaudeBot, GoogleBot, PerplexityBot, Anthropic, OpenAI bot) crawl a website AND how real humans arrive via AI platforms. Covers bot-traffic KPIs (AI citation / index / training / agent), bot type/platform/User-Agent breakdowns; human visits (UTM + referral + GA4 sessions / revenue); site-wide page rankings, 5-metric page tables, AI-platform→page Sankey flows, raw event logs, and per-page deep dives (KPI / logs / platforms / sibling pages / PageSpeed Insights). Use when the user asks about AI 爬虫追踪 / AI bot tracking / 机器人访问 / which AI platforms crawl my site / 哪些 AI 引用我的页面 / AI referral / AI 引荐 / AI 真人访问 / GA4 AI 流量 / 页面健康分 / Core Web Vitals / page detail / page sankey. For brand/topic visibility metrics use adgine-geo-visibility.
---

# GEO AI-Agent Tracking

The biggest analytics skill — 27 endpoints under `/api/projects/{id}/ai-agent/*`.
Grouped into 4 scripts by user intent:

- **bot_traffic.py** — which AI bots crawl my site, how often, what kind
- **human_traffic.py** — what real human traffic AI platforms send me
- **page_analytics.py** — site-wide page rankings, Sankey flow, logs
- **page_detail.py** — deep-dive analytics for a specific page path

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
