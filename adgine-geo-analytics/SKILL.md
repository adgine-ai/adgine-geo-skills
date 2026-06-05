---
name: adgine/geo-analytics
description: High-level traffic analytics overview for a GEO project — GA4 sessions,
  active users, source breakdown, and aggregated AI-referral traffic in a single
  call. Use when the user wants a broad traffic/analytics summary (流量概览,
  analytics overview, traffic summary, AI 引荐汇总). NOT for deep per-bot crawl
  breakdowns or per-page traffic logs — use adgine-geo-aiagent for those. NOT for
  connecting/syncing GA4 or Cloudflare — use adgine-geo-integrations for that.
---

# GEO Analytics

Fetches the full dashboard overview for a project — search, traffic, AI impact,
and infrastructure data in a single call.

## 触发条件

当用户说出以下意图时使用本 skill：
- “流量概览” / “流量汇总” / “traffic overview” / “analytics summary”
- “GA4 数据” / “访客数” / “会话数” / “sessions”
- “AI 引荐流量汇总” / “AI referral traffic”

**⛔ 以下意图不属于本 skill：**
- “哪些 AI bot 爬了我的网站” / “GPTBot 访问日志” / “某个页面的 AI 爬虫明细” → **adgine-geo-aiagent**
- “连接 GA4” / “同步数据” / “部署 Worker” → **adgine-geo-integrations**
- “项目总览” / “Dashboard” → **adgine-geo-dashboard**

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

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as `$GEO_API_KEY` (the environment variable). Never hardcode the key value or use placeholder strings like `API_KEY=***` or `API_KEY=geo_sk_live_xxx` directly in a command — this will cause authentication failures.


## Step 2: Identify project ID

Run `python3 scripts/list_projects.py` from the **adgine-geo-projects** skill if the project ID is unknown.

## Fetch dashboard overview

```bash
python3 scripts/get_overview.py --project-id <id> [--period 30d] [--json]
```

**Period options:** `7d` · `14d` · `30d` (default) · `90d`

## What the overview contains

| Section | Source | Key metrics |
|---|---|---|
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

### 2. Integration status

📡 Integrations
```
┌────────────────────────┬─────────────┐
│ Service                │ Status      │
├────────────────────────┼─────────────┤
│ Google Analytics 4     │ Connected   │
│ Cloudflare             │ ---         │
└────────────────────────┴─────────────┘
```

### 3. Traffic (GA4) — if available

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

### 4. AI Impact — if available

🤖 AI Impact
```
┌────────────────────────┬────────┬─────────┐
│ Metric                 │  Value │ vs Prev │
├────────────────────────┼────────┼─────────┤
│ AI Referral Sessions   │     87 │ +12     │
│ AI Crawler Requests    │  4,320 │ --      │
└────────────────────────┴────────┴─────────┘
```

### 5. Infrastructure (Cloudflare) — if available

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

---

## Post-task recommendations

After reviewing analytics, suggest deeper or follow-up actions:

| What you saw | Suggest |
|---|---|
| Traffic overview | `adgine-geo-aiagent` — 深入分析 AI 爬虫和 AI 引荐流量明细 |
| GA4 data present | `adgine-geo-aiagent` — 查看 AI 驱动的真人访问来源 |
| Cloudflare data present | `adgine-geo-aiagent` — 查看各 AI 平台的爬虫行为 |
| AI referral sessions growing | `adgine-geo-citation` — 运行引用测试，量化 AI 可见性 |
| Integration missing (null sections) | `adgine-geo-integrations` — 连接 GA4 或 Cloudflare 获取完整数据 |
| Low traffic overall | `adgine-geo-content` — 生成更多 GEO 优化内容吸引 AI 引荐流量 |

> 💡 **建议下一步：**
> 1. **[action]** → `skill-name`
> 2. **[action]** → `skill-name`
