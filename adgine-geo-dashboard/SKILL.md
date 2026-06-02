---
name: adgine/geo-dashboard
description: Fetches the top-level project dashboard snapshot — aggregate counts
  (prompts, topics, tests, citations, articles, AI referrals), a lightweight
  7-day visibility trend, and integration connection status (GA4/Cloudflare).
  Use when the user asks for a quick project overview (项目总览 / Dashboard
  概览 / 首页指标 / at-a-glance / 近七天趋势 / 集成状态).
  NOT for deep visibility analytics (Score/SoV/matrix/competitor drill-down) —
  use adgine-geo-visibility. NOT for traffic data — use adgine-geo-analytics.
---

# GEO Dashboard

Project-level snapshot skill: aggregate metrics, lightweight visibility trend,
and third-party integration status. Use this for the "what's the state of my
project right now" question.

For deep visibility analytics (matrix, share-of-voice, topic/prompt drill-down)
use the **adgine-geo-visibility** skill instead.

## 触发条件

当用户说出以下意图时使用本 skill：
- “项目总览” / “Dashboard” / “首页” / “项目概况”
- “近七天趋势” / “7-day trend”
- “集成状态” / “GA4 连接了吗” / “Cloudflare 接入了吗”

**⛔ 以下意图不属于本 skill：**
- “我的 Visibility Score 多少” / “声量份额” / “竞品对比” → **adgine-geo-visibility**
- “流量数据” / “访客来源” → **adgine-geo-analytics**
- “连接 GA4” / “同步数据” → **adgine-geo-integrations**

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
