---
name: adgine/geo-brand
description: Views, generates, and edits the GEO brand cognition profile for a
  website project — including brand introduction, ideal customer profile, competitor
  analysis, brand perspective, author persona, voice and tone, and writing guidelines.
  Use when the user wants to build or update their AI-facing brand identity, generate
  brand cognition content, review existing brand positioning, or refine writing
  style guidelines for GEO (Generative Engine Optimization) visibility.
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
3. Run `python3 scripts/list_projects.py` from the **geo-projects** skill and ask the user to pick

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

## Workflow

See `WORKFLOW.md` for the recommended first-time setup sequence.

## Output Format

**When showing an existing brand profile** (`get_brand.py`), open with a status summary table, then show each field:

**Status overview table:**

| Field | Value |
|-------|-------|
| Project | `<project-id>` |
| Status | ✅ Completed / ⏳ Generating / ➕ Not set up |
| Language | English |
| Region | US |
| CTA | `<cta_text>` → `<cta_landing_page>` |

Then present each content field as a titled section (use `###` heading + full text — do not truncate):

```
### 📌 Brand Introduction
<brand_introduction text>

### 👥 Ideal Customer
<ideal_customer text>

### ⚔️ Competitors
<competitors text>

### 💡 Brand Perspective
<brand_perspective text>

### ✍️ Author Persona
<author_persona text>

### 🎙️ Voice & Tone
<voice_and_tone text>

### 📋 Writing Rules
<writing_rules text>
```

**When generating a brand profile** (`generate_brand.py`):
- Show: `⏳ Generating brand profile… (~30–90 s)`
- When complete, display the status table then all content sections above.

**When updating a field** (`update_brand.py`), confirm with a mini table:

| Field Updated | New Value |
|---------------|-----------|
| `<field_name>` | `<new value preview>` |

Long text fields should always be shown in full — never truncate.
