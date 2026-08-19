---
name: adgine/geo-reports
description: Generate stable, auditable Adgine GEO data reports as localized English or Simplified Chinese standalone offline HTML, Markdown, or JSON. Use this facade for every read-only data query, dashboard, analysis, inventory, status review, or report request across account information, AI visibility, Topics, Prompts, citations, sentiment, GA4, Cloudflare, AI bots, AI-driven human traffic, pages, PageSpeed health, opportunities, content, publishing, integrations, projects, domains, SaaS, and billing. Trigger for requests such as “查询我的账号信息 / my account information / my profile / my name, phone or email”, “this prompt/topic in the last week or half month”, “show my GEO data”, “generate a report”, “which pages have opportunities”, “GA4/Cloudflare/AI bot performance”, and “export HTML”.
---

# Adgine GEO Reports

Use `scripts/report.py` as the default entry point for all platform data reads. Keep the specialist Skills for mutations, setup, and low-level debugging.

## Required workflow

1. Resolve the active project from `--project-id` or `GEO_PROJECT_ID` when the scenario is project-scoped. Pass `--project-name` when the exact name is already known; otherwise the script loads it from the existing project-detail endpoint for user-facing titles.
2. Match the report language to the user's latest request and always pass it explicitly:
   - Primarily Chinese request → `--locale zh-CN`
   - Primarily English request → `--locale en-US`
   - An explicit request such as “用英文输出” overrides automatic choice.
   - Detect the language from the user's instruction, not only the Topic/Prompt entity text. The script's `auto` mode is a fallback for Chinese Topic/Prompt text when the caller omits this step.
3. Translate natural-language windows to explicit options:
   - 最近一周 / last week → `--period 7d`
   - 最近半个月 / last half month → `--period 14d`
   - 最近一个月 / last month → `--period 30d`
   - Exact dates → `--start YYYY-MM-DD --end YYYY-MM-DD`
4. Prefer an explicit Prompt/Topic ID when supplied. Otherwise pass the exact text; supported GEO-Api versions resolve it inside the single report-data business request.
5. Run exactly one report command. If the scenario's default format is HTML, generating and delivering that HTML in the same turn is mandatory: do not answer from a specialist read script, do not stop at a prose summary, do not ask whether the user also wants a report, and do not wait for a second request. Do not repeat the same query with a specialist script to create a summary.
6. For HTML output, follow **WorkBuddy HTML artifact delivery** below. Put the clickable `REPORT_LINK` in the final reply before any summary, then use up to three `REPORT_FINDING` and `REPORT_NEXT` lines.
7. Use 40 rows per page by default. For “next page / 下一页”, increment `--page` and keep `--limit 40`.

Use the scenario's default output policy. Analysis, trend, inventory, and multi-source reports default to offline HTML. Project lists and small single-record results (`projects`, `account-info`, `worker-deployment`, `saas-task`, and `opportunity-detail`) default to inline Markdown. An explicit user request for HTML, inline output, or raw JSON always overrides the scenario default.

## WorkBuddy HTML artifact delivery

Apply this protocol whenever the resolved output format is `html` or `both`:

1. Run the report from the user's current task workspace. Pass
   `--output-dir "<task-workspace>/adgine-reports"` when the current directory
   is the installed Skill directory or any directory outside that workspace.
2. Read `REPORT_FILE`, `REPORT_PREVIEW`, and `REPORT_LINK` from the same command
   output. Verify that `REPORT_FILE` exists and is inside the task workspace. If
   not, rerun once with the explicit workspace output directory.
3. If WorkBuddy exposes an artifact/preview presentation facility, present
   `REPORT_PREVIEW` with it. Treat this as an optional UI enhancement.
4. Start the final reply with the `REPORT_LINK` line exactly as emitted by the
   script. If `REPORT_LINK` is unavailable, construct
   `[打开 HTML 报告](<REPORT_FILE absolute path>)` for Chinese or
   `[Open HTML report](<REPORT_FILE absolute path>)` for English.
5. Always keep that link in the final reply, even when WorkBuddy successfully
   displays a native artifact card or preview panel. Never replace it with only
   “the report is open in Preview.”
6. Say that Preview was opened only after the presentation facility reports
   success. Otherwise say only that the report was generated; the clickable
   link is the guaranteed fallback.
7. If the file does not exist or cannot be delivered, report the failure
   instead of claiming that an HTML report was generated.

After the link, summarize at most three `REPORT_FINDING` lines and offer at
most three `REPORT_NEXT` prompts. Do not rerun the data query for the summary.

```bash
python3 <skill-dir>/scripts/report.py visibility --project-id <id> --period 7d --locale en-US
python3 <skill-dir>/scripts/report.py topic-detail --project-id <id> --topic "主题名称" --period 14d --locale zh-CN
python3 <skill-dir>/scripts/report.py prompt-performance --project-id <id> --prompt "exact prompt text" --period 7d --locale en-US
python3 <skill-dir>/scripts/report.py page-opportunities --project-id <id> --path /blog/example --period 30d --locale en-US
python3 <skill-dir>/scripts/report.py ga4-overview --project-id <id> --period 30d --locale en-US
python3 <skill-dir>/scripts/report.py traffic-overview --project-id <id> --period 14d --locale en-US
python3 <skill-dir>/scripts/report.py data-freshness --project-id <id> --locale en-US
python3 <skill-dir>/scripts/report.py operations-overview --project-id <id> --locale en-US
python3 <skill-dir>/scripts/report.py account-info --locale en-US
```

## Scenario routing

Use these report names:

- Core GEO: `executive-overview`, `catalog`, `visibility`, `matrix`, `topics`, `topic-detail`, `topic-lifecycle`, `prompt-performance`, `prompt-executions`, `citations`, `sentiment`.
- Acquisition and bots: `traffic-overview`, `ga4-overview`, `ga4-referrals`, `ga4-pages`, `cloudflare-overview`, `cloudflare-bots`, `cloudflare-pages`, `worker-traffic`, `worker-pages`, `worker-events`, `worker-deployment`, `ai-overview`, `ai-bots`, `ai-humans`.
- Pages and flows: `ai-pages`, `ai-flow`, `human-flow`, `ga4-flow`, `page-detail`, `page-health`, `page-opportunities`.
- Operations: `account-info`, `data-freshness`, `operations-overview`, `opportunities`, `opportunity-detail`, `content-pipeline`, `content-detail`, `brand-profile`, `brand-jobs`, `integration-health`, `wordpress-publications`, `wordpress-publishable`, `billing`, `projects`, `domains`, `saas-task`.

Run `python3 <skill-dir>/scripts/report.py --list-scenarios` for the machine-readable catalog. Read `references/scenarios.md` when intent overlaps multiple reports or when an entity argument is unclear.

## Query and safety rules

- Treat the script's explicit end date as the source of truth. The default is yesterday to avoid partial same-day traffic.
- Keep concurrent calls at the script's built-in maximum of four. Preserve request memoization and optional-source partial failure behavior.
- Never add GA4 sessions/users, Cloudflare HTTP requests, Worker events, or AI Agent event counts. Present each source and unit separately.
- Never trigger GA4/Cloudflare sync, PageSpeed refresh, citation tests, content generation, publication, deployment, billing, or any other mutation from a report.
- Use cached PageSpeed data in reports. If absent, state that the report is unavailable and offer an explicit refresh as a separate action.
- Hide internal IDs by default. Use `--show-ids` only for debugging or an explicit user request. Never expose passwords, tokens, API keys, or secrets.
- Preserve zero values. Render missing values as `—`; do not infer a zero from missing data.
- Report partial data honestly through coverage, warnings, and source status.
- Cache only `/report-data/capabilities` for two hours on disk without credentials; never cache report business data. Fall back only for a missing/disabled/incompatible report-data route; never hide 401/403/409/422 or business 5xx failures behind legacy calls.
- Treat answer citations, AI-assistant HTTP requests, Worker events, and GA4 AI landing sessions as distinct facts even when they refer to the same page.
- Do not infer page-to-opportunity matches. Until the backend persists `target_path/path_key`, show `PAGE_OPPORTUNITY_MAPPING_UNAVAILABLE` and use only deterministic KPI/health recommendations.
- Account reports may show only the authenticated user's `created_at`, `name`, `phone`, and `email`; do not include user ID, rules, tokens, subscription/credits information, subscription-related follow-up prompts, or unrelated `/auth/me` fields.

Read `references/reporting.md` before changing output behavior, templates, schema fields, chart mapping, or WorkBuddy markers.

## Output controls

```bash
# Scenario default: standalone HTML for analysis and inventory reports
python3 <skill-dir>/scripts/report.py executive-overview --project-id <id> --period 30d

# Scenario default: inline Markdown for small single-record results
python3 <skill-dir>/scripts/report.py account-info

# Project lists also stay inline by default
python3 <skill-dir>/scripts/report.py projects --locale zh-CN

# Alternative representations
python3 <skill-dir>/scripts/report.py account-info --format html
python3 <skill-dir>/scripts/report.py topics --project-id <id> --format markdown
python3 <skill-dir>/scripts/report.py topics --project-id <id> --format json
python3 <skill-dir>/scripts/report.py topics --project-id <id> --format both

# Fully localized Chinese report chrome, labels, findings, and actions
python3 <skill-dir>/scripts/report.py visibility --project-id <id> --locale zh-CN --timezone Asia/Shanghai
```

Support deterministic `en-US` and `zh-CN` presentation. Keep raw Topic/Prompt names, URLs, API values, and user content unchanged; localize only report UI labels and deterministic narrative text. Unsupported locales fall back to `en-US`.

Keep `assets/report-template.html` standalone: no CDN, remote font, remote script, or network dependency.
Treat every HTML artifact as customer-facing material that may be shared with a prospect. Keep the page title, browser title, subtitle, chart titles, descriptions, legends, and findings concise and self-explanatory; never expose backend container names or implementation terminology.
