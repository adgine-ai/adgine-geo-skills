---
name: adgine/geo-performance
description: Checks a specific page's AI-optimization health within a GEO project
  — crawlability status, AI optimization score, indexing issues, content health
  for mobile/desktop. Use when the user asks about a page's AI-readiness:
  page crawlability / AI indexing status / 页面 AI 优化健康度 / 某个页面是否对
  AI 搜索引擎友好 / content issues on a page / per-page AI health score.
  NOT for page traffic/visit logs or which bots visited a page — use
  adgine-geo-aiagent (page_detail) for that.
  NOT for whole-site GEO structural audit — use adgine-geo-site-audit for that.
---

# GEO Performance

Fetches the AI-agent page health report for a specific page path within a project.

## 触发条件

当用户说出以下意图时使用本 skill：
- “某个页面的 AI 优化健康度” / “页面健康检查” / “page health”
- “页面可爬取性” / “是否被 AI 索引” / “crawlability”
- “分析 /pricing 页面” / “检查某个页面对 AI 搜索引擎是否友好”

**⛔ 以下意图不属于本 skill：**
- “某个页面被哪些 AI 爬虫访问过” / “页面爬虫日志” → **adgine-geo-aiagent**
- “审计整个网站” / “GEO 评分” → **adgine-geo-site-audit**

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


## Analyze a page

```bash
python3 scripts/analyze_page.py --path /blog/my-article [--project-id <id>] [--strategy mobile] [--json]
```

**`--path`**: URL path to analyze (required). Can be a bare path (`/pricing`) or a full URL (`https://example.com/pricing` — the domain is ignored).

**Strategy options:**
- `mobile` — mobile device health check (default)
- `desktop` — desktop device health check

**Force a fresh analysis:**
```bash
python3 scripts/analyze_page.py --path /pricing --refresh [--strategy desktop]
```
Without `--refresh`, returns the cached report. With `--refresh`, triggers a new health check and waits for the result.

## Score interpretation

| Score | Rating |
|---|---|
| 90–100 | ✅ Good |
| 50–89 | ⚠️ Needs improvement |
| 0–49 | ❌ Poor |

## Key checks in the output

- **Crawlability**: Whether AI crawlers can access the page (robots.txt, noindex, auth walls)
- **AI Optimization**: Schema markup, structured data, content clarity for AI parsing
- **Indexing Status**: Whether the page is indexed and when it was last crawled
- **Content Health**: Issues with content quality, length, or structure affecting AI visibility

## Output Format

> ⚠️ **CRITICAL — Table cell content rule (must follow exactly):**
> Tables use fenced code blocks with box-drawing borders. They only align correctly when **every cell contains ASCII characters exclusively**.
> - **NEVER** put emoji inside table cells. They are 2 display units wide but count as 1 character, permanently misaligning all following columns.
> - Emoji go ONLY on the label line **above** the ` ``` ` fence.
> - Status in cells: `Pass` / `Fail` / `Warn` (NOT ✅/❌/⚠️)
> - Priority in cells: `High` / `Medium` / `Low` (NOT 🔴/🟡/🟢)

---

### 1. Header

> 🔬 **Page Health** — `<path>` *(<strategy>)*
> Analyzed: `<timestamp>`

### 2. Score card

🎯 Overall Score
```
┌──────────────────────────────────────────────────┐
│  <N> / 100   <rating text>                       │
│                                                  │
│  ████████████████░░░░  <N>%                      │
└──────────────────────────────────────────────────┘
```
Score bar: 20 chars total — `<N>/100 * 20` filled with `█`, rest with `░`.
Rating text in cell (ASCII only): `Good` / `Needs Improvement` / `Poor`

### 3. Health checks

🩺 Health Checks
```
┌──────────────┬──────────────────┬────────┐
│ Category     │ Check            │ Status │
├──────────────┼──────────────────┼────────┤
│ Crawlability │ Robots.txt       │ Pass   │
│ Crawlability │ Noindex          │ Pass   │
│ Crawlability │ Auth wall        │ Fail   │
│ AI Optimize  │ Schema markup    │ Pass   │
│ AI Optimize  │ FAQ schema       │ Warn   │
│ Indexing     │ Indexed          │ Pass   │
│ Content      │ Word count       │ Warn   │
│ Content      │ Duplicate titles │ Pass   │
└──────────────┴──────────────────┴────────┘
```

For each `Fail` or `Warn` row, add a note line below the table:
- Auth wall — Fail: AI crawlers are blocked
- FAQ schema — Warn: add for AI snippet eligibility
- Word count — Warn: 450 words, recommend 800+

### 4. Recommended actions (only if any Fail or Warn exist)

💡 Top Actions
```
┌──────────┬────────────────────────────────────────────┐
│ Priority │ Action                                     │
├──────────┼────────────────────────────────────────────┤
│ High     │ Remove auth wall or add AI crawler rule    │
│ Medium   │ Expand content to 800+ words               │
│ Medium   │ Add FAQ schema markup                      │
└──────────┴────────────────────────────────────────────┘
```
Priority assignment: `Fail` → `High` · crawlability/indexing `Warn` → `High` · other `Warn` → `Medium`

If all checks pass: > 🎉 **All checks pass.** No action needed.

---

## Post-task recommendations

After page health analysis, suggest appropriate follow-up actions:

| What you saw | → use skill (agent-internal) |
|---|---|
| Crawlability issues (Fail) | 检查 robots.txt / 部署 Cloudflare Worker 追踪 AI 爬虫 *(→ adgine-geo-integrations)*|
| Content health warnings | 生成或更新该页面的 GEO 优化内容 *(→ adgine-geo-content)*|
| AI optimization gaps | 对整个网站做全面 GEO 技术审计 *(→ adgine-geo-site-audit)*|
| Specific page analyzed | 查看该页面的 AI 爬虫访问日志 *(→ adgine-geo-aiagent)*|
| All checks pass | 检查该页面在 AI 平台的实际引用表现 *(→ adgine-geo-visibility)*|

**⚠️ Output rule:** Do NOT write skill names (e.g. `adgine-geo-xxx`) in user-facing suggestions. Each suggestion must be phrased as a natural-language prompt the user can copy and send directly to the agent.

> 💡 **建议下一步：**
> 1. **[行动标题]** — *"[可直接发送给 AI 的自然语言提示词]"*
> 2. **[行动标题]** — *"[可直接发送给 AI 的自然语言提示词]"*
