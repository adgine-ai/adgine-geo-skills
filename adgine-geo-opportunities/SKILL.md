---
name: adgine/geo-opportunities
description: Discovers and displays GEO optimization opportunities for a project.
  Shows AI-identified content gaps, topic opportunities, and actionable recommendations
  ranked by potential impact (relevance, traffic, competition, urgency, AI citation).
  Use when the user wants to find new content ideas, discover optimization opportunities,
  see what topics they should target, or get prioritized recommendations for improving
  their AI visibility.
---

# GEO Opportunity Discovery

## Output rules — IDs (apply to every reply)

These rules apply to **every list, table, and confirmation message** in this skill. Their goal: keep user-facing output friendly while preserving the IDs the agent needs internally.

1. **Lists & tables — never show raw UUIDs in cells.** Use a 1-based `#` index column instead. Keep a private mental mapping of `#N → actual UUID` so that follow-up commands like *"show details of #3"*, *"tell me more about the 2nd one"* resolve to the right entity.
   - Index numbers restart from 1 in each new list — they are not stable across calls.
   - If the user references *"the opportunity about X"*, match by visible content (title / category), not by ID.

2. **Single-item operations — prefer a human name over an ID.**
   - ✅ *"Opportunity **Optimize product comparison pages** — score 85/100."*
   - ❌ *"Opportunity `a4305b57-1c79-4cec-a17c-16eb1d959ea6` — score 85."*
   - If the entity has **no human-readable name**, use a short 8-character prefix: `2a2a8f4f…`

3. **Always exception: `--json` mode.** When the user passes `--json` to a script or explicitly asks for raw JSON / debug output, print the script output verbatim — do not strip IDs.

4. **Internally, the agent still uses full UUIDs** for every API call (`--project-id`, `--opportunity-id`, etc.). The display rules only affect what is shown back to the user.

---

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

## What are opportunities?

Opportunities are AI-identified content gaps and optimization recommendations for your project. The system analyzes your current visibility, topics, competitors, and AI citation data to surface high-impact actions you can take to improve GEO performance.

Each opportunity includes:
- **Title** — a concise description of the opportunity
- **Total Score** — composite impact score (higher = more impactful)
- **Scores** — radar chart dimensions: relevance, traffic, competition, urgency, ai_citation
- **Category** — type of opportunity (e.g., content gap, optimization, new topic)
- **Rationale** — why this opportunity matters
- **Guidance** — strategic direction
- **Implementation** — concrete step-by-step actions
- **Coverage** — current coverage data
- **Source URLs** — reference links supporting the recommendation

---

## Commands

### List project opportunities
```bash
python3 scripts/list_opportunities.py [--project-id <id>] [--json]
```
Returns the latest batch of opportunities for the project. Three possible states:
- **ready** — opportunities are available, displays ranked list
- **pending** — opportunities are being generated, check back later
- **empty** — no opportunities have been generated yet

### Get opportunity detail
```bash
python3 scripts/get_opportunity.py --opportunity-id <id> [--project-id <id>] [--json]
```
Shows the full detail of a single opportunity including:
- Title & total score
- Score breakdown (radar dimensions)
- Category & rationale
- Guidance
- Implementation steps (numbered action items)
- Coverage details
- Source URLs

---

## Workflow

1. List opportunities: `python3 scripts/list_opportunities.py`
2. Review the ranked list — higher scores = higher potential impact
3. Drill into specific opportunities: `python3 scripts/get_opportunity.py --opportunity-id <id>`
4. Follow the implementation steps to act on the opportunity
5. Use other skills to execute (e.g., `adgine-geo-content` for article generation, `adgine-geo-topics` for new topics)

---

## Output Format

> ⚠️ **CRITICAL — Table cell content rule (must follow exactly):**
> Tables use fenced code blocks with box-drawing borders. They only align correctly when **every cell contains ASCII characters exclusively**.
> - **NEVER** put emoji inside table cells.
> - Emoji go ONLY on the label line **above** the ` ``` ` fence.
> - Status values in cells: `Ready` / `Pending` / `Empty`
> - Use `[label](url)` for clickable URLs (outside fenced blocks).

---

### When listing opportunities (`list_opportunities.py`)

> 🔍 **Opportunities** — *N items found* (run date: YYYY-MM-DD)

```
┌────┬────────────────────────────────────┬───────┬──────────────┐
│  # │ Title                              │ Score │ Category     │
├────┼────────────────────────────────────┼───────┼──────────────┤
│  1 │ Optimize product comparison pages  │    85 │ content_gap  │
│  2 │ Add FAQ schema to landing pages    │    72 │ optimization │
│  3 │ Target "best X alternatives" topic │    68 │ new_topic    │
└────┴────────────────────────────────────┴───────┴──────────────┘
```

> 💡 Use `get_opportunity.py --opportunity-id <id>` for full details on any item.

---

### When showing opportunity detail (`get_opportunity.py`)

> 🎯 **Opportunity Detail**
> Title: *"<title>"*
> Score: **N/100**

📊 Score Breakdown
```
┌──────────────┬───────┐
│ Dimension    │ Score │
├──────────────┼───────┤
│ Relevance    │    18 │
│ Traffic      │    16 │
│ Competition  │    17 │
│ Urgency      │    15 │
│ AI Citation  │    19 │
└──────────────┴───────┘
```

**Category:** content_gap
**Rationale:** "<rationale text>"
**Guidance:** "<guidance text>"

📋 Implementation Steps:
1. Step one description
2. Step two description
3. Step three description

🔗 Source URLs:
- [source1.com/page](https://source1.com/page)
- [source2.com/article](https://source2.com/article)
