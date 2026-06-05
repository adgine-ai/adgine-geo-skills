---
name: adgine/geo-content
description: Generates AI-optimized article outlines and full articles for GEO content strategy, manages the content library, and inspects/retries the underlying outline and article generation jobs. Supports generating title suggestions, producing a keyword-optimized outline (async), writing a complete article from an approved outline (async), listing/editing/deleting content items, and managing the workflow / outline / article job lists with detail inspection and retry. Use when the user wants to create an article (写文章 / generate article), generate an outline (生成大纲 / outline), write GEO-optimized content, check content status, review generated articles, manage their content pipeline, check job progress (任务进度 / job status), or retry a failed content job (重试失败任务 / retry job). Intent synonyms: article generation, outline generation, content jobs, content workflow, retry failed job, 内容生成任务.
---

# GEO Content

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

## Content lifecycle

```
Prompts selected → generate-titles → generate-outline (async) → approve outline → generate-article (async) → article ready
```

Content items progress through statuses: `draft` → `outline` → `article`

---

## Commands

### List content items
```bash
python3 scripts/list_content.py [--project-id <id>] [--status draft|outline|article] \
  [--topic-id <id>] [--page 1] [--limit 20] [--json]
```

### Suggest article titles (quick, sync)
```bash
python3 scripts/generate_titles.py --topic-id <tid> --prompt-ids <id1,id2,...> \
  [--project-id <id>]
```
Returns 5–10 AI-suggested article titles for the given topic and prompts.

### Generate article outline (async, ~10–15 min)
```bash
python3 scripts/generate_outline.py --topic-id <tid> --prompt-ids <id1,id2,...> \
  [--project-id <id>] [--title "Your chosen title"] \
  [--reference-urls "https://url1,https://url2"] \
  [--instructions "Additional guidance for the AI"]
```
Creates a content item with status `outline` once complete.

> ⏳ **Expected duration: 10–15 minutes.** The script polls automatically (interval 10 s, timeout 20 min). Do NOT cancel early — this is a large LLM job.

### Generate full article from outline (async, ~5–10 min)
```bash
python3 scripts/generate_article.py --content-id <cid> [--project-id <id>]
```
Content item must have status `outline`. Produces the full article.

> ⏳ **Expected duration: 5–10 minutes.** The script polls automatically (interval 10 s, timeout 15 min). Do NOT cancel early.

### Inspect & retry generation jobs

The content pipeline runs three job types: the combined **workflow** job, the
**outline** job, and the **article** job. They each have their own list/detail
endpoints. Use `manage_jobs.py` to inspect or retry them.

List jobs:
```bash
python3 scripts/manage_jobs.py list-workflow [--page 1] [--limit 20] [--json]
python3 scripts/manage_jobs.py list-outline  [--page 1] [--limit 20] [--json]
python3 scripts/manage_jobs.py list-article  [--page 1] [--limit 20] [--json]
```

Get job detail:
```bash
python3 scripts/manage_jobs.py get-workflow --job-id <id>
python3 scripts/manage_jobs.py get-outline  --job-id <id>
python3 scripts/manage_jobs.py get-article  --job-id <id>
```

Retry a failed workflow job:
```bash
python3 scripts/manage_jobs.py retry --job-id <id>
```

## Workflow

See `WORKFLOW.md` for the detailed step-by-step content creation flow.

## Output Format

> ⚠️ **CRITICAL — Table cell content rule (must follow exactly):**
> Tables use fenced code blocks with box-drawing borders. They only align correctly when **every cell contains ASCII characters exclusively**.
> - **NEVER** put emoji inside table cells. They are 2 display units wide but count as 1 character, permanently misaligning all following columns.
> - Emoji go ONLY on the label line **above** the ` ``` ` fence.
> - Status in cells: `Draft` / `Outline` / `Article` (NOT 📝/📋/✅)

---

### When listing content (`list_content.py`)

> 📄 **Content Library** — (Page 1 / N)

📚 Items
```
┌────┬─────────┬───────────────────────────────┐
│  # │ Status  │ Title                                │
├────┼─────────┼───────────────────────────────┤
│  1 │ Draft   │ How to Improve Your SEO in 2025      │
│  2 │ Outline │ Top 10 GEO Strategies for SaaS       │
│  3 │ Article │ What is Generative Engine Optimi...  │
└────┴─────────┴───────────────────────────────┘
```
Truncate long titles to ~36 chars with `...`.

---

### When suggesting titles (`generate_titles.py`)

> 💡 **Suggested Titles** — pick one to generate an outline:

💡 Title Options
```
┌────┬──────────────────────────────────────────────────────┐
│  # │ Title                                                │
├────┼──────────────────────────────────────────────────────┤
│  1 │ How to Dominate AI Search in 2025                    │
│  2 │ The Complete Guide to GEO for SaaS Companies         │
│  3 │ Why Traditional SEO Is Not Enough Anymore            │
└────┴──────────────────────────────────────────────────────┘
```
*Which title would you like to use for the outline?*

---

### When generating an outline (`generate_outline.py`)

- Progress: `⏳ **Generating outline…** (~10–15 min)`
- On completion, show the outline as a nested numbered list, then:

✅ Outline Ready
```
┌────────────┬────────────────────────────────────┐
│ Content ID │ <id>                               │
│ Sections   │ 6                                  │
│ Next step  │ generate_article.py -c <id>        │
└────────────┴────────────────────────────────────┘
```

---

### When generating an article (`generate_article.py`)

- Progress: `⏳ **Writing article…** (~5–10 min)`
- On completion:

✅ Article Complete
```
┌────────────┬────────────────────────────────────┐
│ Title      │ <title>                            │
│ Content ID │ <id>                               │
│ Word Count │ ~1,200                             │
│ Status     │ Article                            │
└────────────┴────────────────────────────────────┘
```

Then the **full article text** with `##`/`###` headings and bullet lists — never wrap article body in a code fence.

---

## Post-task recommendations

After content operations, guide the user to the next stage:

| You just… | Suggest next |
|---|---|
| Generated an outline | Review outline, then `adgine-geo-content` — 生成完整文章 |
| Generated a full article | `adgine-geo-wordpress` — 发布文章到 WordPress |
| Listed content items | `adgine-geo-content` — 选择一篇生成 outline 或 article |
| Checked job status / retried | `adgine-geo-content` — 继续管理内容管线 |
| Article published-ready | `adgine-geo-performance` — 检查文章页面的 AI 优化健康度 |
| Multiple articles ready | `adgine-geo-citation` — 对文章主题运行引用测试，验证效果 |

> 💡 **建议下一步：**
> 1. **[action]** → `skill-name`
> 2. **[action]** → `skill-name`
