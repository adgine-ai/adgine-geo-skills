---
name: adgine/geo-topics
description: Creates and manages GEO content topics and AI answer prompts for SEO and citation strategy. Supports creating topics (主题 / topic), batch creation, listing topics, listing all prompts across the entire project (跨主题 / cross-topic), adding or editing individual prompts, and triggering AI-powered bulk prompt generation (async). Use when the user wants to organize content categories (内容分类 / content categories), create AI search prompts (提示词 / prompts / AI 查询), generate batches of prompts automatically, manage their topic-prompt structure, or build the foundation for citation tests and article generation. Intent synonyms: topics, 主题词, prompts, 提示词, 提示词生成, generate prompts, list all prompts, 全部提示词.
---

# GEO Topics

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

> ✅ Topic **"Product Reviews"** created — ID: `t-abc`
> ✅ Topic `t-abc` updated — *<changed fields>*
> 🗑️ Topic `t-abc` deleted.

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

> ✅ Prompt created — ID: `p-123`
> ✅ Prompt `p-123` updated.
> 🗑️ Prompt `p-123` deleted.

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
