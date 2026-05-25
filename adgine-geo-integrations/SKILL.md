---
name: adgine/geo-integrations
description: Manages Google Analytics 4 (GA4) and Cloudflare data integrations for a GEO project — OAuth setup, property/zone selection, scheduled data syncs, traffic overviews, page rankings, channel/source breakdown, AI-referral detail, and Cloudflare Worker deployment for AI crawler tracking. Use when the user wants to connect GA4 (连接 GA4, bind GA4, GA4 OAuth, Google Analytics 集成), connect Cloudflare (连接 Cloudflare, bind CF API token, 接入 CF), sync analytics data (同步 GA4 / 同步 Cloudflare), query traffic overview / pages / sources (流量概览, 来源, top pages), inspect AI-referral analytics (AI 引荐, AI referral traffic), or deploy/check/remove the Cloudflare Worker (部署 Worker, AI 爬虫追踪 Worker, Worker 部署状态). For the WordPress integration, use adgine-geo-wordpress.
---

# GEO Integrations

Unified skill for the two analytics integrations (GA4 + Cloudflare). Four
scripts cover OAuth setup, data sync, traffic queries, and Cloudflare Worker
management for AI traffic tracking.

> WordPress integration lives in the separate **adgine-geo-wordpress** skill
> (publishing-focused, very different workflow).

## Step 1: Locate your API key

**A)** `printenv GEO_API_KEY` → returns a value → proceed.
**B)** `grep '^GEO_API_KEY=' .env 2>/dev/null` → found → `export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)`
**C)** Not found → ask the user for a key from the GEO platform.

## Project selection

```bash
export GEO_PROJECT_ID=<project-id>
```

## Scripts

### GA4 setup (OAuth + property selection)

```bash
python3 scripts/ga4_setup.py auth-url                       # show OAuth URL
python3 scripts/ga4_setup.py connect --code <auth_code>     # manual code exchange (debug)
python3 scripts/ga4_setup.py properties                     # list available GA4 properties
python3 scripts/ga4_setup.py select --property-id <id>      # bind property (triggers 7-day backfill)
```

### GA4 data (sync + queries)

```bash
python3 scripts/ga4_data.py sync                                  # pull latest data into local DB
python3 scripts/ga4_data.py overview     [--start ...] [--end ...]   # sessions/users/pageviews
python3 scripts/ga4_data.py ai-referrals [--start ...] [--end ...]   # AI platform breakdown
python3 scripts/ga4_data.py pages        [--page 1] [--limit 20]     # top pages
python3 scripts/ga4_data.py sources      [--start ...] [--end ...]   # channel split
```

### Cloudflare connection (token + zones + sync)

```bash
python3 scripts/cloudflare_connect.py list-zones --token <api_token>   # zones the token can access
python3 scripts/cloudflare_connect.py connect    --token <api_token>   # bind (auto-matches zone)
python3 scripts/cloudflare_connect.py sync                             # pull latest CF data
python3 scripts/cloudflare_connect.py overview [--start ...] [--end ...]
```

### Cloudflare Worker (AI traffic tracking)

```bash
python3 scripts/cloudflare_worker.py config                      # get Worker JS code + keys
python3 scripts/cloudflare_worker.py deploy [--zone-id <id>]     # one-click deploy
python3 scripts/cloudflare_worker.py deploy-status               # is Worker deployed?
python3 scripts/cloudflare_worker.py overview [--start ...] [--end ...]
python3 scripts/cloudflare_worker.py pages   [--page 1] [--limit 20]
python3 scripts/cloudflare_worker.py undeploy [--keep-script] --yes   # DESTRUCTIVE
```

> The Cloudflare API token must include **Workers** permissions for deploy /
> undeploy / Worker analytics. Without it, `deploy-status` returns `deployed=false`
> (it does not throw).

## Output Format

ASCII tables only inside fenced code blocks. Status vocabulary:
`Connected` / `Disconnected` / `Pending` / `Yes` / `No`.

## Workflow narrative

### GA4 first-time setup
1. `ga4_setup.py auth-url` → user opens the URL → Google asks for permission.
2. After Google callback the GEO platform stores tokens automatically.
3. `ga4_setup.py properties` → list options.
4. `ga4_setup.py select --property-id <id>` → bind property.
5. Backfill runs automatically; check progress with `ga4_data.py overview`.

### Cloudflare first-time setup
1. User creates a Cloudflare API token (with Zone:Read + Analytics:Read +
   optionally Workers:Edit).
2. `cloudflare_connect.py list-zones --token <t>` to verify access.
3. `cloudflare_connect.py connect --token <t>` to bind.
4. `cloudflare_connect.py sync` to pull initial data.

### Cloudflare Worker (optional, for AI tracking)
1. `cloudflare_worker.py config` → grab Worker JS + receiver URL.
2. `cloudflare_worker.py deploy` → one-click deploy.
3. `cloudflare_worker.py deploy-status` → verify route is live.
4. After traffic accrues: `cloudflare_worker.py overview` / `pages`.

## Related endpoints

| Method | Path |
|---|---|
| GET    | `/api/projects/{id}/integrations/ga4/auth-url` |
| POST   | `/api/projects/{id}/integrations/ga4/connect` |
| GET    | `/api/projects/{id}/integrations/ga4/properties` |
| POST   | `/api/projects/{id}/integrations/ga4/select-property` |
| POST   | `/api/projects/{id}/integrations/ga4/sync` |
| GET    | `/api/projects/{id}/integrations/ga4/overview` |
| GET    | `/api/projects/{id}/integrations/ga4/ai-referrals` |
| GET    | `/api/projects/{id}/integrations/ga4/pages` |
| GET    | `/api/projects/{id}/integrations/ga4/sources` |
| POST   | `/api/projects/{id}/integrations/cloudflare/list-zones` |
| POST   | `/api/projects/{id}/integrations/cloudflare/connect` |
| POST   | `/api/projects/{id}/integrations/cloudflare/sync` |
| GET    | `/api/projects/{id}/integrations/cloudflare/overview` |
| GET    | `/api/projects/{id}/integrations/cloudflare/worker-config` |
| POST   | `/api/projects/{id}/integrations/cloudflare/worker/deploy` |
| DELETE | `/api/projects/{id}/integrations/cloudflare/worker/deploy` |
| GET    | `/api/projects/{id}/integrations/cloudflare/worker/deploy-status` |
| GET    | `/api/projects/{id}/integrations/cloudflare/worker/overview` |
| GET    | `/api/projects/{id}/integrations/cloudflare/worker/pages` |
