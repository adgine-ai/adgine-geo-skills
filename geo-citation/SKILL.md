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
# Run python3 scripts/list_projects.py from geo-projects skill to find your IDs
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

1. Generate prompts: `geo-topics/scripts/generate_prompts.py --topic-id <id>`
2. Run tests: `python3 scripts/create_tests.py --prompt-ids <id1,id2,...>`
3. Wait ~5–15 minutes for AI platforms to respond
4. Review results: `python3 scripts/get_results.py --prompt-id <id>`

## Output Format

**When submitting tests** (`create_tests.py`):
> ✅ Citation tests submitted for **N** prompt(s). Results will be ready in ~5–15 minutes.

**When showing results for a prompt** (`get_results.py`):

```
🔍 Citation Results — "<prompt text>"
Prompt ID: <id>  |  Project: <project-id>

Platform        Status      Cited?   
─────────────────────────────────────
ChatGPT         ✅ Done     ✅ Yes   
Perplexity      ✅ Done     ❌ No    
Google AIO      ⏳ Pending  —        
```

For each platform where citation = Yes, show:
```
  🔗 ChatGPT — Your brand was cited
     Cited URLs:
       • https://example.com/article-1
       • https://example.com/about
     AI Response (excerpt):
       "<first 200 chars of AI response>…"
```

For platforms where citation = No, show:
```
  ❌ Perplexity — Not cited in this response
```

**Summary line** at the end:
> 📊 Citation rate: **2 / 3 platforms** (67%) for this prompt.

**When showing aggregated URLs** (`--aggregate`):
List all cited URLs as a ranked bullet list, showing how many times each was cited:
```
🔗 Most Cited URLs (across N prompts)
  1. https://example.com/guide      — cited 8 times
  2. https://example.com/about      — cited 5 times
  3. https://example.com/pricing    — cited 2 times
```
