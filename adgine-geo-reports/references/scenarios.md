# Scenario catalog and intent routing

## Contents

- Fast routing
- P1 core GEO reports
- P2 acquisition, bots, pages, and flows
- P3 operations and inventory
- Entity and date arguments

## Fast routing

The call counts below describe business data calls. A project-scoped report also loads
`GET /api/projects/{id}` for the user-facing project name unless `--project-name` is supplied.

| User intent | Scenario | Typical call count |
|---|---|---:|
| Overall GEO status | `executive-overview` | 1 aggregate (+ capability on cold cache) |
| “Topic/Prompt list” | `catalog` | 2 paginated |
| Visibility over a period | `visibility` | 1 |
| Topic portfolio | `topics` | 1 |
| One Topic | `topic-detail` | 1 aggregate (+ capability on cold cache) |
| One Prompt with ID | `prompt-performance` | 1 aggregate (+ capability on cold cache) |
| One Prompt by text | `prompt-performance` | 1 aggregate (+ capability on cold cache) |
| AI citation / sentiment | `citations` / `sentiment` | 1 |
| GA4 / Cloudflare | matching P2 scenario | 1 |
| Bot/human multiview | `ai-bots` / `ai-humans` | 3 concurrent |
| Cross-source traffic | `traffic-overview` | 1 aggregate (+ capability on cold cache) |
| One page | `page-detail` | 1 aggregate (+ capability on cold cache) |
| Page recommendations | `page-opportunities` | 1 aggregate (+ capability on cold cache) |
| Content operations | `content-pipeline` | 1 aggregate (+ capability on cold cache) |
| Freshness / operations | `data-freshness` / `operations-overview` | 1 aggregate (+ capability on cold cache) |
| My account/profile/name/phone/email | `account-info` | 1 |
| Project list / my projects | `projects` (inline) | 1 |

## P1 core GEO reports

| Scenario | Primary question | Required arguments |
|---|---|---|
| `executive-overview` | How is GEO performing across visibility, traffic coverage, opportunities, and integrations? | Project |
| `catalog` | What Topics and Prompts exist? | Project |
| `visibility` | What are visibility, SoV, position, recommendation rates, and trends? | Project/window |
| `matrix` | How does our brand compare by AI platform? | Project/window; optional `--metric` |
| `topics` | Which Topics perform best/worst? | Project/window |
| `topic-detail` | How do Prompts inside one Topic perform? | `--topic` |
| `topic-lifecycle` | How do early vs later Prompts compare? | `--topic` |
| `prompt-performance` | How does one Prompt perform by period/platform? | Prompt selector |
| `prompt-executions` | What completed model executions exist for one Prompt? | Prompt selector |
| `citations` | How often and where is the brand cited? | Project/window |
| `sentiment` | What sentiment distribution/trend appears in brand mentions? | Project/window |

`topic-lifecycle` divides Prompts into deterministic halves ordered by `created_at ASC`; it is descriptive, not causal.

## P2 acquisition, bots, pages, and flows

| Scenario | Scope | Notes |
|---|---|---|
| `ga4-overview` | All-site GA4 traffic and channels | GA4 units only. |
| `ga4-referrals` | AI referral sessions/users by source | Do not equate sessions with Worker events. |
| `ga4-pages` | Top GA4 pages | Uses `offset` + `limit`. |
| `cloudflare-overview` | Requests, bandwidth, threats, page views, visitors | Cloudflare Analytics units. |
| `cloudflare-bots` | Bot category/name traffic | Uses local Cloudflare data. |
| `cloudflare-pages` | Bot requests by page | Uses `offset` + `limit`. |
| `worker-traffic` | Worker-captured AI event mix | Event/request units. |
| `worker-pages` | Worker events by page | Uses `offset` + `limit`. |
| `worker-events` | Read-only raw Worker event inventory | Uses `page` + `limit`. |
| `worker-deployment` | Worker deployment and routes | Status only; never deploys or removes a Worker. |
| `ai-overview` | Site AI KPI facade | Keep source units visible. |
| `traffic-overview` | GA4 + Cloudflare API + Worker + derived AI KPI | Sections remain source-separated; no grand total. |
| `ai-bots` | KPI + platform + User-Agent | Three concurrent reads. |
| `ai-humans` | KPI + platform + page | Three concurrent reads. |
| `ai-pages` | Five-dimension page table | One aggregate call. |
| `ai-flow` | AI platform → page | Flow links rendered as bars/table. |
| `human-flow` | AI platform → page for real people | Worker-derived flow. |
| `ga4-flow` | GA4 AI source → landing page | GA4 sessions. |
| `page-detail` | KPI, platforms, related pages, cached health | Requires `--path`. |
| `page-health` | Cached PageSpeed report | Never refreshes automatically. |
| `page-opportunities` | Cached health + page KPI | Backend opportunities stay empty until `target_path/path_key` exists; deterministic recommendations remain available. |

## P3 operations and inventory

| Scenario | Scope | Required arguments |
|---|---|---|
| `account-info` | Current account creation time, name, phone, and email | Account only |
| `data-freshness` | Source status, latest date/write time, lag threshold | Project |
| `operations-overview` | Sanitized integrations, jobs, publishing, opportunities, freshness | Project |
| `opportunities` | Latest optimization opportunity batch | Project |
| `opportunity-detail` | One opportunity | `--resource-id` |
| `content-pipeline` | Content library and jobs | Project |
| `content-detail` | One content item | `--resource-id` |
| `brand-profile` | Current brand profile | Project |
| `brand-jobs` | Brand generation job status | Project |
| `integration-health` | Connected services | Project |
| `wordpress-publications` | Publish history | Project |
| `wordpress-publishable` | Publish-ready content | Project |
| `billing` | Subscription, credits, and plans | Account only |
| `projects` | Project catalog; inline by default, never auto-generates HTML | Account only |
| `domains` | Registered domain portfolio | Account only |
| `saas-task` | One deployment task | `--resource-id` |

Report scenarios are read-only. Use specialist Skills for create/update/delete, connection, sync, refresh, retry, publish, or deployment actions.

## Entity and date arguments

Prompt selector priority:

1. `--prompt-id <uuid>`
2. `--prompt <uuid>`
3. `--topic <id-or-name> --prompt <exact-or-unique-text>`
4. `--topic <id-or-name> --prompt-index <1-based-index>`
5. `--prompt <exact-or-unique-project-wide-text>`

Page reports accept a path or a same-project full URL. Query/fragment are ignored, duplicate slashes collapse, non-root trailing slash is removed, case is preserved, and percent encoding is not decoded.

Use `--period 7d|14d|30d|90d` or explicit `--start/--end`. The script expands periods into inclusive natural-day ranges and defaults the end to yesterday.

Paginated scenarios default to `--page 1 --limit 40`. For the next page, keep `--limit 40` and increment `--page`; offset-based endpoints use `(page - 1) * 40` internally.
