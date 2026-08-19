# GEO report-data implementation contract

This is the versioned consumer contract for GEO-Api schema `1.0`. The backend implementation lives in `/Users/thunder/code/GEO-Api/src/geo/report_data/`; the facade consumer lives in `adgine-geo-reports/scripts/`.

## Endpoint surface

Prefix: `/api/projects/{id}/report-data`

| Feature | Endpoint | Facade scenarios |
|---|---|---|
| `executive_overview` | `/executive-overview` | `executive-overview` |
| `topic_performance` | `/topic-performance` | `topic-detail`, `topic-lifecycle` |
| `prompt_performance` | `/prompt-performance` | `prompt-performance`, `prompt-executions` |
| `traffic_overview` | `/traffic-overview` | `traffic-overview` |
| `pages` | `/pages` | `ai-pages` |
| `page_detail` | `/page-detail` | `page-detail`, `page-opportunities` |
| `data_freshness` | `/data-freshness` | `data-freshness` |
| `content_pipeline` | `/content-pipeline` | `content-pipeline` |
| `operations_overview` | `/operations-overview` | `operations-overview` |

`/capabilities` exposes these keys one-to-one.

## Stable decisions

- Schema version `1.0`; maximum range 366 days.
- Default page size 40. Normal maximum is 100; `/pages` uses offset/limit and a maximum of 200.
- Topic/Prompt text is trimmed and exact case-insensitive. Ambiguity returns `40907` with at most 10 candidates; not found remains `40405`/`40406`.
- Visibility dashboard parity uses `created_at`; Topic/Prompt performance uses `analyzed_at` and publishes the date basis.
- Warnings are structured objects; units are metric-level objects; timestamps are UTC.
- Optional integration absence is `unavailable`, not partial. Optional query failure is HTTP 200 with `partial=true`; required citation failure is `50304`.
- GA4, Cloudflare, Worker, assistant HTTP requests, and answer citations stay source-separated and are never summed into a grand total.
- Page keys remove query/fragment, collapse duplicate slashes, add a leading slash, remove non-root trailing slash, preserve case, and do not percent-decode. Full URLs must belong to the project host.
- Page opportunities remain empty with `PAGE_OPPORTUNITY_MAPPING_UNAVAILABLE` until `target_path/path_key` is persisted.
- Content returns latest versions per language, nullable publish status when no version exists, one latest active job plus its count, and no large workflow internals.
- Operations uses a strict public whitelist and never exposes credentials, secrets, passwords, full integration `extra_data`, or token expiry.
- Migration `089_report_data_indexes` adds partial indexes for high-frequency analyzed CitationTest reads.

## Facade switching

- Only capabilities are cached for two hours on disk without credential material; report business data is never cached by the facade. `GEO_REPORT_CAPABILITY_CACHE_TTL_SECONDS` may override the TTL during rollout.
- Capability/route 404 or 501, `feature=false`, and unsupported schema may use existing live endpoints.
- 401/403, entity 404, 409, 422, business 5xx, and business timeouts never silently fall back.
- Capability discovery failure may use stale cache; without cache, legacy mode carries an explicit audit warning.

Account information remains on `/api/auth/me` and is intentionally outside report-data.
