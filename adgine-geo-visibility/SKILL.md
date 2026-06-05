---
name: adgine/geo-visibility
description: Reads and analyzes already-collected AI visibility data for a GEO
  project — Visibility Score, Share of Voice, Average Position, competitor matrix,
  historical AI executions, full AI responses, brand mentions, cited URLs.
  Use when the user wants to READ analytics results: AI visibility / 可见性得分 /
  Visibility Score / 声量份额 / Share of Voice / 平均排名 / 竞品对比 / 平台矩阵 /
  AI 回答历史 / prompt 历史测试 / AI 具体怎么回复的 / 品牌提及 / 引用链接.
  NOT for running new citation tests (向 AI 平台发请求测试是否引用) — use
  adgine-geo-citation to actively submit prompts and collect new results.
  NOT for lightweight dashboard summary — use adgine-geo-dashboard instead.
---

# GEO Visibility (Analytics)

Deep analytics over `/api/projects/{id}/analytics/*` — 11 endpoints covering
the AI visibility funnel from brand-level single metrics down to individual
prompt executions.

> Lightweight dashboard summary lives in **adgine-geo-dashboard**.
> Prompt CRUD / start-analysis actions live in **adgine-geo-topics**.

## 触发条件

当用户说出以下意图时使用本 skill：
- “可见性得分” / “Visibility Score” / “我的可见度”
- “声量份额” / “Share of Voice” / “平均排名” / “Average Position”
- “竞品对比” / “平台矩阵” / “competitor matrix”
- “AI 回答历史” / “AI 具体怎么回复的” / “prompt 历史测试结果”
- “品牌提及” / “引用链接”（查看已有数据）

**⛔ 以下意图不属于本 skill：**
- “跑一次引用测试” / “测试 AI 是否引用”（发起新测试）→ **adgine-geo-citation**
- “项目总览” / “Dashboard” / “近七天趋势” → **adgine-geo-dashboard**
- “创建提示词” / “管理主题” → **adgine-geo-topics**

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

---

## Post-task recommendations

After visibility analysis, suggest actions to improve or act on the results:

| What you saw | Suggest |
|---|---|
| Low Visibility Score | `adgine-geo-citation` — 运行新引用测试，诊断哪些平台未引用 |
| Low Share of Voice | `adgine-geo-content` — 针对弱项话题生成更多 GEO 内容 |
| Competitor outperforming | `adgine-geo-brand` — 优化品牌画像，强化差异化定位 |
| Specific prompt performing well | `adgine-geo-content` — 基于该 prompt 生成扩展文章 |
| Specific prompt performing poorly | `adgine-geo-topics` — 优化或替换该 prompt |
| Execution history reviewed | `adgine-geo-aiagent` — 查看对应页面的 AI 爬虫访问数据 |

> 💡 **建议下一步：**
> 1. **[action]** → `skill-name`
> 2. **[action]** → `skill-name`
