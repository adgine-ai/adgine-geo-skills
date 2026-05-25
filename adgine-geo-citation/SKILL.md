---
name: adgine/geo-citation
description: Runs AI citation visibility tests to measure how often a brand or website
  is cited in AI-generated responses across platforms like ChatGPT, Perplexity,
  Google AI Overviews, and Gemini. Supports submitting prompts for testing, retrieving
  test results, and viewing citation URLs. Use when the user wants to check their
  AI visibility, test whether their brand is cited by AI search engines, measure
  citation rates, review AI platform responses, or audit which URLs are being cited.
---

# GEO Citation Tests

## Step 1: Locate your API key

**A)** `printenv GEO_API_KEY` → returns a value → proceed.  
**B)** `grep '^GEO_API_KEY=' .env 2>/dev/null` → found → `export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)`  
**C)** Not found → ask the user for a key from https://platform.adgine.ai, then `export GEO_API_KEY=geo_sk_live_xxx`

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
