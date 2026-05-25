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

## Step 1: Locate your API key

**A)** `printenv GEO_API_KEY` → returns a value → proceed.
**B)** `grep '^GEO_API_KEY=' .env 2>/dev/null` → found → `export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)`
**C)** Not found → ask the user for a key from the GEO platform.

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
