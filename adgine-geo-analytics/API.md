# GEO Analytics API Reference

## Endpoint

```
GET /api/public/projects/{project_id}/dashboard/overview
```

### Query parameters

| Param | Values | Default | Description |
|---|---|---|---|
| `period` | `7d` `14d` `30d` `90d` | `30d` | Analysis time window |

### Response envelope

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "period": "30d",
    "date_range":    { "start": "2026-03-19", "end": "2026-04-18" },
    "compare_range": { "start": "2026-02-17", "end": "2026-03-18" },
    "integrations":  { "gsc": true, "ga4": true, "cloudflare": false },
    "search":        { ... },
    "traffic":       { ... },
    "ai_impact":     { ... },
    "infrastructure":{ ... }
  }
}
```

Sections that are `null` → integration not connected.

---

## Section: `search` (Google Search Console)

| Field | Type | Description |
|---|---|---|
| `clicks` | int | Total organic clicks |
| `impressions` | int | Total impressions |
| `avg_ctr` | float | Average click-through rate |
| `avg_position` | float | Average ranking position |
| `clicks_trend` | array | Daily clicks `[{ date, clicks }]` |
| `top_queries` | array | Top 5 search queries `[{ query, clicks, impressions, ctr, position }]` |
| `prev_clicks` | int | Previous period clicks (for comparison) |
| `prev_impressions` | int | Previous period impressions |

---

## Section: `traffic` (Google Analytics 4)

| Field | Type | Description |
|---|---|---|
| `sessions` | int | Total sessions |
| `active_users` | int | Active users |
| `sessions_trend` | array | Daily sessions |
| `top_sources` | array | Top traffic sources |
| `prev_sessions` | int | Previous period sessions |
| `prev_active_users` | int | Previous period active users |

---

## Section: `ai_impact`

| Field | Type | Description |
|---|---|---|
| `ai_referral_sessions` | int | Sessions from AI platforms (ChatGPT, Perplexity, etc.) |
| `ai_crawler_requests` | int | Requests from AI crawlers via Cloudflare |
| `ai_referral_trend` | array | Daily AI referral sessions |
| `ai_crawler_trend` | array | Daily AI crawler requests |
| `top_ai_sources` | array | Top AI referral sources |
| `top_ai_bots` | array | Top AI crawlers |

**Tracked AI sources**: chat.openai.com, chatgpt.com, perplexity.ai, claude.ai,
copilot.microsoft.com, gemini.google.com, you.com, phind.com, poe.com

---

## Section: `infrastructure` (Cloudflare)

| Field | Type | Description |
|---|---|---|
| `total_requests` | int | Total HTTP requests |
| `bandwidth_bytes` | int | Bandwidth consumed |
| `threats_blocked` | int | Blocked threats |
| `requests_trend` | array | Daily request counts |
