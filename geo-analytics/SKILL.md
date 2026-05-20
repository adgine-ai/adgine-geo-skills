---
name: adgine/geo-analytics
description: Queries SEO and traffic analytics for GEO projects, including Google
  Search Console search performance (clicks, impressions, CTR, keyword positions,
  top queries), Google Analytics 4 traffic data (sessions, active users, source
  breakdown), AI crawler and bot traffic, and site-wide dashboard overviews with
  comparison periods. Use when the user asks about website traffic, search rankings,
  organic clicks, impressions, click-through rate, keyword positions, AI-generated
  referral traffic, Cloudflare bot data, SEO performance, or any analytics and
  reporting metrics.
---

# GEO Analytics

Fetches the full dashboard overview for a project — search, traffic, AI impact,
and infrastructure data in a single call.

## Step 1: Locate your API key

**A)** `printenv GEO_API_KEY` → returns a value → proceed.  
**B)** `grep '^GEO_API_KEY=' .env 2>/dev/null` → found → `export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)`  
**C)** Not found → ask the user for a key from https://platform.adgine.ai, then `export GEO_API_KEY=geo_sk_live_xxx`

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as `$GEO_API_KEY` (the environment variable). Never hardcode the key value or use placeholder strings like `API_KEY=***` or `API_KEY=geo_sk_live_xxx` directly in a command — this will cause authentication failures.


## Step 2: Identify project ID

Run `python3 scripts/list_projects.py` from the **geo-projects** skill if the project ID is unknown.

## Fetch dashboard overview

```bash
python3 scripts/get_overview.py --project-id <id> [--period 30d] [--json]
```

**Period options:** `7d` · `14d` · `30d` (default) · `90d`

## What the overview contains

| Section | Source | Key metrics |
|---|---|---|
| `search` | Google Search Console | clicks, impressions, CTR, position, top queries |
| `traffic` | Google Analytics 4 | sessions, active users, top sources |
| `ai_impact` | GA4 + Cloudflare | AI referral sessions, AI crawler requests |
| `infrastructure` | Cloudflare | total requests, bandwidth, threat data |

Sections return `null` if the integration is not connected for that project.

## Tips

- Use `--period 7d` for recent trends, `--period 90d` for long-term patterns
- If a section is `null`, suggest the user connect that integration in the GEO dashboard
- For detailed API field reference, see [API.md](API.md)

## Output Format

> ⚠️ **CRITICAL — Table cell content rule (must follow exactly):**
> Use fenced code blocks with box-drawing border tables. They align perfectly — **only if every cell contains ASCII characters exclusively**.
> - **NEVER** put emoji (`✅` `❌` `📈` etc.) or non-ASCII text inside table cells. Emoji render as 2 display units but count as 1 character → all columns after them shift right permanently.
> - Emoji are allowed ONLY on the label line **immediately above** the opening ` ``` ` fence.
> - Status values in cells: `Connected` / `---` / `Pending` (NOT ✅/❌)
> - Change values in cells: `+1,200` / `-3,400` / `--` (NOT 📈/📉)
> - Box-drawing border chars (`┌─┬─┐ │ ├─┼─┤ └─┴─┘`) are fine — they are narrow 1-unit chars.

When presenting analytics results, follow this structure exactly.

### 1. Header

> 📊 **Analytics Overview** — `<start>` → `<end>` (`<period>`)
> Project: `<project-id>`

### 2. Integration status

📡 Integrations
```
┌────────────────────────┬─────────────┐
│ Service                │ Status      │
├────────────────────────┼─────────────┤
│ Google Search Console  │ Connected   │
│ Google Analytics 4     │ Connected   │
│ Cloudflare             │ ---         │
└────────────────────────┴─────────────┘
```

### 3. Search Performance (GSC) — if available

🔍 Search Performance (GSC)
```
┌──────────────────┬──────────┬──────────┐
│ Metric           │    Value │ vs Prev  │
├──────────────────┼──────────┼──────────┤
│ Clicks           │   12,345 │ +1,200   │
│ Impressions      │   98,765 │ -3,400   │
│ Avg CTR          │    12.5% │ --       │
│ Avg Position     │      8.2 │ +0.5     │
└──────────────────┴──────────┴──────────┘
```

🔝 Top Queries (max 5 rows, truncate query to ~30 chars with `…`)
```
┌────┬────────────────────────────────┬────────┬──────────┐
│  # │ Query                          │ Clicks │ Position │
├────┼────────────────────────────────┼────────┼──────────┤
│  1 │ best seo tool                  │  1,234 │      3.2 │
│  2 │ geo optimization               │    876 │      5.1 │
└────┴────────────────────────────────┴────────┴──────────┘
```

### 4. Traffic (GA4) — if available

📈 Traffic (GA4)
```
┌────────────────────────┬──────────┬─────────┐
│ Metric                 │    Value │ vs Prev │
├────────────────────────┼──────────┼─────────┤
│ Sessions               │    5,432 │ +320    │
│ Active Users           │    3,210 │ --      │
│ Pageviews              │    8,100 │ --      │
│ Bounce Rate            │    42.1% │ --      │
│ Avg Session Duration   │   2m 34s │ --      │
└────────────────────────┴──────────┴─────────┘
```

🌐 Top Sources (max 3 rows)
```
┌────────────────────┬──────────┬───────┐
│ Source / Medium    │ Sessions │ Share │
├────────────────────┼──────────┼───────┤
│ organic / google   │    2,100 │ 38.7% │
│ direct / none      │    1,200 │ 22.1% │
└────────────────────┴──────────┴───────┘
```

### 5. AI Impact — if available

🤖 AI Impact
```
┌────────────────────────┬────────┬─────────┐
│ Metric                 │  Value │ vs Prev │
├────────────────────────┼────────┼─────────┤
│ AI Referral Sessions   │     87 │ +12     │
│ AI Crawler Requests    │  4,320 │ --      │
└────────────────────────┴────────┴─────────┘
```

### 6. Infrastructure (Cloudflare) — if available

☁️ Infrastructure (Cloudflare)
```
┌──────────────────┬─────────┐
│ Metric           │   Value │
├──────────────────┼─────────┤
│ Total Requests   │ 120,000 │
│ Bandwidth        │  4.5 GB │
│ Threats Blocked  │      23 │
└──────────────────┴─────────┘
```

### Rules

- Status cells: `Connected` or `---` — **never** ✅/❌ inside cells
- Change cells: `+N` / `-N` / `--` — **never** 📈/📉 inside cells
- If a section is null/not connected: skip its table, show one line `🔌 **<Service>** — not connected. [Connect](https://platform.adgine.ai)`
- Keep total table width under ~60 chars (fits Telegram mobile without scroll)
- Each table in its own separate ` ``` ` fence
