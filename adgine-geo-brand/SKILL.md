---
name: adgine/geo-brand
description: Views, generates (async AI job), edits and inspects the GEO brand cognition profile for a website project — brand introduction, ideal customer profile, competitor analysis, brand perspective, author persona, voice and tone, writing guidelines — and lists/starts/inspects brand generation background jobs. Use when the user wants to build or update their AI-facing brand identity, generate brand cognition content (品牌画像 / 品牌认知 / brand profile), review existing brand positioning, refine writing style guidelines, or check the status of running/failed brand generation jobs (任务列表 / job status / 重新生成). Intent synonyms: brand profile, 品牌画像, 品牌认知, brand cognition, brand identity, generate brand, brand job status, retry brand generation.
---

# GEO Brand

## Step 1: Locate your API key

**A)** `printenv GEO_API_KEY` → returns a value → proceed.  
**B)** `grep '^GEO_API_KEY=' .env 2>/dev/null` → found → `export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)`  
**C)** Not found → ask the user for a key from https://platform.adgine.ai, then `export GEO_API_KEY=geo_sk_live_xxx`

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as `$GEO_API_KEY` (the environment variable). Never hardcode the key value or use placeholder strings like `API_KEY=***` or `API_KEY=geo_sk_live_xxx` directly in a command — this will cause authentication failures.


## Project selection

All commands require a project ID. Resolve in this order:
1. `--project-id` argument
2. `GEO_PROJECT_ID` env var (session shortcut)
3. Run `python3 scripts/list_projects.py` from the **adgine-geo-projects** skill and ask the user to pick

```bash
export GEO_PROJECT_ID=<project-id>   # session shortcut — resets when terminal closes
```

## Commands

### View current brand profile
```bash
python3 scripts/get_brand.py [--project-id <id>] [--json]
```
Shows: status (`none` / `generating` / `completed`), all brand fields.

### Generate brand profile (AI-powered, async ~30–90 s)
```bash
python3 scripts/generate_brand.py [--project-id <id>] [--language English] [--region US]
```
Starts an AI generation job, polls automatically, then prints the completed profile.

### Update individual brand fields
```bash
python3 scripts/update_brand.py [--project-id <id>] --field <field_name> --value "<text>"
```

**Updatable fields:**

| Field | Description |
|---|---|
| `brand_introduction` | Core brand description for AI audiences |
| `ideal_customer` | Who you serve (demographics, needs, pain points) |
| `competitors` | Direct competitors (for context/differentiation) |
| `brand_perspective` | Unique differentiators and positioning |
| `author_persona` | The narrative voice persona |
| `voice_and_tone` | Writing style guidelines |
| `writing_rules` | Specific do's and don'ts |
| `cta_text` | Call-to-action text |
| `cta_landing_page` | CTA URL |
| `language` | Brand content language (default: English) |
| `region` | Target region (default: US) |

### Brand generation jobs

List recent brand jobs:
```bash
python3 scripts/list_jobs.py list [--project-id <id>] [--page 1] [--limit 20] [--json]
```

Inspect one job in detail (status, phases, error message):
```bash
python3 scripts/list_jobs.py get --job-id <id>
```

Manually start a job that was created with `auto_start=false`:
```bash
python3 scripts/list_jobs.py start --job-id <id>
```

## Workflow

See `WORKFLOW.md` for the recommended first-time setup sequence.

## Output Format

> ⚠️ **CRITICAL — Table cell content rule (must follow exactly):**
> Tables use fenced code blocks with box-drawing borders. They only align correctly when **every cell contains ASCII characters exclusively**.
> - **NEVER** put emoji inside table cells — they are 2 display units wide but count as 1 character, permanently misaligning all following columns.
> - Emoji go ONLY on the label line **above** the ` ``` ` fence.
> - Status values in cells: `Completed` / `Generating` / `Not set` / `Failed` (NOT ✅/⏳/❌)

---

### When showing an existing brand profile (`get_brand.py`)

**1. Status table:**

🏷️ Brand Profile
```
┌────────────┬──────────────────────────────────────┐
│ Field      │ Value                                │
├────────────┼──────────────────────────────────────┤
│ Project    │ <project-id>                         │
│ Status     │ Completed                            │
│ Language   │ English                              │
│ Region     │ US                                   │
│ CTA Text   │ <cta_text>                           │
│ CTA URL    │ <cta_landing_page>                   │
└────────────┴──────────────────────────────────────┘
```
Status values in cell: `Completed` / `Generating` / `Not set` / `Failed`

**2. Content fields** — use `###` headings + full text (never truncate). Skip empty with *"not set yet"*:

### Brand Introduction
<brand_introduction text>

### Ideal Customer
<ideal_customer text>

### Competitors
<competitors text>

### Brand Perspective
<brand_perspective text>

### Author Persona
<author_persona text>

### Voice & Tone
<voice_and_tone text>

### Writing Rules
<writing_rules text>

---

### When generating a brand profile (`generate_brand.py`)

- Initial line: `⏳ **Generating brand profile…** (~30–90 s)`
- On completion, show the status table + all content sections above.

---

### When updating a field (`update_brand.py`)

✅ Field Updated
```
┌────────────┬──────────────────────────────────────┐
│ Field      │ <field_name>                         │
│ New Value  │ <preview, first 60 chars>            │
└────────────┴──────────────────────────────────────┘
```
Then show the full new value below the table if it was truncated.
