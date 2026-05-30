# adgine-geo-site-audit

Agent-driven GEO (Generative Engine Optimization) audit skill: 5 dimensions,
30 compressed strict v3 checks, optional AI visibility/citation sampling, and PDF
export.

This skill is intended to be integrated into
[`adgine-ai/adgine-geo-skills`](https://github.com/adgine-ai/adgine-geo-skills)
as `adgine-geo-site-audit/`. The narrower name keeps it distinct from platform
API skills such as `adgine-geo-performance`, `adgine-geo-visibility`,
`adgine-geo-analytics`, and `adgine-geo-citation`.

## Architecture

```
Python collector              Agent judgment              Deterministic scorer
┌─────────────────┐   JSON    ┌────────────────────┐      ┌─────────────────┐
│ geo_collect.py  │ ───────→  │ 30 item statuses   │ ───→ │ geo_score.py    │
│ public signals  │           │ evidence + notes   │      │ score + caps    │
│ 20-page sample  │           │                    │      │                 │
└─────────────────┘           └────────────────────┘      └─────────────────┘
```

`scripts/geo_score.py` is the single source of truth for the evaluation table:
dimension weights, item points, status coefficients, and cap rules.

## Dimensions

| Dimension | Weight | Items | Focus |
|---|---:|---:|---|
| 维度一：AI 可发现 | 25% | 7 | crawler discovery, access, indexability, rendering |
| 维度二：AI 可理解 | 20% | 7 | metadata, headings, information architecture, schema |
| 维度三：AI 可引用 | 20% | 5 | quotable answers, content formats, evidence, density |
| 维度四：AI 可信任 | 20% | 5 | entity clarity, trust pages, third-party validation |
| 维度五：AI 可推荐 | 15% | 6 | topical authority, decision assets, conversion paths |

## Quick Start

```bash
pip install -r requirements.txt
python scripts/geo_collect.py https://example.com --max-subpages 20 --concurrency 6 --output ./signals.json
python scripts/geo_score.py validate
```

The agent reads `SKILL.md`, evaluates all 30 items from the collected evidence,
then scores the structured assessment:

```bash
python scripts/geo_score.py score ./assessment.json \
  --output ./score-results.json \
  --report ./score-report.md
```

Windows PowerShell:

```powershell
py -m pip install -r requirements.txt
py scripts\geo_collect.py https://example.com --max-subpages 20 --concurrency 6 --output .\signals.json
py scripts\geo_score.py validate
py scripts\geo_score.py score .\assessment.json `
  --output .\score-results.json `
  --report .\score-report.md
```

Assessment JSON shape:

```json
{
  "items": {
    "1.1": {"status": "PASS", "note": "HTTPS 可用，入口统一。"},
    "1.2": {"status": "WARN", "note": "robots 可访问，但缺少 llms.txt。"}
  }
}
```

## Scoring

| Status | Badge | Coefficient | Meaning |
|---|---|---:|---|
| PASS | ✅ PASS | 1.0 | Meets standard |
| WARN | ⚠️ WARN | item-specific | Needs improvement |
| FAIL | ❌ FAIL | 0.0 | Does not meet standard |
| ERROR | 🔴 ERROR | excluded | Detection failed |
| N/A | ➖ N/A | excluded | Not applicable to the business model |

Formula:

`dimension_score = floor(Σ(item_points × coefficient) / Σ(effective_item_points) × 100)`

`GEO score = floor(Σ(dimension_score × dimension_weight))`

`WARN` uses each item's own strict-v3 coefficient, commonly 20%, 30%, 40%,
50%, or 60%. `ERROR` and `N/A` are excluded from the effective denominator and
the dimension is normalized back to 100.

Caps apply to severe blockers:

- AI 可发现: failures in AI crawler accessibility, indexability, or error-page
  fallback cap the dimension at 55 or 35.
- AI 可引用: failures in quotable answer capability and evidence support cap the
  dimension at 65, 45, or 35.
- AI 可信任: failures in verifiable brand entity/contact or compliance/security
  transparency cap the dimension at 55 or 35.
- AI 可推荐: failures in platform/search-intent coverage, topical authority, or
  conversion landing pages cap the dimension at 60 or 45.
- Cross-dimension caps apply when crawler accessibility or error-page fallback
  fails. P0 technical blockers also cap the final score at 70 or 62.

## Optional AI Visibility / Citation Sampling

The normal audit flow does not run or mention isolated sub-agent visibility
sampling. Run it only when the user explicitly asks for AI visibility,
AI citation, or brand-in-answer sampling. This output is an optional reference
section only and does not participate in the GEO score.

Prepare prompts:

```bash
python scripts/geo_visibility.py prepare ./signals.json --output ./visibility-plan.json
```

The generated plan includes `subagent_concurrency_limit: 5` and
`subagent_batches`. The agent sends each `subagent_tasks` entry to one isolated
sub-agent, with no more than 5 sub-agents running at once. Sub-agents receive
only the raw prompt and output schema, not the brand profile, audit JSON, or
parent-agent conclusions.

After collecting sub-agent answers:

```bash
python scripts/geo_visibility.py score ./visibility-plan.json ./visibility-answers.json \
  --output ./visibility-results.json \
  --report ./visibility-report.md
```

Product and use-case terms are extracted from the audited site's own public
content and URL slugs. The visibility module does not use a fixed product
keyword list, so prompts are less biased toward finance, payments, or SaaS
examples.

## Collection Performance

The collector samples up to 20 sub-pages by default. Raising the sample size
improves coverage but can increase runtime on slow sites; use
`--max-subpages` to tune it per run.

Sub-page sampling combines sitemap order with GEO-specific priority. The
homepage is fetched separately first. If sitemap page URLs exist, they are used
as the candidate pool; if sitemap is missing or empty, same-origin homepage
links are used as the fallback pool. Candidates are selected in this order: core
conversion pages, core trust pages, citation-ready pages, one page per
important residual template, technical entry URLs, and finally high-risk
validation URLs such as component/search/fallback/404-like paths.

Time-saving defaults:

- Sitemap discovery first uses robots-declared sitemap URLs, then falls back to
  common sitemap locations only when the declared paths fail. Child sitemap
  indexes are followed in bounded parallel batches. If no sitemap page URLs are
  available, homepage same-origin links are used for sub-page sampling without
  marking the sitemap itself as healthy.
- AI/search crawler UA probes run in parallel.
- Sitemap sub-page fetches run in parallel with a default concurrency of 6.
- Wikipedia and Wikidata probes run concurrently.
- The 404 probe remains mandatory because it feeds soft-404 and 404-index
  conflict scoring; it runs in the resource-discovery batch and is timed as
  `meta.timings.notfound_probe_seconds`.

Reports do not display generation duration for now. Detailed debug timings are stored in `meta.timings` inside the collector JSON.
`geo_score.py` and `geo_visibility.py` also write `timings` to their output JSON.
For PDF export, pass `--timings-output ./pdf-timings.json` when you need a
debug trace of Markdown rendering and PDF engine time.

To summarize timing without slowing down the audit, run `scripts/geo_timing.py`
once at the end. It reads existing artifact timings instead of adding start/stop
commands around every phase:

```bash
python scripts/geo_collect.py https://example.com --max-subpages 20 --concurrency 6 --output ./signals.json
# agent generates assessment.json
python scripts/geo_score.py score ./assessment.json --output ./score-results.json --report ./score-report.md

python scripts/geo_timing.py artifacts \
  --label example.com \
  --collect-json ./signals.json \
  --score-json ./score-results.json \
  --output ./timing-summary.json \
  --report ./timing-summary.md
```

If the optional AI visibility/citation sampling ran, add
`--visibility-plan-json ./visibility-plan.json` and
`--visibility-results-json ./visibility-results.json`.

If the UI exposes elapsed time, pass it as `--ui-elapsed-seconds <seconds>` and
the summary reports the remaining untracked agent/UI overhead. The legacy
`start`/`mark` ledger mode still exists for deep debugging, but it should not be
used in the default audit flow because marker commands themselves add overhead.

## PDF Export

After the agent generates a Markdown report, save it to a `.md` file and render
it to PDF:

```bash
TEMP_DIR="${TMPDIR:-/tmp}"
python scripts/render_report_pdf.py "$TEMP_DIR/geo_audit_reports/example.md" \
  --output "$TEMP_DIR/geo_audit_reports/example.pdf"
```

Windows PowerShell:

```powershell
py scripts\render_report_pdf.py $env:TEMP\geo_audit_reports\example.md `
  --output $env:TEMP\geo_audit_reports\example.pdf
```

The renderer defaults to the pure-Python ReportLab path, so normal PDF export
does not launch Chrome/Chromium in background agent environments. Use
`--keep-html` to preserve intermediate HTML for debugging. Use
`--engine playwright` or `--engine chrome` only when browser rendering is
explicitly required; `--engine auto` tries ReportLab first, then browser
engines.

To install Playwright into the Python environment that runs this script, pass
`--install-playwright` once:

```bash
python scripts/render_report_pdf.py "$TEMP_DIR/geo_audit_reports/example.md" \
  --output "$TEMP_DIR/geo_audit_reports/example.pdf" \
  --engine playwright \
  --install-playwright
```

Set `GEO_AUDIT_PLAYWRIGHT_EXECUTABLE_PATH=/path/to/chrome` if Playwright's
default bundled browser is blocked. Set `GEO_AUDIT_CHROME_PATH=/path/to/chrome`
to force a Chrome/Chromium/Edge binary.

## Skill Package Export

Create a portable zip package for installing or moving this skill:

```bash
python scripts/export_skill_package.py
```

By default the script writes `dist/adgine-geo-site-audit-<timestamp>.zip` and
stores files under the top-level `adgine-geo-site-audit/` directory inside the
zip. It includes `SKILL.md`, `README.md`, `requirements.txt`, `scripts/*.py`,
and `tests/*.py`, while excluding `.git`, `dist`, Python caches, pyc files, and
local run artifacts.

Runtime-only package:

```bash
python scripts/export_skill_package.py --no-tests --output dist/adgine-geo-site-audit-runtime.zip
```

## Usage with Agent

Tell your agent:

> 审计 longbridge.com

The agent will:

1. Run `geo_collect.py` to collect public signals.
2. Judge all 30 score-table items with evidence-backed notes.
3. Run `geo_score.py score` to calculate dimension scores, caps, and GEO score.
4. Generate a Markdown report and ask whether to export PDF.

If the user explicitly asks to add AI visibility/citation sampling, the agent
runs `geo_visibility.py` and inserts the optional reference section before
prioritized recommendations.

## Dependencies

- Python 3.9+ on macOS/Linux/Windows
- requests, beautifulsoup4, lxml, markdown, reportlab
- Chrome/Chromium/Edge or Playwright Chromium, optional for SPA rendering and
  high-fidelity PDF export
