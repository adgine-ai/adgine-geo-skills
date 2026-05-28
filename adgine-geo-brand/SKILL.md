---
name: adgine/geo-brand
description: Views, generates (async AI job), edits and inspects the GEO brand cognition profile for a website project — brand introduction, ideal customer profile, competitor analysis, brand perspective, author persona, voice and tone, writing guidelines — and lists/starts/inspects brand generation background jobs. Use when the user wants to build or update their AI-facing brand identity, generate brand cognition content (品牌画像 / 品牌认知 / brand profile), review existing brand positioning, refine writing style guidelines, or check the status of running/failed brand generation jobs (任务列表 / job status / 重新生成). Intent synonyms: brand profile, 品牌画像, 品牌认知, brand cognition, brand identity, generate brand, brand job status, retry brand generation.
---

# GEO Brand

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

### Generate brand profile (AI-powered, async ~2–5 min)
```bash
python3 scripts/generate_brand.py [--project-id <id>] [--language English] [--region US]
```
Starts an AI generation job, polls automatically, then prints the completed profile.

> ⏳ **Expected duration: 2–5 minutes.** The script polls automatically (interval 8 s, timeout 10 min). Do NOT cancel early.

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

- Initial line: `⏳ **Generating brand profile…** (~2–5 min)`
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
