#!/usr/bin/env python3
"""Generate stable, auditable GEO reports from the current GEO-Api contracts."""

import argparse
import copy
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(__file__))
from _client import ApiError, api_get, get_api_config, get_project_id, print_json  # noqa: E402
from _capabilities import discover_capabilities, supports  # noqa: E402
from _contracts import SCENARIOS, get_scenario, scenario_rows  # noqa: E402
from _reporting import now_iso, render_markdown, write_html  # noqa: E402


INTERNAL_KEYS = {
    "id", "project_id", "topic_id", "prompt_id", "execution_id", "competitor_id",
    "content_id", "job_id", "record_id", "task_id", "brand_relation_id",
}
SENSITIVE_KEY_PARTS = ("password", "secret", "api_key", "api_token", "access_token", "refresh_token")
DATE_KEYS = ("date", "day", "timestamp", "occurred_at", "created_at", "analyzed_at")
PREFERRED_COLUMNS = (
    "name", "title", "content", "path", "page_path", "landing_page", "platform",
    "source", "channel", "status", "type", "traffic_type", "bot_name",
    "visibility_score", "share_of_voice", "average_position", "current", "change",
    "requests", "sessions", "active_users", "page_views", "visits", "revenue",
    "transactions", "conversion_rate", "score", "rank", "created_at", "updated_at",
)
SOURCE_UNITS = {
    "visibility": "percent / rank",
    "matrix": "percent",
    "topics": "percent / rank",
    "prompt": "percent / rank",
    "executions": "executions",
    "citations": "citations / percent",
    "sentiment": "responses / percent",
    "ga4": "sessions / users / page views",
    "referrals": "sessions / users / page views",
    "cloudflare": "HTTP requests / bytes",
    "bots": "HTTP requests",
    "worker": "Worker events",
    "worker_pages": "Worker events by page",
    "worker_events": "Worker events",
    "worker_deployment": "deployment state",
    "traffic": "source-separated events and sessions",
    "overview": "events / sessions (source-specific)",
    "kpi": "events",
    "health": "PageSpeed score / Web Vitals",
    "opportunities": "opportunity records",
    "content": "content records",
    "jobs": "job records",
    "integrations": "connection states",
    "credits": "credits",
    "subscription": "subscription state",
    "plans": "plan catalog",
    "account": "account profile fields",
}

DEFAULT_PAGE_SIZE = 40

REPORT_DATA_SCENARIOS = {
    "executive-overview": ("executive_overview", "executive-overview"),
    "topic-detail": ("topic_performance", "topic-performance"),
    "topic-lifecycle": ("topic_performance", "topic-performance"),
    "prompt-performance": ("prompt_performance", "prompt-performance"),
    "prompt-executions": ("prompt_performance", "prompt-performance"),
    "traffic-overview": ("traffic_overview", "traffic-overview"),
    "ai-pages": ("pages", "pages"),
    "page-detail": ("page_detail", "page-detail"),
    "page-opportunities": ("page_detail", "page-detail"),
    "data-freshness": ("data_freshness", "data-freshness"),
    "content-pipeline": ("content_pipeline", "content-pipeline"),
    "operations-overview": ("operations_overview", "operations-overview"),
}


class ReportClient:
    """Read-only API wrapper with memoization, timings, and partial failures."""

    def __init__(self, key, base, project_id=None):
        self.key = key
        self.base = base
        self.project_id = project_id
        self.calls = []
        self.cache = {}

    @staticmethod
    def _cache_key(path, params):
        frozen = json.dumps(params or {}, ensure_ascii=False, sort_keys=True, default=str)
        return path, frozen

    def get(self, path, params=None):
        cache_key = self._cache_key(path, params)
        if cache_key in self.cache:
            return copy.deepcopy(self.cache[cache_key])
        started = time.perf_counter()
        call = {"path": path, "duration_ms": 0, "status": "ok"}
        try:
            result = api_get(
                path, self.key, self.base, params=params, timeout=40,
                exit_on_error=False,
            )
            if isinstance(result, dict) and result.get("code") not in (None, 0):
                raise ApiError(result.get("message") or "API request failed", payload=result)
            data = result.get("data", result) if isinstance(result, dict) else result
            self.cache[cache_key] = copy.deepcopy(data)
            return data
        except ApiError as exc:
            call["status"] = f"error:{exc.status_code or 'network'}"
            call["error"] = str(exc)
            raise
        finally:
            call["duration_ms"] = round((time.perf_counter() - started) * 1000)
            self.calls.append(call)

    def fetch_all(self, path, params=None, paging="page", limit=DEFAULT_PAGE_SIZE, max_items=1000):
        base_params = dict(params or {})
        output = []
        cursor = 0 if paging == "offset" else 1
        while len(output) < max_items:
            query = dict(base_params)
            if paging == "offset":
                query.update({"offset": cursor, "limit": limit})
            elif paging == "page_size":
                query.update({"page": cursor, "page_size": limit})
            else:
                query.update({"page": cursor, "limit": limit})
            payload = self.get(path, query)
            if isinstance(payload, list):
                items, total = payload, len(payload)
            else:
                payload = payload or {}
                items = _first_list(payload, ("items", "topics", "prompts", "rows", "results"))
                total = payload.get("total")
            output.extend(items)
            if not items or len(items) < limit or (total is not None and len(output) >= int(total)):
                break
            cursor = cursor + limit if paging == "offset" else cursor + 1
        return {"items": output[:max_items], "total": total if total is not None else len(output)}


def _first_list(payload, keys):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _platforms(raw_values):
    output = []
    for raw in raw_values or []:
        output.extend(part.strip() for part in raw.split(",") if part.strip())
    return list(dict.fromkeys(output))


def _window(args):
    end = date.fromisoformat(args.end) if args.end else date.today() - timedelta(days=1)
    if args.start:
        start = date.fromisoformat(args.start)
    else:
        days = int(args.period.rstrip("d"))
        start = end - timedelta(days=days - 1)
    if start > end:
        raise ValueError("--start must be earlier than or equal to --end")
    return start.isoformat(), end.isoformat()


def _analytics_params(args, start, end):
    params = {"date_from": start, "date_to": end, "granularity": args.granularity}
    platforms = _platforms(args.platform)
    if platforms:
        params["platform"] = platforms
    return params


def _traffic_params(args, start, end, accepts_platform=False):
    params = {"start_date": start, "end_date": end}
    platforms = _platforms(args.platform)
    if accepts_platform and platforms:
        params["platform"] = platforms[0]
    return params


def _resolve_topic(client, reference, analytics_params):
    payload = client.get(
        f"/api/projects/{client.project_id}/analytics/topics", analytics_params,
    ) or {}
    items = _first_list(payload, ("items", "topics"))
    lowered = reference.strip().casefold()
    matches = [
        item for item in items
        if str(item.get("topic_id") or item.get("id") or "").casefold() == lowered
        or str(item.get("name") or item.get("topic") or "").casefold() == lowered
    ]
    if not matches:
        raise ValueError(f"Topic not found: {reference}")
    if len(matches) > 1:
        raise ValueError(f"Topic name is ambiguous; use its ID: {reference}")
    topic = matches[0]
    topic["id"] = topic.get("topic_id") or topic.get("id")
    return topic


def _resolve_prompt(client, args, analytics_params):
    if args.prompt_id:
        return {"id": args.prompt_id, "content": args.prompt or "Selected prompt"}, "explicit ID"
    reference = (args.prompt or "").strip()
    if reference and re.fullmatch(r"[0-9a-fA-F-]{32,36}", reference):
        return {"id": reference, "content": "Selected prompt"}, "ID in --prompt"
    if args.topic:
        topic = _resolve_topic(client, args.topic, analytics_params)
        payload = client.fetch_all(
            f"/api/projects/{client.project_id}/topics/{topic['id']}/prompts",
            paging="page", limit=DEFAULT_PAGE_SIZE,
        )
        items = payload["items"]
        if reference:
            exact = [item for item in items if str(item.get("content") or "").casefold() == reference.casefold()]
            partial = [item for item in items if reference.casefold() in str(item.get("content") or "").casefold()]
            matches = exact or partial
            if len(matches) != 1:
                raise ValueError(f"Prompt text matched {len(matches)} records; provide --prompt-id")
            return matches[0], f"resolved within Topic {topic.get('name')}"
        ordered = sorted(items, key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")))
        if args.prompt_index < 1 or args.prompt_index > len(ordered):
            raise ValueError(f"--prompt-index is out of range (1..{len(ordered)})")
        return ordered[args.prompt_index - 1], f"Topic prompt #{args.prompt_index}, created_at ASC"
    if not reference:
        raise ValueError("Prompt reports require --prompt-id, --prompt, or --topic with --prompt-index")
    payload = client.fetch_all(
        f"/api/projects/{client.project_id}/prompts", paging="page", limit=DEFAULT_PAGE_SIZE,
    )
    items = payload["items"]
    exact = [item for item in items if str(item.get("content") or "").casefold() == reference.casefold()]
    partial = [item for item in items if reference.casefold() in str(item.get("content") or "").casefold()]
    matches = exact or partial
    if len(matches) != 1:
        raise ValueError(f"Prompt text matched {len(matches)} records; provide --prompt-id")
    return matches[0], "resolved from project prompt catalog"


def _replace_query_values(value, values):
    if not isinstance(value, str):
        return value
    return value.format(**values)


def _request_params(spec, args, start, end, values):
    if spec.date_style == "analytics":
        params = _analytics_params(args, start, end)
        if not spec.accepts_platform:
            params.pop("platform", None)
    elif spec.date_style == "traffic":
        params = _traffic_params(args, start, end, spec.accepts_platform)
    elif spec.date_style == "dashboard-period":
        params = {"period": args.period}
    else:
        params = {}
    for key, value in spec.query.items():
        params[key] = _replace_query_values(value, values)
    if args.metric and spec.alias == "matrix":
        params["metric"] = "share_of_voice" if args.metric in ("sov", "share_of_voice") else "visibility_score"
    if spec.paging == "page":
        params.update({"page": args.page, "limit": args.limit})
    elif spec.paging == "page_size":
        params.update({"page": args.page, "page_size": args.limit})
    elif spec.paging == "offset":
        params.update({"offset": (args.page - 1) * args.limit, "limit": args.limit})
    return params


def _fetch_spec(client, scenario, spec, args, start, end, values):
    path = spec.path.format(**values)
    params = _request_params(spec, args, start, end, values)
    return client.get(path, params or None)


def _fetch_scenario(client, scenario, args, start, end, values):
    payloads, errors = {}, {}
    workers = min(4, max(1, len(scenario.requests)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_fetch_spec, client, scenario, spec, args, start, end, values): spec
            for spec in scenario.requests
        }
        for future in as_completed(futures):
            spec = futures[future]
            try:
                payloads[spec.alias] = future.result()
            except (ApiError, ValueError) as exc:
                errors[spec.alias] = str(exc)
                payloads[spec.alias] = None
    required_errors = [f"{spec.alias}: {errors[spec.alias]}" for spec in scenario.requests if spec.required and spec.alias in errors]
    if required_errors:
        raise ValueError("; ".join(required_errors))
    return payloads, errors


def _looks_like_uuid(value):
    return bool(value and re.fullmatch(r"[0-9a-fA-F-]{32,36}", str(value).strip()))


def _native_params(scenario, args, start, end, client, analytics_params):
    params = {}
    if scenario.name not in ("data-freshness", "content-pipeline", "operations-overview"):
        params.update({"date_from": start, "date_to": end})
    platforms = _platforms(args.platform)
    if platforms:
        params["platform"] = platforms if scenario.name in (
            "executive-overview", "topic-detail", "topic-lifecycle",
            "prompt-performance", "prompt-executions", "traffic-overview",
        ) else platforms[0]
    entity = resolution = None
    if scenario.name in ("executive-overview", "topic-detail", "topic-lifecycle"):
        params["granularity"] = args.granularity
    if scenario.name in ("topic-detail", "topic-lifecycle"):
        if _looks_like_uuid(args.topic):
            params["topic_id"] = args.topic.strip()
            resolution = "Topic ID sent directly to /report-data/topic-performance"
        else:
            params["q"] = args.topic.strip()
            resolution = "exact Topic name resolved by /report-data/topic-performance"
        params.update({"limit": args.limit, "offset": (args.page - 1) * args.limit})
        if scenario.name == "topic-lifecycle":
            params["include_lifecycle"] = True
        entity = {"name": args.topic}
    if scenario.name in ("prompt-performance", "prompt-executions"):
        reference = args.prompt_id or args.prompt
        if not reference and args.topic:
            resolved, resolution = _resolve_prompt(client, args, analytics_params)
            reference = resolved.get("id") or resolved.get("prompt_id")
            entity = resolved
        else:
            entity = {"content": args.prompt or "Selected prompt"}
        if _looks_like_uuid(reference):
            params["prompt_id"] = str(reference).strip()
            resolution = resolution or "Prompt ID sent directly to /report-data/prompt-performance"
        else:
            params["q"] = str(reference).strip()
            resolution = "exact Prompt text resolved by /report-data/prompt-performance"
        params["include_executions"] = scenario.name == "prompt-executions"
        params.update({"execution_limit": args.limit, "execution_offset": (args.page - 1) * args.limit})
    if scenario.name == "ai-pages":
        params.update({"limit": args.limit, "offset": (args.page - 1) * args.limit})
    if scenario.name in ("page-detail", "page-opportunities"):
        params["path"] = args.path
        entity = {"name": args.path}
    if scenario.name == "content-pipeline":
        params.update({"page": args.page, "limit": args.limit})
    if scenario.name == "operations-overview":
        params["publication_limit"] = args.limit
    return params, entity, resolution


def _native_payloads(scenario, data):
    if scenario.name == "page-opportunities":
        return {
            "kpi": data,
            "health": data.get("health") or {},
            "opportunities": {"items": data.get("opportunities") or []},
        }
    return {"report_data": data}


def _try_report_data(client, scenario, args, start, end, analytics_params):
    mapping = REPORT_DATA_SCENARIOS.get(scenario.name)
    if not mapping:
        return None
    capabilities, warning = discover_capabilities(client)
    feature, endpoint = mapping
    if not supports(capabilities, feature):
        fallback = warning or f"Report-data feature {feature} is disabled; legacy API workflow used."
        return {"used": False, "warning": fallback}
    params, entity, resolution = _native_params(
        scenario, args, start, end, client, analytics_params,
    )
    path = f"/api/projects/{client.project_id}/report-data/{endpoint}"
    try:
        data = client.get(path, params or None) or {}
    except ApiError as exc:
        payload = exc.payload if isinstance(exc.payload, dict) else {}
        business_code = payload.get("code")
        if exc.status_code in (404, 501) and business_code not in (40405, 40406):
            return {
                "used": False,
                "warning": f"Report-data route {endpoint} is unavailable; legacy API workflow used.",
            }
        raise
    if data.get("schema_version") != "1.0":
        return {
            "used": False,
            "warning": "Report-data business response has an unsupported schema; legacy API workflow used.",
        }
    return {
        "used": True,
        "payloads": _native_payloads(scenario, data),
        "metadata": data,
        "entity": entity,
        "resolution": resolution,
        "warning": warning,
    }


def _label(key):
    special = {
        "ai": "AI", "ga4": "GA4", "sov": "Share of Voice", "avg": "Average",
        "pct": "%", "kpi": "KPI", "url": "URL", "utm": "UTM",
    }
    parts = str(key).replace("-", "_").split("_")
    return " ".join(special.get(part.lower(), part.capitalize()) for part in parts)


def _format_for(key, value=None):
    key = str(key).lower()
    if any(token in key for token in ("rate", "ratio", "share", "score", "percent", "pct")):
        return "percent"
    if "rank" in key:
        return "rank"
    if "byte" in key or "bandwidth" in key:
        return "bytes"
    if "duration" in key:
        return "seconds"
    if isinstance(value, int) or any(token in key for token in ("count", "requests", "sessions", "users", "views", "visits", "total")):
        return "integer"
    return None


def _direction(key, change):
    number = _numeric(change)
    if number in (None, 0):
        return ""
    lower_is_better = any(token in str(key).lower() for token in ("position", "rank", "bounce", "negative", "latency", "lcp", "cls", "inp"))
    good = number < 0 if lower_is_better else number > 0
    return "good" if good else "bad"


def _numeric(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _comparison_metric(key, value):
    current = value.get("current")
    change = value.get("change")
    if change is None:
        change = value.get("delta_pct") if value.get("delta_pct") is not None else value.get("delta")
    return {
        "label": _label(key), "value": current, "change": change,
        "format": _format_for(key, current), "direction": _direction(key, change),
        "note": value.get("unit"),
    }


def _collect_metrics(payloads, limit=8):
    metrics, seen = [], set()

    def add(key, value):
        if key in seen or len(metrics) >= limit:
            return
        if key in INTERNAL_KEYS or str(key).endswith("_id"):
            return
        if isinstance(value, dict) and "current" in value:
            metric = _comparison_metric(key, value)
        elif _numeric(value) is not None:
            metric = {"label": _label(key), "value": value, "format": _format_for(key, value)}
        else:
            return
        seen.add(key)
        metrics.append(metric)

    for payload in payloads.values():
        if not isinstance(payload, dict):
            continue
        kpis = payload.get("kpis")
        if isinstance(kpis, dict):
            for key, value in kpis.items():
                add(key, value)
        else:
            for item in kpis or []:
                if isinstance(item, dict):
                    add(item.get("key") or item.get("label") or "metric", item)
        for container_key in ("metrics", "summary", "distribution"):
            container = payload.get(container_key)
            if isinstance(container, dict):
                for key, value in container.items():
                    add(key, value)
        for key, value in payload.items():
            if key in ("total", "page", "limit", "pages", "period_days"):
                continue
            add(key, value)
    return metrics


def _series_from_list(name, points, color=None):
    if not isinstance(points, list) or not points:
        return []
    numeric_keys = []
    for point in points:
        if isinstance(point, dict):
            numeric_keys.extend(key for key, value in point.items() if key not in DATE_KEYS and _numeric(value) is not None)
    numeric_keys = list(dict.fromkeys(numeric_keys))[:4]
    output = []
    for key in numeric_keys:
        data = []
        for index, point in enumerate(points):
            if not isinstance(point, dict):
                continue
            x = next((point.get(date_key) for date_key in DATE_KEYS if point.get(date_key) is not None), index + 1)
            data.append({"x": x, "y": point.get(key)})
        output.append({"name": f"{name} · {_label(key)}", "points": data, "color": color})
    return output


def _collect_charts(payloads, scenario):
    charts = []
    matrix = payloads.get("matrix")
    if isinstance(matrix, dict):
        platforms = matrix.get("platforms") or []
        competitors = matrix.get("competitors") or matrix.get("rows") or []
        if platforms and competitors:
            charts.append({
                "type": "heatmap", "title": "Cross-platform comparison",
                "columns": [item.get("code") or item.get("name") if isinstance(item, dict) else item for item in platforms],
                "rows": [
                    {
                        "label": row.get("name") or row.get("brand"),
                        "values": row.get("values") or row.get("scores") or {},
                        "highlight": row.get("is_our_brand") or row.get("is_self"),
                    }
                    for row in competitors
                ],
                "format": "percent",
            })
    for alias, payload in payloads.items():
        if not isinstance(payload, dict) or len(charts) >= 5:
            continue
        comparison_series = []
        for key, value in payload.items():
            if isinstance(value, dict):
                metric_trend = value.get("trend") or value.get("daily")
            else:
                metric_trend = None
            if isinstance(metric_trend, list) and metric_trend:
                points = [{"x": item.get("date"), "y": item.get("value")} for item in metric_trend]
                comparison_series.append({"name": _label(key), "points": points})
        if comparison_series:
            charts.append({"type": "line", "title": f"{_label(alias)} trend", "series": comparison_series})
        kpi_series = []
        for item in payload.get("kpis") or []:
            if not isinstance(item, dict):
                continue
            metric_name = item.get("label") or item.get("key") or "KPI"
            kpi_series.extend(_series_from_list(str(metric_name), item.get("daily"))[:1])
            if len(kpi_series) >= 4:
                break
        if kpi_series and len(charts) < 5:
            charts.append({"type": "line", "title": f"{_label(alias)} KPI trend", "series": kpi_series[:4]})
        for key in ("daily", "trend", "prev_daily"):
            points = payload.get(key)
            series = _series_from_list(_label(alias), points)
            if series and len(charts) < 5:
                charts.append({"type": "line", "title": f"{_label(alias)} · {_label(key)}", "series": series})
        links = payload.get("links")
        if isinstance(links, list) and links and len(charts) < 5:
            items = sorted(links, key=lambda item: _numeric(item.get("value")) or 0, reverse=True)[:15]
            charts.append({
                "type": "bar", "title": f"{_label(alias)} · top flows",
                "items": [{"label": f"{item.get('source')} → {item.get('target')}", "value": item.get("value")} for item in items],
                "format": "integer",
            })
    return charts


def _public_keys(rows, show_ids=False):
    keys = []
    for preferred in PREFERRED_COLUMNS:
        if any(preferred in row for row in rows):
            keys.append(preferred)
    for row in rows:
        for key, value in row.items():
            if key.startswith("_") or key in keys:
                continue
            if not show_ids and (key in INTERNAL_KEYS or key.endswith("_id")):
                continue
            if key in (
                "response_text", "worker_js", "wp_password", "full_content",
                "article_body", "master_draft",
            ):
                continue
            if isinstance(value, str) and len(value) > 500:
                continue
            if isinstance(value, (dict, list)) and len(str(value)) > 300:
                continue
            keys.append(key)
            if len(keys) >= 10:
                return keys
    return keys[:10]


def _table(title, rows, show_ids=False, note=None):
    rows = [_sanitize(item, show_ids) for item in rows if isinstance(item, dict)]
    keys = _public_keys(rows, show_ids)
    columns = [
        {
            "key": key, "label": _label(key), "format": _format_for(key),
            "align": "right" if any(_numeric(row.get(key)) is not None for row in rows) else "left",
        }
        for key in keys
    ]
    public_rows = []
    for row in rows:
        clean = {}
        for key in keys:
            value = row.get(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            clean[key] = value
        if row.get("is_our_brand") or row.get("is_self"):
            clean["_highlight"] = True
        public_rows.append(clean)
    return {"title": title, "columns": columns, "rows": public_rows, "note": note}


def _payload_lists(payload):
    if isinstance(payload, list):
        return [("items", payload)]
    if not isinstance(payload, dict):
        return []
    output = []
    for key, value in payload.items():
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            if key in ("daily", "trend", "prev_daily", "previous_trend", "nodes"):
                continue
            output.append((key, value))
    if not output:
        for key in ("items", "rows", "pages", "topics", "prompts", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                output.append((key, value))
    return output


def _catalog_tables(payloads, show_ids):
    topics = _first_list(payloads.get("topics") or {}, ("items", "topics"))
    prompts = _first_list(payloads.get("prompts") or {}, ("items", "prompts"))
    topic_map = {str(item.get("id") or item.get("topic_id")): item.get("name") for item in topics}
    for index, item in enumerate(sorted(topics, key=lambda row: (str(row.get("created_at") or ""), str(row.get("id") or ""))), 1):
        item["ordinal"] = index
    counters = {}
    for item in sorted(prompts, key=lambda row: (str(row.get("created_at") or ""), str(row.get("id") or ""))):
        topic_id = str(item.get("topic_id") or "")
        counters[topic_id] = counters.get(topic_id, 0) + 1
        item["ordinal"] = counters[topic_id]
        item["topic"] = topic_map.get(topic_id) or "Unknown topic"
    return [_table("Topics", topics, show_ids), _table("Prompts", prompts, show_ids)]


def _lifecycle_table(payloads, show_ids):
    metadata = _first_list(payloads.get("prompt_metadata") or {}, ("items", "prompts"))
    analytics = _first_list(payloads.get("prompts") or {}, ("items", "prompts"))
    meta = {str(item.get("id") or item.get("prompt_id")): item for item in metadata}
    rows = []
    for item in analytics:
        prompt_id = str(item.get("prompt_id") or item.get("id") or "")
        row = {**meta.get(prompt_id, {}), **item}
        rows.append(row)
    rows.sort(key=lambda row: (str(row.get("created_at") or ""), str(row.get("prompt_id") or row.get("id") or "")))
    pivot = max(1, (len(rows) + 1) // 2)
    for index, row in enumerate(rows):
        row["cohort"] = "Initial" if index < pivot else "Later"
        row["ordinal"] = index + 1
    return _table("Prompt lifecycle cohorts", rows, show_ids, "Cohorts are deterministic halves ordered by created_at ASC; they are not causal attribution.")


def _account_table(payloads, show_ids):
    account = payloads.get("account") or {}
    rows = [
        {"field": "Created at", "value": account.get("created_at")},
        {"field": "Account name", "value": account.get("name")},
        {"field": "Phone", "value": account.get("phone")},
        {"field": "Email", "value": account.get("email")},
    ]
    return _table("Account information", rows, show_ids)


def _collect_tables(payloads, scenario, show_ids=False):
    if scenario.name == "catalog":
        return _catalog_tables(payloads, show_ids)
    if scenario.name == "topic-lifecycle":
        return [_lifecycle_table(payloads, show_ids)]
    if scenario.name == "account-info":
        return [_account_table(payloads, show_ids)]
    tables = []
    for alias, payload in payloads.items():
        payload_tables = _payload_lists(payload)
        for key, rows in payload_tables:
            if key == "kpis":
                continue
            tables.append(_table(f"{_label(alias)} · {_label(key)}", rows[:100], show_ids))
            if len(tables) >= 10:
                return tables
        if scenario.density in ("detail", "status") and isinstance(payload, dict):
            safe_payload = _sanitize(payload, show_ids)
            scalar_rows = []
            for key, value in safe_payload.items():
                if isinstance(value, list):
                    continue
                if isinstance(value, str) and len(value) > 500:
                    continue
                if isinstance(value, dict) and len(json.dumps(value, ensure_ascii=False, default=str)) > 500:
                    continue
                scalar_rows.append({"field": _label(key), "value": value})
            if scalar_rows:
                tables.insert(0, _table(f"{_label(alias)} · summary", scalar_rows, show_ids))
    return tables


def _page_opportunity_rules(payloads):
    findings, rows = [], []
    health = payloads.get("health") or {}
    report = health.get("report") if isinstance(health, dict) else None
    report = report or (health if isinstance(health, dict) else {})
    performance_score = report.get("performance_score")
    if performance_score is None:
        performance_score = report.get("performance")
    score = _numeric(performance_score)
    if score is None:
        rows.append({"priority": "Medium", "area": "Performance", "recommendation": "Generate or refresh PageSpeed data explicitly before prioritizing Core Web Vitals work."})
    elif score < 50:
        rows.append({"priority": "High", "area": "Performance", "recommendation": "Improve critical rendering and Core Web Vitals; cached performance score is below 50."})
    elif score < 90:
        rows.append({"priority": "Medium", "area": "Performance", "recommendation": "Review PageSpeed opportunities; cached performance score is below 90."})
    kpi = payloads.get("kpi") or {}
    values = kpi.get("kpis") if isinstance(kpi, dict) else {}
    values = values if isinstance(values, dict) else {}
    citation = values.get("ai_citation")
    citation = citation.get("current") if isinstance(citation, dict) else citation
    if _numeric(citation) == 0:
        rows.append({"priority": "High", "area": "AI citations", "recommendation": "Strengthen answer-ready claims, evidence, entity clarity, and internal links; no AI citation events were observed in the selected period."})
    training = values.get("ai_training")
    training = training.get("current") if isinstance(training, dict) else training
    if _numeric(training) == 0:
        rows.append({"priority": "Medium", "area": "Crawler access", "recommendation": "Check robots directives, crawlable HTML, sitemaps, and server responses for training crawlers."})
    opportunities = _first_list(payloads.get("opportunities") or {}, ("items", "opportunities"))
    findings.append(f"{len(rows)} deterministic page checks produced an action; {len(opportunities)} backend opportunities were available before path filtering.")
    return rows, findings


def _insights(metrics, tables, errors, scenario):
    if scenario.name == "account-info":
        return ["The authenticated account profile was loaded from GEO-Api."]
    output = []
    comparable = [item for item in metrics if _numeric(item.get("value")) is not None]
    changed = [item for item in comparable if _numeric(item.get("change")) not in (None, 0)]
    if changed:
        item = max(changed, key=lambda row: abs(_numeric(row.get("change"))))
        output.append(f"{item['label']} has the largest displayed period change ({item.get('change')}).")
    for table in tables:
        rows = table.get("rows") or []
        columns = table.get("columns") or []
        numeric = [column for column in columns if column.get("align") == "right"]
        label_cols = [column for column in columns if column.get("align") != "right"]
        if rows and numeric and label_cols:
            key = numeric[0]["key"]
            candidates = [row for row in rows if _numeric(row.get(key)) is not None]
            if candidates:
                leader = max(candidates, key=lambda row: _numeric(row.get(key)))
                output.append(f"{leader.get(label_cols[0]['key'])} leads {table.get('title')} on {numeric[0].get('label')}.")
                break
    if errors:
        output.append(f"The report is partial: {', '.join(errors)} unavailable.")
    if not output:
        output.append("The selected window contains insufficient comparable data for a deterministic trend finding.")
    return output[:3]


def _next_actions(scenario, args):
    actions = {
        "visibility": ["Compare visibility by AI platform", "Review the weakest Topic", "Inspect citation sources"],
        "topics": ["Open the lowest-visibility Topic", "Compare Topic prompt performance", "Review Topic citation sources"],
        "prompt-performance": ["Show this Prompt's execution history", "Compare this Prompt by platform", "Inspect its cited URLs"],
        "ai-pages": ["Open the leading page detail", "Show page-level optimization opportunities", "Compare bot and human traffic separately"],
        "page-detail": ["Generate deterministic opportunities for this page", "Inspect exact page event logs", "Compare related pages"],
        "content-pipeline": ["Inspect failed content jobs", "Open the latest content item", "Review WordPress publish readiness"],
        "account-info": ["Review my subscription and credits", "List my projects", "Show integration health"],
    }
    return actions.get(scenario.name, ["Compare a different time window", "Narrow the report by platform", "Open the most important row in detail"])[:3]


def _mask_path(path, show_ids=False):
    if show_ids:
        return path
    value = str(path)
    patterns = (
        (r"(/projects/)[^/?]+", r"\1<project>"),
        (r"(/topics/)[^/?]+", r"\1<topic>"),
        (r"(/prompts/)[^/?]+", r"\1<prompt>"),
        (r"(/opportunities/)[^/?]+", r"\1<opportunity>"),
        (r"(/content/)[^/?]+", r"\1<content>"),
        (r"(/task/)[^/?]+", r"\1<task>"),
    )
    for pattern, replacement in patterns:
        value = re.sub(pattern, replacement, value)
    return value


def _sanitize(value, show_ids=False):
    if isinstance(value, dict):
        return {
            key: _sanitize(item, show_ids)
            for key, item in value.items()
            if (show_ids or (key not in INTERNAL_KEYS and not key.endswith("_id")))
            and not any(part in key.lower() for part in SENSITIVE_KEY_PARTS)
        }
    if isinstance(value, list):
        return [_sanitize(item, show_ids) for item in value]
    return value


def build_report(
    scenario, args, client, payloads, errors, start, end, entity=None,
    resolution=None, native_metadata=None, workflow_warning=None,
):
    title = scenario.title_zh if args.locale.lower().startswith("zh") else scenario.title
    project_scoped = any("{project_id}" in spec.path for spec in scenario.requests)
    context = [
        {
            "label": "Project" if project_scoped else "Account",
            "value": (
                client.project_id if project_scoped and args.show_ids
                else "Current project" if project_scoped
                else "Current account"
            ),
        },
        {"label": "Range", "value": f"{start} → {end}"},
        {"label": "Period", "value": args.period},
    ]
    platforms = _platforms(args.platform)
    if platforms:
        context.append({"label": "Platform", "value": ", ".join(platforms)})
    if any(spec.paging != "none" for spec in scenario.requests):
        context.extend([
            {"label": "Page", "value": args.page},
            {"label": "Page size", "value": args.limit},
        ])
    if entity:
        context.append({"label": "Entity", "value": entity.get("name") or entity.get("content") or args.path or "Selected entity"})
    metrics = _collect_metrics(payloads)
    charts = _collect_charts(payloads, scenario)
    tables = _collect_tables(payloads, scenario, args.show_ids)
    extra_insights = []
    if scenario.name == "page-opportunities":
        rows, extra_insights = _page_opportunity_rules(payloads)
        tables.insert(0, _table("Deterministic recommendations", rows, args.show_ids))
    warnings = [f"{alias}: {message}" for alias, message in errors.items()]
    if workflow_warning:
        warnings.append(workflow_warning)
    for item in (native_metadata or {}).get("warnings") or []:
        if isinstance(item, dict):
            warnings.append(
                f"{item.get('code')}: {item.get('message')}"
                + (f" [{item.get('source')}]" if item.get("source") else "")
            )
        else:
            warnings.append(str(item))
    if len(scenario.requests) > 1 or scenario.name in ("ai-overview", "page-detail"):
        warnings.append("GA4 sessions/users, Cloudflare requests, Worker events, and AI Agent event counts use different units and are displayed separately; they are never added together.")
    if scenario.name in ("page-health", "page-detail", "page-opportunities"):
        warnings.append("Page health uses cached data only. This report never triggers the blocking PageSpeed refresh endpoint.")
    sources = []
    if native_metadata:
        for source in native_metadata.get("sources") or []:
            units = source.get("units") or {}
            sources.append({
                "name": source.get("name"),
                "status": source.get("status"),
                "as_of": source.get("as_of"),
                "units": units,
                "unit": ", ".join(f"{key}: {value}" for key, value in units.items()) or "records",
                "effective_range": source.get("effective_range"),
                "available_days": source.get("available_days"),
                "expected_days": source.get("expected_days"),
                "expected_lag_seconds": source.get("expected_lag_seconds"),
                "date_basis": source.get("date_basis"),
                "reason": source.get("reason"),
            })
    else:
        for spec in scenario.requests:
            status = "error" if spec.alias in errors else ("partial" if payloads.get(spec.alias) in (None, {}, []) else "ok")
            sources.append({
                "name": spec.alias, "status": status, "as_of": end,
                "unit": SOURCE_UNITS.get(spec.alias, "records"),
            })
    audit_fields = [
        {"label": "Scenario", "value": scenario.name},
        {"label": "Density", "value": scenario.density},
        {"label": "Locale", "value": args.locale},
        {"label": "Timezone", "value": args.timezone},
        {"label": "Concurrency limit", "value": "4"},
    ]
    if any(spec.paging != "none" for spec in scenario.requests):
        audit_fields.extend([
            {"label": "Page", "value": args.page},
            {"label": "Page size", "value": args.limit},
        ])
    if resolution:
        audit_fields.append({"label": "Entity resolution", "value": resolution})
    report = {
        "schema_version": "1.0",
        "report_type": scenario.name,
        "title": title,
        "subtitle": scenario.description or f"Read-only {scenario.density} report with explicit coverage and source units.",
        "generated_at": now_iso(),
        "locale": args.locale,
        "timezone": args.timezone,
        "context": context,
        "metrics": metrics,
        "charts": charts,
        "tables": tables,
        "insights": (extra_insights + _insights(metrics, tables, errors, scenario))[:3],
        "next_actions": _next_actions(scenario, args),
        "coverage": {
            "requested_range": (native_metadata or {}).get("requested_range") or {"from": start, "to": end},
            "effective_range": (native_metadata or {}).get("effective_range") or {"from": start, "to": end},
            "as_of": (native_metadata or {}).get("as_of"),
            "partial": bool((native_metadata or {}).get("partial")) or bool(errors),
            "sources": sources,
        },
        "audit": {
            "fields": audit_fields,
            "api_calls": [
                {**call, "path": _mask_path(call.get("path"), args.show_ids)}
                for call in client.calls
            ],
            "warnings": warnings,
        },
    }
    return _sanitize(report, args.show_ids)


def _validate_requirements(scenario, args):
    for requirement in scenario.requires:
        if requirement == "topic" and not args.topic:
            raise ValueError(f"{scenario.name} requires --topic <ID or exact name>")
        if requirement == "prompt" and not (args.prompt_id or args.prompt or args.topic):
            raise ValueError(f"{scenario.name} requires --prompt-id, --prompt, or --topic")
        if requirement == "path" and not args.path:
            raise ValueError(f"{scenario.name} requires --path /page/path")
        if requirement == "resource-id" and not args.resource_id:
            raise ValueError(f"{scenario.name} requires --resource-id")


def run_report(args, client=None):
    scenario = get_scenario(args.scenario)
    _validate_requirements(scenario, args)
    if args.page < 1 or args.limit < 1:
        raise ValueError("--page and --limit must be positive integers")
    start, end = _window(args)
    if client is None:
        key, base = get_api_config()
        project_required = any("{project_id}" in spec.path for spec in scenario.requests)
        project_id = get_project_id(args.project_id) if project_required else args.project_id
        client = ReportClient(key, base, project_id)
    values = {
        "project_id": client.project_id,
        "topic_id": "",
        "prompt_id": "",
        "resource_id": quote(args.resource_id or "", safe=""),
        "page_path": args.path or "",
    }
    entity = resolution = None
    analytics_params = _analytics_params(args, start, end)
    native = _try_report_data(client, scenario, args, start, end, analytics_params)
    if native and native.get("used"):
        return build_report(
            scenario,
            args,
            client,
            native["payloads"],
            {},
            start,
            end,
            native.get("entity"),
            native.get("resolution"),
            native_metadata=native.get("metadata"),
            workflow_warning=native.get("warning"),
        )
    workflow_warning = native.get("warning") if native else None
    if "topic" in scenario.requires:
        entity = _resolve_topic(client, args.topic, analytics_params)
        values["topic_id"] = quote(str(entity["id"]), safe="")
        resolution = "exact Topic ID/name match via /analytics/topics"
    if "prompt" in scenario.requires:
        entity, resolution = _resolve_prompt(client, args, analytics_params)
        values["prompt_id"] = quote(str(entity.get("id") or entity.get("prompt_id")), safe="")
    payloads, errors = _fetch_scenario(client, scenario, args, start, end, values)
    return build_report(
        scenario, args, client, payloads, errors, start, end, entity, resolution,
        workflow_warning=workflow_warning,
    )


def emit_report(report, args):
    output_format = "json" if args.json else args.format
    if output_format == "json":
        print_json(report)
        return None
    if output_format in ("markdown", "both"):
        print(render_markdown(report), end="")
    path = None
    if output_format in ("html", "both"):
        path = write_html(report, args.output, args.output_dir)
        print(f"\nREPORT_TITLE: {report.get('title')}")
        print(f"REPORT_FILE: {path}")
        print(f"REPORT_PREVIEW: {path}")
        for finding in (report.get("insights") or [])[:3]:
            text = finding.get("body") if isinstance(finding, dict) else finding
            print(f"REPORT_FINDING: {' '.join(str(text).split())}")
        for action in (report.get("next_actions") or [])[:3]:
            print(f"REPORT_NEXT: {' '.join(str(action).split())}")
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Adgine GEO scenario reports (offline HTML by default)")
    parser.add_argument("scenario", nargs="?", choices=sorted(SCENARIOS), help="Report scenario")
    parser.add_argument("--list-scenarios", action="store_true", help="List all P1-P3 report scenarios")
    parser.add_argument("--project-id", help="Project ID, or use GEO_PROJECT_ID")
    parser.add_argument("--period", choices=["7d", "14d", "30d", "90d"], default="7d")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD; defaults to yesterday")
    parser.add_argument("--granularity", choices=["day", "week", "month"], default="day")
    parser.add_argument("--platform", action="append", help="Platform code; repeat or use comma-separated values")
    parser.add_argument("--topic", help="Topic ID or exact name")
    parser.add_argument("--prompt", help="Prompt ID or text")
    parser.add_argument("--prompt-id", help="Explicit Prompt ID (fastest)")
    parser.add_argument("--prompt-index", type=int, default=1, help="Stable 1-based index within Topic")
    parser.add_argument("--path", help="Exact website path beginning with /")
    parser.add_argument("--resource-id", help="Opportunity/content/task identifier")
    parser.add_argument("--metric", choices=["visibility", "visibility_score", "sov", "share_of_voice"])
    parser.add_argument("--page", type=int, default=1, help="1-based result page")
    parser.add_argument("--limit", type=int, default=DEFAULT_PAGE_SIZE, help="Rows per page (default: 40)")
    parser.add_argument("--locale", default=os.environ.get("GEO_REPORT_LOCALE", "en-US"))
    parser.add_argument("--timezone", default=os.environ.get("GEO_REPORT_TIMEZONE", "UTC"))
    parser.add_argument("--format", choices=["html", "markdown", "json", "both"], default="html")
    parser.add_argument("--json", action="store_true", help="Alias for --format json")
    parser.add_argument("--output", help="Exact HTML output path")
    parser.add_argument("--output-dir", help="HTML output directory")
    parser.add_argument("--show-ids", action="store_true", help="Include internal identifiers for debugging")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.list_scenarios:
        print_json(scenario_rows())
        return 0
    if not args.scenario:
        print("ERROR: choose a scenario or pass --list-scenarios")
        return 2
    try:
        report = run_report(args)
        emit_report(report, args)
        return 0
    except (ApiError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
