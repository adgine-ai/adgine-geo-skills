---
name: adgine/geo-citation
description: Actively submits AI search prompts to live AI platforms (ChatGPT,
  Perplexity, Google AI Overviews, Gemini) and measures whether your brand/website
  appears in the real responses — citation rate, cited URLs, full AI reply text.
  Requires GEO_API_KEY and a platform project with configured prompts. Use when
  the user wants to run citation tests (运行引用测试 / 跑引用测试), check if AI
  platforms actually cite their brand (AI 有没有引用我 / 品牌被引用了吗), measure
  citation rates, review real AI platform responses, or see which URLs AI cited.
  NOT for website technical/structural GEO audits — use adgine-geo-site-audit.
  NOT for reading pre-aggregated visibility scores — use adgine-geo-visibility.
---

# GEO Citation Tests

## 触发条件

当用户说出以下意图时使用本 skill：
- “运行引用测试” / “跑引用测试” / “run citation test”
- “AI 有没有引用我” / “AI 搜索能找到我吗” / “ChatGPT 有没有提到我”
- “品牌被引用了吗” / “引用率多少” / “查看引用结果”
- “哪些 URL 被 AI 引用了” / “查看 AI 回复原文”

**⛔ 以下意图不属于本 skill：**
- “审计网站” / “GEO 评分” / “检测网站结构” → **adgine-geo-site-audit**
- “我的 Visibility Score” / “声量份额” / “可见性得分” → **adgine-geo-visibility**
- “创建提示词” / “管理主题” → **adgine-geo-topics**

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


## Project selection

```bash
export GEO_PROJECT_ID=<project-id>   # session shortcut — resets when terminal closes
# Run python3 scripts/list_projects.py from adgine-geo-projects skill to find your IDs
```

## What are citation tests?

A citation test submits an AI search prompt to multiple AI platforms (ChatGPT, Perplexity, Google AI Overviews, etc.) and checks whether your website or brand appears in the response — either as a cited source or in the generated text.

---

## Commands

### Run citation tests on prompts
```bash
python3 scripts/create_tests.py --prompt-ids <id1,id2,...> [--project-id <id>]
```
Creates citation tests for each prompt × platform combination. Results are processed asynchronously.

### Get results for a prompt
```bash
python3 scripts/get_results.py --prompt-id <id> [--project-id <id>] [--json]
```
Shows citation test results for a specific prompt, including:
- Platform
- Test status
- Whether your brand was cited
- Full AI response text
- List of URLs cited

### Get results with date filtering
```bash
python3 scripts/get_results.py --prompt-id <id> --start-date 2025-02-01 --end-date 2025-03-01 [--json]
```
When `--start-date` / `--end-date` are provided, uses the analytics endpoint to filter executions by date range. Useful for comparing citation performance across time periods.

### Get project-level citation aggregate
```bash
python3 scripts/get_aggregate.py [--start-date 2025-02-22] [--end-date 2025-03-14] [--platform chatgpt,perplexity] [--json]
```
Returns project-level citation metrics for a time window (auto-compared with previous equal-length period):
- **Citation Count**: total times your brand was cited
- **Citation Share**: your brand's citations as % of all brand citations
- **Citation Rank**: your brand's ranking among all brands by citation count
- **By Platform**: per-platform breakdown
- **Competitor Ranking**: all brands ranked by citations

### Get aggregated citation URLs
```bash
python3 scripts/get_results.py --aggregate [--project-id <id>] \
  --prompt-ids <id1,id2,...> [--json]
```
Shows all URLs that were cited across tests for a set of prompts.

---

## Workflow

1. Generate prompts: `adgine-geo-topics/scripts/generate_prompts.py --topic-id <id>`
2. Run tests: `python3 scripts/create_tests.py --prompt-ids <id1,id2,...>`
3. Wait ~5–15 minutes for AI platforms to respond
4. Review results: `python3 scripts/get_results.py --prompt-id <id>`
5. Analyze trends: `python3 scripts/get_aggregate.py --start-date <from> --end-date <to>`

### Period Comparison Workflow

To compare citation performance across two time periods (e.g., "early GEO" vs "recent"):
1. Run `python3 scripts/get_aggregate.py --start-date <early_start> --end-date <early_end> --json` for the early period
2. Run `python3 scripts/get_aggregate.py --start-date <recent_start> --end-date <recent_end> --json` for the recent period
3. Compare the `citation_count`, `citation_share`, and `citation_rank` values between the two responses

## Output Format

> ⚠️ **CRITICAL — Table cell content rule (must follow exactly):**
> Tables use fenced code blocks with box-drawing borders. They only align correctly when **every cell contains ASCII characters exclusively**.
> - **NEVER** put emoji inside table cells. They are 2 display units wide but count as 1 character, permanently misaligning all following columns.
> - Emoji go ONLY on the label line **above** the ` ``` ` fence.
> - Status values in cells: `Done` / `Pending` / `---`
> - Cited values in cells: `Yes` / `No` (NOT ✅/❌)
> - Use `[label](url)` for clickable URLs (outside fenced blocks).

---

### When submitting tests (`create_tests.py`)

> ✅ **Citation tests submitted** for **N** prompt(s).
> Results ready in ~5–15 min. Check with `get_results.py --prompt-id <id>`.

---

### When showing results for a prompt (`get_results.py`)

> 🔍 **Citation Results**
> Prompt: *"<prompt text>"*
> ID: `<prompt-id>`

🎯 Per-Platform Results
```
┌──────────────┬───────────┬───────┬────────────┐
│ Platform     │ Status    │ Cited │ URLs found │
├──────────────┼───────────┼───────┼────────────┤
│ ChatGPT      │ Done      │ Yes   │          2 │
│ Perplexity   │ Done      │ No    │          0 │
│ Google AIO   │ Pending   │ ---   │          - │
└──────────────┴───────────┴───────┴────────────┘
```

For each platform where Cited = `Yes`, list URLs as clickable links:

**ChatGPT** — cited URLs:
- [example.com/article-1](https://example.com/article-1)
- [example.com/about](https://example.com/about)

*Response excerpt: "<first 200 chars>…"*

> 📊 **Citation rate: 2 / 3 platforms (67%)** for this prompt.

---

### When showing aggregated URLs (`--aggregate`)

> 🔗 **Most Cited URLs** — across **N** prompts

🔝 Top URLs
```
┌────┬──────────────────────────────────────┬────────┐
│  # │ URL                                  │ Cited  │
├────┼──────────────────────────────────────┼────────┤
│  1 │ example.com/guide                    │     8x │
│  2 │ example.com/about                    │     5x │
│  3 │ example.com/pricing                  │     2x │
└────┴──────────────────────────────────────┴────────┘
```

Then list as clickable links below the table:
- [example.com/guide](https://example.com/guide) — 8×
- [example.com/about](https://example.com/about) — 5×

> 📊 **N unique URLs** cited across **M prompts**.

---

## Post-task recommendations

After reviewing citation results, suggest contextual next actions:

| What you saw | → use skill (agent-internal) |
|---|---|
| Citation tests completed | 查看可见性趋势和竞品对比 *(→ adgine-geo-visibility)*|
| Low citation rate (< 30%) | 生成针对性的 GEO 优化文章 *(→ adgine-geo-content)*|
| Low citation rate (< 30%) | 检查被引用页面的 AI 优化健康度 *(→ adgine-geo-performance)*|
| Specific URLs cited | 查看这些页面的 AI 爬虫访问明细 *(→ adgine-geo-aiagent)*|
| High citation rate | 扩大内容覆盖，生成更多 GEO 文章 *(→ adgine-geo-content)*|
| Aggregate results reviewed | 发布表现最好的内容到 WordPress *(→ adgine-geo-wordpress)*|

**⚠️ Output rule:** Do NOT write skill names (e.g. `adgine-geo-xxx`) in user-facing suggestions. Each suggestion must be phrased as a natural-language prompt the user can copy and send directly to the agent.

> 💡 **建议下一步：**
> 1. **[行动标题]** — *"[可直接发送给 AI 的自然语言提示词]"*
> 2. **[行动标题]** — *"[可直接发送给 AI 的自然语言提示词]"*
