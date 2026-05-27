---
name: adgine/geo-topics
description: Creates and manages GEO content topics and AI answer prompts for SEO and citation strategy. Supports creating topics (主题 / topic), batch creation, listing topics, listing all prompts across the entire project (跨主题 / cross-topic), adding or editing individual prompts, and triggering AI-powered bulk prompt generation (async). Use when the user wants to organize content categories (内容分类 / content categories), create AI search prompts (提示词 / prompts / AI 查询), generate batches of prompts automatically, manage their topic-prompt structure, or build the foundation for citation tests and article generation. Intent synonyms: topics, 主题词, prompts, 提示词, 提示词生成, generate prompts, list all prompts, 全部提示词.
---

# GEO Topics

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

```bash
export GEO_PROJECT_ID=<project-id>   # session shortcut — resets when terminal closes
# Run python3 scripts/list_projects.py from adgine-geo-projects skill to find your IDs
```

## Concepts

- **Topic** — a content category or theme (e.g. "Product Reviews", "SEO Guides")
- **Prompt** — an AI search query tied to a topic (e.g. "What is the best SEO tool for small businesses?")

Topics organize prompts. Prompts are used for citation tests and article generation.

---

## Topic commands

### List all topics
```bash
python3 scripts/manage_topics.py list [--project-id <id>] [--page 1] [--limit 20] [--json]
```

### Create a topic
```bash
python3 scripts/manage_topics.py create --name "Product Reviews" [--description "Review-related content"]
```

### Batch-create topics
```bash
python3 scripts/manage_topics.py batch --names "Topic A,Topic B,Topic C"
```

### Update a topic
```bash
python3 scripts/manage_topics.py update --topic-id <id> [--name "New Name"] [--description "..."]
```

### Delete a topic
```bash
python3 scripts/manage_topics.py delete --topic-id <id>
```

---

## Prompt commands

### List prompts for a topic
```bash
python3 scripts/manage_prompts.py list --topic-id <tid> [--project-id <id>] [--json]
```

### List all prompts across the project
```bash
python3 scripts/manage_prompts.py list-all [--project-id <id>] [--json]
```

### Create a prompt manually
```bash
python3 scripts/manage_prompts.py create --topic-id <tid> \
  --content "What is the best GEO tool?" \
  [--language "English (en-US)"] [--region US] \
  [--platforms "openai,perplexity,google_aio"]
```

**Platform IDs:** `openai` · `google_aio` · `perplexity`

### Update a prompt
```bash
python3 scripts/manage_prompts.py update --topic-id <tid> --prompt-id <pid> \
  --content "Updated prompt text"
```

### Delete a prompt
```bash
python3 scripts/manage_prompts.py delete --topic-id <tid> --prompt-id <pid>
```

---

## AI prompt generation (async)

```bash
python3 scripts/generate_prompts.py --topic-id <tid> [--project-id <id>] \
  [--count 10] [--language "English (en-US)"] [--region US] \
  [--platforms "openai,perplexity,google_aio"] \
  [--instructions "Focus on enterprise buyers"]
```

Generates AI search prompts relevant to the topic automatically. Polls until done (~10–60 s).

## Output Format

> ⚠️ **CRITICAL — Table cell content rule (must follow exactly):**
> Tables use fenced code blocks with box-drawing borders. They only align correctly when **every cell contains ASCII characters exclusively**.
> - **NEVER** put emoji inside table cells. They are 2 display units wide but count as 1 character, permanently misaligning all following columns.
> - Emoji go ONLY on the label line **above** the ` ``` ` fence.
> - All cell content must be ASCII: letters, digits, spaces, `+/-/%` only.

---

### When listing topics (`manage_topics.py list`)

> 🗂️ **Topics** — **N** total

🗂️ Topics
```
┌────┬────────────────────────┬─────────┐
│  # │ Topic Name             │ Prompts │
├────┼────────────────────────┼─────────┤
│  1 │ Product Reviews        │      12 │
│  2 │ SEO Guides             │       8 │
│  3 │ Case Studies           │       0 │
└────┴────────────────────────┴─────────┘
```
Truncate long names to ~22 chars with `...`.

---

### When creating / updating / deleting a topic

> ✅ Topic **"Product Reviews"** created.
> ✅ Topic **&lt;topic name&gt;** updated — *<changed fields>*
> 🗑️ Topic **&lt;topic name&gt;** deleted.

---

### When listing prompts (`manage_prompts.py list`)

> 💬 **Prompts** — Topic: *"Product Reviews"* (**N** total)

💬 Prompts
```
┌────┬──────────────────────────────────────┬───────────────────┬────────┐
│  # │ Prompt                               │ Platforms         │ Region │
├────┼──────────────────────────────────────┼───────────────────┼────────┤
│  1 │ What is the best GEO tool for sma... │ ChatGPT,Perp,AIO  │ US     │
│  2 │ How do I improve my AI search vis... │ ChatGPT           │ US     │
└────┴──────────────────────────────────────┴───────────────────┴────────┘
```
Truncate prompts to ~36 chars with `...`.

---

### When creating / updating / deleting a prompt

> ✅ Prompt created under topic **"&lt;topic name&gt;"** (now #&lt;index in latest list&gt;).
> ✅ Prompt **#&lt;index&gt;** updated.
> 🗑️ Prompt **#&lt;index&gt;** deleted.

(Refer to the prompt by the `#N` index shown in the most recent list. If no list is in context, fall back to the prompt's first 60 characters of text — not its UUID.)

---

### When generating prompts (`generate_prompts.py`)

- Progress: `⏳ **Generating prompts** for topic *"<name>"*… (~10–60 s)`
- On completion:

> ✅ **Generated N prompts** for topic *"<name>"*

✨ Generated Prompts
```
┌────┬──────────────────────────────────────────────────────┐
│  # │ Prompt                                               │
├────┼──────────────────────────────────────────────────────┤
│  1 │ What tools help with generative engine optimization? │
│  2 │ How do AI search engines rank websites differently?  │
└────┴──────────────────────────────────────────────────────┘
```

> **Next:** run citation tests:
> `python3 adgine-geo-citation/scripts/create_tests.py --prompt-ids <id1,id2,...>`
