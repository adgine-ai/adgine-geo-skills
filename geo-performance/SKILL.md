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

## Step 1: Locate your API key

**A)** `printenv GEO_API_KEY` → returns a value → proceed.  
**B)** `grep '^GEO_API_KEY=' .env 2>/dev/null` → found → `export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)`  
**C)** Not found → ask the user for a key from https://platform.adgine.ai, then `export GEO_API_KEY=geo_sk_live_xxx`

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

> ⚠️ **CRITICAL — Telegram rendering rules:**
> - **Do NOT use Markdown pipe tables** — Telegram strips them.
> - Render tables as **fenced code blocks** with **box-drawing characters**.
> - Use **bold**, *italic*, emoji, and `[label](url)` links freely.

---

### 1. Header (blockquote)

> 🔬  **Page Health** — `<path>` *(<strategy>)*  
> Project: `<project-id>` · Analyzed: `<timestamp>`

### 2. Score card (fenced monospace)

```
🎯  Overall Score
┌──────────────────────────────────────────────────┐
│  78 / 100   ⚠️ Needs Improvement                 │
│                                                  │
│  ███████████████░░░░░  78%                       │
└──────────────────────────────────────────────────┘
```

**Score bar logic** — 20 cells total, `█` for filled, `░` for empty:
- score `78` → 15 filled (`78/100 * 20 = 15.6 → 15`)
- score `92` → 18 filled
- score `45` → 9 filled

**Rating icons:** 90–100 ✅ Good · 50–89 ⚠️ Needs Improvement · 0–49 ❌ Poor

### 3. Health checks (single fenced block)

```
🩺  Health Checks
┌──────────────────┬──────────────────┬────────────┬─────────────────────┐
│ Category         │ Check            │ Status     │ Notes               │
├──────────────────┼──────────────────┼────────────┼─────────────────────┤
│ 🕷️  Crawlability │ Robots.txt       │ ✅ Allowed │ —                   │
│ 🕷️  Crawlability │ Noindex          │ ✅ None    │ —                   │
│ 🕷️  Crawlability │ Auth wall        │ ❌ Found   │ AI crawlers blocked │
│ 🤖  AI Optimize  │ Schema markup    │ ✅ Present │ Article, Breadcrumb │
│ 🤖  AI Optimize  │ FAQ schema       │ ⚠️  Missing│ Add for snippets    │
│ 📑  Indexing     │ Indexed          │ ✅ Yes     │ Crawled 2025-05-10  │
│ 📝  Content      │ Word count       │ ⚠️  Short  │ 450 / min 800       │
│ 📝  Content      │ Duplicate titles │ ✅ None    │ —                   │
└──────────────────┴──────────────────┴────────────┴─────────────────────┘
```

### 4. Recommended actions (only if any ⚠️ or ❌ exist)

```
💡  Top Actions
┌────────────┬──────────────────────────────────────────────────┐
│ Priority   │ Action                                           │
├────────────┼──────────────────────────────────────────────────┤
│ 🔴 High    │ Remove auth wall or add AI crawler exception     │
│ 🟡 Medium  │ Expand content to 800+ words                     │
│ 🟡 Medium  │ Add FAQ schema markup                            │
└────────────┴──────────────────────────────────────────────────┘
```

Priority assignment:
- ❌ Failed checks → 🔴 High
- ⚠️ Warnings on crawlability/indexing → 🔴 High
- ⚠️ Warnings on content/optimization → 🟡 Medium
- Nice-to-haves → 🟢 Low

If all checks pass, replace this section with:
> 🎉  **All checks pass.** No action needed.
