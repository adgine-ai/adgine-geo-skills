# Stable reporting protocol

## Contents

- Output modes and markers
- Report schema
- Density and visual mapping
- Coverage and unit rules
- Entity resolution and performance
- Audit, privacy, and empty values
- Locale selection and bilingual output
- Template maintenance

## Output modes and markers

Use `scripts/report.py` for all read-only GEO reports.

- `auto` is the CLI default. It resolves to the scenario's declared `default_format`.
- Analysis, trend, inventory, and multi-source scenarios normally resolve to `html` and write a standalone file under the caller's `adgine-reports/` directory. This is a mandatory same-turn action, not a suggestion that waits for a second user request.
- Project lists and small single-record scenarios (`projects`, `account-info`, `worker-deployment`, `saas-task`, and `opportunity-detail`) resolve to inline `markdown`.
- An explicit `--format html|markdown|json|both` always overrides the scenario default.
- `markdown` prints a fixed narrative/table representation.
- `json` prints the stable report contract.
- `both` prints Markdown and writes HTML.

After writing HTML, emit these WorkBuddy-compatible lines:

```text
REPORT_TITLE: <title>
REPORT_FILE: <absolute path>
REPORT_PREVIEW: <absolute path>
REPORT_LINK: <localized Markdown link to the absolute path>
REPORT_FINDING: <deterministic finding, at most 3>
REPORT_NEXT: <contextual next question, at most 3>
```

Consume these markers directly. Do not perform another API query merely to restate the result.

### WorkBuddy delivery contract

- Treat `REPORT_FILE` as the file-existence source of truth.
- Treat `REPORT_PREVIEW` as a hint for an optional WorkBuddy presentation
  facility. Printing the marker does not prove that the UI opened a panel.
- Treat `REPORT_LINK` as mandatory final-reply content. Copy it before the
  findings so users always have a visible entry point independent of native UI
  rendering.
- Keep the artifact under the current task workspace. When the report command
  is invoked from an installed Skill directory, pass an explicit
  `--output-dir <task-workspace>/adgine-reports`.
- Never claim “opened in Preview” unless the host presentation call returned
  success. If no presentation facility exists, return the link without apology;
  it is the supported fallback.
- If `REPORT_LINK` is missing, construct it from the verified `REPORT_FILE`:
  `[打开 HTML 报告](</absolute/path/report.html>)` for Chinese or
  `[Open HTML report](</absolute/path/report.html>)` for English.
- Do not omit the link because the final answer also contains findings or next
  actions. Do not expose a nonexistent link when generation failed.

## Report schema

Every representation derives from one dictionary with `schema_version=1.0`:

| Field | Meaning |
|---|---|
| `report_type` | Stable scenario name from `_contracts.py`. |
| `title`, `subtitle` | Localized user-facing title and scope. Project reports include the project name; Topic, Prompt, and page reports lead with the entity value. |
| `generated_at` | ISO timestamp with offset. |
| `locale`, `timezone` | Presentation context; raw source dates are not silently shifted. |
| `context` | Project label, requested range, platform, and selected entity. |
| `metrics` | KPI cards with raw value, change, format, direction, and optional unit. |
| `charts` | Declarative customer-facing charts using the ten standard types below. |
| `tables` | Explicit columns and rows. |
| `insights` | At most three deterministic observations. |
| `next_actions` | At most three follow-up prompts; excluded from the embedded HTML JSON. |
| `coverage` | Requested/effective range, partial state, source-level status, as-of time, metric-level units, date basis, and freshness fields. |
| `audit` | Resolution rule, API paths/timings, warnings, and quality caveats. |

The HTML embeds a presentation-safe subset of the public report JSON in `#adgine-report-data`. Omit `schema_version`, `coverage`, `audit`, and `next_actions` from the HTML payload; JSON output keeps the complete stable contract. Never embed raw API responses, credentials, or hidden identifiers.

## Locale selection and bilingual output

Support `en-US` and `zh-CN` across HTML, Markdown, JSON, and WorkBuddy markers. Localize report titles, subtitles, context labels, metric and table labels, chart headings, deterministic findings, next actions, coverage, audit headings, empty states, Boolean values, and template chrome.

Apply this priority:

1. Explicit language requested by the user.
2. Primary language of the user's latest instruction, passed by the agent as `--locale zh-CN` or `--locale en-US`.
3. `GEO_REPORT_LOCALE` when configured.
4. `auto` fallback detection from supplied Topic/Prompt text, then `en-US`.

Do not infer solely from an entity name: a Chinese request may analyze an English Topic, and an explicit English report may analyze Chinese content. Do not translate raw Topic/Prompt names, URLs, source values, error codes, or API payload content. Unsupported locales fall back to `en-US` without adding a dependency or an LLM translation call.

## Density and visual mapping

HTML reports are customer-facing and may be used in prospect conversations. Use short, specific
titles; one-sentence plain-language descriptions; visible units; readable legends; and raw entity
names. Never show container labels such as `report_data`, `metrics`, `summary`, or backend field paths.

Support these chart `type` values without external libraries:

| Type | Use only when the data has this shape |
|---|---|
| `bar_chart` | Comparable categories or a ranked list. |
| `line_chart` | Ordered date/time series. |
| `pie_chart` | Mutually exclusive parts of a known whole; render as a donut by default. |
| `gauge` | One bounded 0–100 score where higher is better. |
| `funnel` | Explicit ordered stages with non-increasing volumes. |
| `scatter_plot` | At least three records sharing two meaningful numeric metrics. |
| `treemap` | Additive contribution categories with at least four positive values. |
| `heatmap_table` | A two-dimensional category matrix. |
| `progress_bar` | One or more bounded rates, shares, coverage, or completion percentages. |
| `timeline` | Dated events, executions, jobs, or publications. |

Select the chart from the data shape, not from visual variety. Never fabricate missing stages,
percentages, pairings, chronology, hierarchy, or denominators merely to use a particular chart.
When no chart truthfully fits, keep a concise table.

Use four stable densities:

| Density | Use | Primary visuals |
|---|---|---|
| `analysis` | Trends, comparisons, prioritization | KPI cards, `line_chart`, `bar_chart` / `heatmap_table`, ranked table |
| `inventory` | Topics, Prompts, pages, content, projects | Counts and dense sortable-style tables |
| `detail` | One Prompt, Topic, page, opportunity, or content item | Entity context, focused KPIs, related tables |
| `status` | Jobs, integration health, billing, publication | State cards, timestamps, issue tables |

Map data deterministically:

- Date series → `line_chart`; show the previous period as a dashed comparison series when available.
- Map each source's real daily fields. Customer-facing GA4 sections use only AI referral sessions, AI referral users, and AI referral rate from `/integrations/ga4/ai-referrals`. Customer-facing Cloudflare sections use only `ai_assistant`, `ai_search`, `ai_training`, and their platform leaderboards from `/ai-agent/overview-kpi`. Never assume a generic `value` field.
- Brand/platform comparisons → `bar_chart` or `heatmap_table`.
- True parts-of-whole distributions → `pie_chart`; never use it for arbitrary rankings.
- Bounded quality scores → `gauge`; bounded shares/rates/progress → `progress_bar`.
- Explicit ordered, non-increasing stages → `funnel`; mutually exclusive status counts remain `pie_chart`.
- Paired numeric records → `scatter_plot` when at least three complete points exist.
- Additive top-source/page contributions → `treemap`; non-additive rankings remain `bar_chart`.
- Dated jobs/executions/publications/events → `timeline`.
- Flow links → `bar_chart` plus a link table.
- KPIs → cards; do not turn arbitrary categorical rows into decorative charts.

Omit the Worker trend from composite customer reports (`executive-overview` and `traffic-overview`). Keep it only in a dedicated Worker report requested by the user.

Never render revenue or transaction fields. The reporting facade does not calculate them, and it does not add GA4 sessions to Cloudflare HTTP requests. Render Cloudflare platform distribution as a three-column comparison (`ai_assistant`, `ai_search`, `ai_training`) without adding the categories into a synthetic total.

Place charts in a responsive two-column grid, with trend lines and heatmaps spanning the full width. Keep exact records in tables below the visuals.

Keep long labels intact in tables. SVG bar labels may visually shorten at the right edge but must preserve the full label in a tooltip.

## Coverage and unit rules

Always distinguish these units:

- GA4 customer reports: AI referral sessions, AI referral active users, and AI referral rate.
- Cloudflare Analytics: HTTP requests, cached requests, bytes, threats, page views, unique visitors.
- Cloudflare Worker: captured events/requests by AI traffic type.
- AI Agent: derived bot/human event aggregates, with endpoint-specific source metadata.
- Visibility: percentages, positions, ranks, and completed model execution counts.

Never add metrics across those unit families. A management overview may place them next to one another only when each card/table keeps its source and unit.

Default `end` to yesterday. Report the requested range separately from each source's available/as-of state. Mark optional failures as `partial` or `error` while still producing the artifact. Fail the report only when a required primary source fails.

Do not auto-sync external systems. A report reflects already-ingested local data unless a scenario explicitly documents a realtime endpoint; current report scenarios use local/cached reads.

## Capability, fallback, and performance

Apply the smallest call plan:

- Topic portfolio: one `/analytics/topics` call.
- Topic detail by ID/exact name: one `/report-data/topic-performance` business call.
- Prompt by ID/exact text: one `/report-data/prompt-performance` business call.
- Page detail and multi-source overview: one report-data aggregate business call.
- Paginated reads: 40 rows per page; next-page offsets advance by exactly 40.

Cache only report-data capabilities on disk for two hours, keyed by API origin and Project ID. Never cache report business data or persist API credentials. A cold cache adds one capability request; a warm cache sends only the business request. Set `GEO_REPORT_CAPABILITY_CACHE_TTL_SECONDS` to a non-negative number of seconds to shorten the window during a backend rollout; `0` forces a capability probe on every report command.

Fallback rules are strict:

- Legacy workflow is allowed for capability/route 404 or 501, `feature=false`, or unsupported schema version.
- A capability discovery outage may use stale cache; without cache it uses legacy workflow with an explicit audit warning.
- 401, 403, entity 404 (`40405`/`40406`), 409, 422, business 5xx, and business timeouts never silently fall back.

Exact matching wins. If text has zero or multiple matches, stop and request/use an ID instead of guessing.

## Audit, privacy, and empty values

- Mask Project, Topic, Prompt, Opportunity, Content, and Task IDs in user-facing audit paths.
- Omit all `*_id` fields by default. Use `--show-ids` only for explicit debugging.
- Remove secrets and keys even when `--show-ids` is enabled.
- Record entity resolution rule, time window, locale, timezone, concurrency cap, API path, duration, and failure status.
- Never expose API keys, OAuth tokens, Cloudflare tokens, Worker secrets, WordPress passwords, or generated Worker source containing secrets.
- For `account-info`, expose only creation time, account name, phone, and email from `/api/auth/me`; omit the user ID, subscription/credits information and follow-up prompts, and all unrelated response fields.
- Show `0` as zero. Show `null`/missing as `—`.
- If an execution count is zero, state that no completed executions were observed; do not convert this to a performance score of zero.
- Treat average position/rank, bounce, latency, negative sentiment, and Web Vitals as lower-is-better when assigning direction color.

## Template maintenance

Change visuals in `assets/report-template.html` and `_reporting.py`, not in `SKILL.md`. Do not render schema labels, generic summary tables, source/coverage tables, or query-audit sections in HTML. Keep those fields only in the complete JSON contract for diagnostics.

Use the light Adgine brand palette: white surfaces, pale-blue backgrounds, dark navy text,
and blue-to-indigo accents. Keep the template fully offline:

- Inline CSS and SVG only.
- No remote fonts, scripts, images, analytics, or CDN assets.
- Escape all table/context text.
- Escape `</` in embedded JSON.
- Preserve responsive and print styles.

Run the report tests and `quick_validate.py` after changing the contract, renderer, Skill instructions, or agent metadata.
