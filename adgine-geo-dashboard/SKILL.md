---
name: adgine/geo-dashboard
description: Fetches the top-level project dashboard snapshot for a GEO project — aggregate metrics (visibility score, prompts/topics/tests counts, citations, articles, AI referrals), the lightweight 7-day brand visibility trend, and the status of connected third-party data integrations (GA4, Cloudflare). Use when the user asks about project overview, dashboard, 项目总览, Dashboard 概览, 首页指标, visibility snapshot, 可见度得分, 7-day trend, 近七天趋势, integration status, 集成状态, GA4/Cloudflare connection, 数据集成, or wants a quick health/at-a-glance snapshot of a project.
---

# GEO Dashboard

Project-level snapshot skill: aggregate metrics, lightweight visibility trend,
and third-party integration status. Use this for the "what's the state of my
project right now" question.

For deep visibility analytics (matrix, share-of-voice, topic/prompt drill-down)
use the **adgine-geo-visibility** skill instead.

## Step 1: Locate your API key

**A)** `printenv GEO_API_KEY` → returns a value → proceed.
**B)** `grep '^GEO_API_KEY=' .env 2>/dev/null` → found → `export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)`
**C)** Not found → ask the user for a key from the GEO platform, then `export GEO_API_KEY=geo_sk_live_xxx`

> In shell commands always reference the key as `$GEO_API_KEY`. Never hardcode the literal value.

## Step 2: Identify project ID

Set `export GEO_PROJECT_ID=<id>` or pass `--project-id <id>` to each script.
Run `python3 scripts/list_projects.py` from the **adgine-geo-projects** skill if unknown.

## Scripts

### 1) Project overview snapshot

```bash
python3 scripts/get_overview.py [--project-id <id>] [--period 30d] [--json]
```

- **Period options:** `7d` · `14d` · `30d` (default) · `90d`
- Returns the aggregate Dashboard home metrics (visibility, prompts, topics,
  tests, citations, articles, AI referrals — whichever the API includes).

### 2) Lightweight 7-day visibility snapshot

```bash
python3 scripts/get_visibility_overview.py [--project-id <id>] \
    [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--json]
```

- Returns current visibility score, period-over-period change, and the daily
  trend list. Optimised for a small inline widget; for full analytics use the
  `adgine-geo-visibility` skill.

### 3) Third-party integration status

```bash
python3 scripts/check_integrations.py list                              # list all
python3 scripts/check_integrations.py status --service ga4              # one service
python3 scripts/check_integrations.py disconnect --service ga4 --yes    # DESTRUCTIVE
```

- Services typically include `ga4` and `cloudflare`.
- `disconnect` requires `--yes`. Without it the script prints a confirmation
  prompt and exits non-zero.

## Output Format

> **Table cell rule (must follow exactly):**
> Use fenced code blocks with box-drawing border tables. They align perfectly
> **only if every cell is ASCII**.
> - **NEVER** put emoji (✅ ❌ 📈 etc.) inside table cells. They render as 2
>   display units but count as 1 character → all later columns shift.
> - Emoji are allowed only on the label line **above** the opening ` ``` ` fence.
> - Status cell vocabulary: `Connected` / `Pending` / `Disconnected` (NOT ✅ / ❌).
> - Change cell vocabulary: `+N` / `-N` / `--` (NOT 📈 / 📉). `0` means exact zero.
> - Keep total table width ≤60 chars (Telegram mobile friendly).

### Recommended layout

> 📊 **Dashboard Overview** — `<start>` → `<end>` (`<period>`)

📈 Snapshot
```
┌────────────────────────┬──────────┬──────────┐
│ Metric                 │    Value │ vs Prev  │
├────────────────────────┼──────────┼──────────┤
│ Visibility Score       │     72.3 │ +1.5     │
│ Prompts (total)        │      128 │ +6       │
│ Topics                 │       12 │ 0        │
│ Tests run              │    1,540 │ +220     │
│ Citations              │      342 │ +18      │
└────────────────────────┴──────────┴──────────┘
```

📡 Integrations
```
┌────────────────┬──────────────┬──────────────────────┐
│ Service        │ Status       │ Connected at         │
├────────────────┼──────────────┼──────────────────────┤
│ ga4            │ Connected    │ 2025-08-12 09:14     │
│ cloudflare     │ Disconnected │ --                   │
└────────────────┴──────────────┴──────────────────────┘
```

## When to suggest other skills

| User intent | Suggest |
|---|---|
| Deep visibility / share-of-voice / matrix / per-topic / per-prompt drill-down | `adgine/geo-visibility` |
| AI bot crawler traffic, ChatGPT/Gemini/Perplexity crawlers, page-by-bot detail | `adgine/geo-aiagent` |
| Connect GA4 or Cloudflare (OAuth / Worker deploy) | `adgine/geo-integrations` |
| Listing or selecting projects | `adgine/geo-projects` |

## Related endpoints

| Method | Path |
|---|---|
| GET | `/api/projects/{id}/dashboard/overview` |
| GET | `/api/projects/{id}/dashboard/visibility` |
| GET | `/api/projects/{id}/integrations` |
| GET | `/api/projects/{id}/integrations/{service}/status` |
| DELETE | `/api/projects/{id}/integrations/{service}` |
