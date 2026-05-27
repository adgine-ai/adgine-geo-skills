---
name: adgine/geo-performance
description: Analyzes AI-agent page health for website pages in a GEO project,
  returning crawlability status, AI optimization scores, indexing issues, and
  content health checks for mobile or desktop device strategies. Use when the
  user asks about page crawlability, AI indexing status, page health scores,
  whether a page is optimized for AI search engines, content issues on a specific
  page, or any per-page AI visibility metrics.
---

# GEO Performance

Fetches the AI-agent page health report for a specific page path within a project.

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
