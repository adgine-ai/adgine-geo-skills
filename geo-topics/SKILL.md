---
name: adgine/geo-topics
description: Creates and manages GEO content topics and AI answer prompts for SEO
  and citation strategy. Supports creating topics, listing topics, adding or editing
  individual prompts, and triggering AI-powered bulk prompt generation (async).
  Use when the user wants to organize content categories, create AI search prompts,
  generate batches of prompts automatically, manage their topic-prompt structure,
  or build the foundation for citation tests and article generation.
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
# Run python3 scripts/list_projects.py from geo-projects skill to find your IDs
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
