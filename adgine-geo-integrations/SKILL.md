---
name: adgine/geo-integrations
description: Connects, configures, and syncs GA4 and Cloudflare data sources for a
  GEO project — OAuth setup, property/zone selection, data sync triggers, and
  Cloudflare Worker deployment for AI crawler tracking. Also queries the
  integration-specific traffic data (GA4 sessions/sources, CF bot events). Use
  when the user wants to connect GA4 (连接 GA4 / bind GA4 / GA4 OAuth / Google
  Analytics 集成), connect Cloudflare (连接 Cloudflare / bind CF API token /
  接入 CF), sync data (同步 GA4 / 同步 Cloudflare / 拉取数据), or deploy
  the Cloudflare Worker (部署 Worker / Worker 部署状态).
  NOT for high-level project traffic summary (no GA4/CF context) — use
  adgine-geo-analytics. NOT for per-bot crawl drill-downs — use
  adgine-geo-aiagent. For WordPress — use adgine-geo-wordpress.
---

# GEO Integrations

Unified skill for the two analytics integrations (GA4 + Cloudflare). Four
scripts cover OAuth setup, data sync, traffic queries, and Cloudflare Worker
management for AI traffic tracking.

> WordPress integration lives in the separate **adgine-geo-wordpress** skill
> (publishing-focused, very different workflow).

## 触发条件

当用户说出以下意图时使用本 skill：
- 连接/绑定/接入 GA4 或 Cloudflare
- GA4 OAuth 授权 / 选择 GA4 媒体资源 / 选择 Cloudflare Zone
- 同步数据 / 拉取数据 / 手动同步
- 查询 GA4 流量来源 / 查询 Cloudflare bot 事件
- 部署/检查/删除 Cloudflare Worker

**⛔ 以下意图不属于本 skill：**
- “流量概览” / “项目流量汇总”（不涉及连接/同步操作）→ **adgine-geo-analytics**
- “哪些 AI bot 爬了我的网站” / “GPTBot 访问明细” → **adgine-geo-aiagent**
- “发布到 WordPress” → **adgine-geo-wordpress**

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
