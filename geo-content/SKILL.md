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

**When listing content** (`list_content.py`):
```
📄 Content Library — <project-id>  (Page 1 of N)

  1. 📝 [draft]    "How to Improve Your SEO in 2025"        ID: abc123
  2. 📋 [outline]  "Top 10 GEO Strategies for SaaS"         ID: def456
  3. ✅ [article]  "What is Generative Engine Optimization?" ID: ghi789
```
Status icons: 📝 draft · 📋 outline · ✅ article

**When suggesting titles** (`generate_titles.py`):
```
💡 Suggested Titles
  1. "How to Dominate AI Search in 2025"
  2. "The Complete Guide to GEO for SaaS Companies"
  3. "Why Traditional SEO Is Not Enough Anymore"
  ... (up to 10)
Ask the user: "Which title would you like to use for the outline?"
```

**When generating an outline** (`generate_outline.py`):
- Progress: `⏳ Generating outline… (30–90 s)`
- On completion, show the full outline with section headings as a numbered list.
- End with: `✅ Outline ready. Content ID: **<id>**  Run generate_article.py to write the full article.`

**When generating an article** (`generate_article.py`):
- Progress: `⏳ Writing article… (60–180 s)`
- On completion:
```
✅ Article complete!
  Title:    "<title>"
  Content ID: <id>
  Words:    ~1,200
  Status:   article

<full article text shown below>
```
