---
name: adgine/geo-content
description: Generates AI-optimized article outlines and full articles for GEO content strategy, manages the content library, and inspects/retries the underlying outline and article generation jobs. Supports generating title suggestions, producing a keyword-optimized outline (async), writing a complete article from an approved outline (async), listing/editing/deleting content items, and managing the workflow / outline / article job lists with detail inspection and retry. Use when the user wants to create an article (写文章 / generate article), generate an outline (生成大纲 / outline), write GEO-optimized content, check content status, review generated articles, manage their content pipeline, check job progress (任务进度 / job status), or retry a failed content job (重试失败任务 / retry job). Intent synonyms: article generation, outline generation, content jobs, content workflow, retry failed job, 内容生成任务.
---

# GEO Content

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

### Generate article outline (async, ~30–90 s)
```bash
python3 scripts/generate_outline.py --topic-id <tid> --prompt-ids <id1,id2,...> \
  [--project-id <id>] [--title "Your chosen title"] \
  [--reference-urls "https://url1,https://url2"] \
  [--instructions "Additional guidance for the AI"]
```
Creates a content item with status `outline` once complete.

### Generate full article from outline (async, ~60–180 s)
```bash
python3 scripts/generate_article.py --content-id <cid> [--project-id <id>]
```
Content item must have status `outline`. Produces the full article.

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

- Progress: `⏳ **Generating outline…** (~30–90 s)`
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

- Progress: `⏳ **Writing article…** (~60–180 s)`
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
