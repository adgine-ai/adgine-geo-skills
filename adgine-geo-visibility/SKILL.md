---
name: adgine/geo-visibility
description: Deep AI visibility analytics for a GEO project — query Visibility Score / Share of Voice / Average Position at brand, topic, or prompt level; inspect competitor × AI-platform matrix; drill into a prompt's per-platform breakdown; review historical AI executions including full responses, brand mentions, and citations. Use when the user asks about AI visibility / 可见性得分 / 可见度 / Visibility Score / 声量份额 / Share of Voice / 平均排名 / Average Position / 主题可见度 / 提示词表现 / prompt 可见度 / 竞品对比 / 平台矩阵 / matrix / AI 平台表现 / AI 回答历史 / prompt 历史测试 / AI 具体怎么回复的 / 品牌提及 / brand mentions / 引用链接. For lightweight dashboard summary, use adgine-geo-dashboard instead.
---

# GEO Visibility (Analytics)

Deep analytics over `/api/projects/{id}/analytics/*` — 11 endpoints covering
the AI visibility funnel from brand-level single metrics down to individual
prompt executions.

> Lightweight dashboard summary lives in **adgine-geo-dashboard**.
> Prompt CRUD / start-analysis actions live in **adgine-geo-topics**.

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

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as `$GEO_API_KEY` (the environment variable). Never hardcode the literal value.

## Project selection

```bash
export GEO_PROJECT_ID=<project-id>
```

## Scripts

### Brand-level single metrics

```bash
python3 scripts/get_visibility.py score
python3 scripts/get_visibility.py share-of-voice
python3 scripts/get_visibility.py average-position
# common opts: --platform openai|google_aio|perplexity|gemini --start ... --end ...
```

### Competitor × platform matrix

```bash
python3 scripts/get_matrix.py                 # default: visibility metric
python3 scripts/get_matrix.py --metric sov
```

### Topic-level metrics

```bash
python3 scripts/get_topic_metrics.py list                         # full Topic dimension
python3 scripts/get_topic_metrics.py visibility                   # lightweight picker list
python3 scripts/get_topic_metrics.py prompts --topic-id <id>      # prompts under topic
python3 scripts/get_topic_metrics.py prompts-visibility --topic-id <id>
```

### Per-prompt overview

```bash
python3 scripts/get_prompt_metrics.py --prompt-id <prompt_id>
# adds: previous-period delta + per-platform breakdown
```

### Prompt execution history & detail

```bash
python3 scripts/get_execution.py list --prompt-id <prompt_id>
python3 scripts/get_execution.py list --prompt-id <pid> --platform openai
python3 scripts/get_execution.py get --prompt-id <pid> --execution-id <eid>
```

## Output Format

ASCII tables only inside fenced code blocks. Numeric formatting: 1 or 2
decimals depending on metric scale; "%" suffix for percentage metrics;
"--" for null. Change-from-previous-period is shown with explicit sign
("+1.5" / "-0.3").

## Metric vocabulary

| Metric            | Unit | Typical range |
|---|---|---|
| Visibility Score  | %    | 0–100  |
| Share of Voice    | %    | 0–100  |
| Average Position  | rank | 1+ (lower is better) |

## Platform codes

`openai` · `google_aio` · `perplexity` · `gemini`

## Related endpoints

| Method | Path |
|---|---|
| GET | `/api/projects/{id}/analytics/visibility/score` |
| GET | `/api/projects/{id}/analytics/visibility/share-of-voice` |
| GET | `/api/projects/{id}/analytics/visibility/average-position` |
| GET | `/api/projects/{id}/analytics/platforms/matrix` |
| GET | `/api/projects/{id}/analytics/topics` |
| GET | `/api/projects/{id}/analytics/topics/visibility` |
| GET | `/api/projects/{id}/analytics/topics/{topic_id}/prompts` |
| GET | `/api/projects/{id}/analytics/topics/{topic_id}/prompts/visibility` |
| GET | `/api/projects/{id}/analytics/prompts/{prompt_id}/overview` |
| GET | `/api/projects/{id}/analytics/prompts/{prompt_id}/executions` |
| GET | `/api/projects/{id}/analytics/prompts/{prompt_id}/executions/{execution_id}` |
