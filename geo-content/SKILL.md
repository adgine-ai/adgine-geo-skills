---
name: adgine/geo-content
description: Generates AI-optimized article outlines and full articles for GEO
  content strategy, and manages the content library. Supports generating title
  suggestions, producing a keyword-optimized outline (async), writing a complete
  article from an approved outline (async), listing/editing/deleting content items.
  Use when the user wants to create an article, generate an outline, write GEO-optimized
  content, check content status, review generated articles, or manage their content pipeline.
---

# GEO Content

## Step 1: Locate your API key

**A)** `printenv GEO_API_KEY` → returns a value → proceed.  
**B)** `grep '^GEO_API_KEY=' .env 2>/dev/null` → found → `export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)`  
**C)** Not found → ask the user for a key from https://platform.adgine.ai, then `export GEO_API_KEY=geo_sk_live_xxx`

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as `$GEO_API_KEY` (the environment variable). Never hardcode the key value or use placeholder strings like `API_KEY=***` or `API_KEY=geo_sk_live_xxx` directly in a command — this will cause authentication failures.


## Project selection

```bash
export GEO_PROJECT_ID=<project-id>   # session shortcut — resets when terminal closes
# Run python3 scripts/list_projects.py from geo-projects skill to find your IDs
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

> 📄 **Content Library** — Project `<project-id>` (Page 1 / N)

📚 Items
```
┌────┬─────────┬──────────────────────────────────────┬──────────┐
│  # │ Status  │ Title                                │ ID       │
├────┼─────────┼──────────────────────────────────────┼──────────┤
│  1 │ Draft   │ How to Improve Your SEO in 2025      │ abc123   │
│  2 │ Outline │ Top 10 GEO Strategies for SaaS       │ def456   │
│  3 │ Article │ What is Generative Engine Optimi...  │ ghi789   │
└────┴─────────┴──────────────────────────────────────┴──────────┘
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
