#!/usr/bin/env python3
"""Generate stable, auditable GEO reports from the current GEO-Api contracts."""

import argparse
import copy
import json
import math
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
from _i18n import label as display_label, localize_unit, normalize_locale, t  # noqa: E402
from _reporting import now_iso, render_markdown, write_html  # noqa: E402


INTERNAL_KEYS = {
    "id", "project_id", "topic_id", "prompt_id", "execution_id", "competitor_id",
    "content_id", "job_id", "record_id", "task_id", "brand_relation_id",
}
SENSITIVE_KEY_PARTS = ("password", "secret", "api_key", "api_token", "access_token", "refresh_token")
PRESENTATION_META_KEYS = {
    "schema_version", "requested_range", "effective_range", "as_of", "partial",
    "warnings", "sources",
}
DATE_KEYS = ("date", "day", "timestamp", "occurred_at", "created_at", "analyzed_at")
PREFERRED_COLUMNS = (
    "name", "title", "content", "path", "page_path", "landing_page", "platform",
    "source", "channel", "status", "type", "traffic_type", "bot_name",
    "visibility_rank", "visibility_score", "share_of_voice", "average_position",
    "visibility_rank_change", "visibility_score_change", "share_of_voice_change",
    "average_position_change", "prompt_count", "executions", "positive", "neutral",
    "negative", "current", "change",
    "requests", "sessions", "active_users", "page_views", "visits",
    "conversion_rate", "score", "rank", "created_at", "updated_at",
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
    "ga4_ai": "AI referral sessions / users / percent",
    "referrals": "sessions / users / page views",
    "cloudflare": "HTTP requests / bytes",
    "cloudflare_ai": "AI assistant / search / training HTTP requests",
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
    "competitor_rankings": "percent / rank",
    "competitor_overview": "percent / rank",
    "competitor_topics": "percent / rank",
    "competitor_prompts": "percent / rank",
}

DEFAULT_PAGE_SIZE = 40
SUPPORTED_CHART_TYPES = (
    "bar_chart", "line_chart", "pie_chart", "gauge", "funnel",
    "scatter_plot", "treemap", "heatmap_table", "progress_bar", "timeline",
)
PREFERRED_TREND_METRICS = {
    "ga4": ("sessions", "active_users", "page_views"),
    "ga4_ai": ("sessions", "active_users"),
    "ai_referrals": ("sessions", "active_users"),
    "referrals": ("sessions", "active_users"),
    "cloudflare": ("requests_total", "requests_cached"),
    "worker": ("requests",),
}
COMPOSITE_REPORTS_WITHOUT_WORKER_TREND = {"executive-overview", "traffic-overview"}
AI_TRAFFIC_PRESENTATION_SCENARIOS = {
    "executive-overview", "traffic-overview", "ga4-overview", "ga4-referrals",
    "cloudflare-overview", "cloudflare-bots", "ai-overview", "ai-bots",
}
GA4_AI_PRESENTATION_SCENARIOS = {
    "executive-overview", "traffic-overview", "ga4-overview", "ga4-referrals",
}
CLOUDFLARE_AI_PRESENTATION_SCENARIOS = {
    "executive-overview", "traffic-overview", "cloudflare-overview",
    "cloudflare-bots", "ai-overview", "ai-bots",
}
HIDDEN_PRESENTATION_KEY_PARTS = ("revenue", "transaction")

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


def _normalized_domain(value):
    value = str(value or "").strip().casefold()
    value = re.sub(r"^[a-z][a-z0-9+.-]*://", "", value)
    value = value.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    return value[4:] if value.startswith("www.") else value


def _resolve_competitor(client, args):
    explicit_id = str(args.competitor_id or "").strip()
    reference = str(args.competitor or "").strip()
    if explicit_id:
        return {
            "id": explicit_id,
            "name": reference or t(args.locale, "selected_competitor"),
        }, t(args.locale, "resolution_competitor_explicit_id")
    if _looks_like_uuid(reference):
        return {
            "id": reference,
            "name": t(args.locale, "selected_competitor"),
        }, t(args.locale, "resolution_competitor_reference_id")
    payload = client.get(f"/api/projects/{client.project_id}/competitors") or {}
    items = _first_list(payload, ("items", "competitors"))
    lowered = reference.casefold()
    domain = _normalized_domain(reference)
    matches = [
        item for item in items
        if str(item.get("name") or "").strip().casefold() == lowered
        or (domain and _normalized_domain(item.get("domain")) == domain)
    ]
    if not matches:
        raise ValueError(f"Competitor not found: {reference}")
    if len(matches) > 1:
        raise ValueError(f"Competitor name/domain is ambiguous; use --competitor-id: {reference}")
    competitor = matches[0]
    competitor["id"] = competitor.get("id") or competitor.get("competitor_id")
    if not competitor.get("id"):
        raise ValueError(f"Competitor has no usable ID: {reference}")
    return competitor, t(args.locale, "resolution_competitor_catalog")


def _resolve_prompt(client, args, analytics_params):
    if args.prompt_id:
        return {
            "id": args.prompt_id,
            "content": args.prompt or t(args.locale, "selected_prompt"),
        }, t(args.locale, "resolution_explicit_id")
    reference = (args.prompt or "").strip()
    if reference and re.fullmatch(r"[0-9a-fA-F-]{32,36}", reference):
        return {
            "id": reference,
            "content": t(args.locale, "selected_prompt"),
        }, t(args.locale, "resolution_id_in_prompt")
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
            return matches[0], t(
                args.locale,
                "resolution_within_topic",
                topic=topic.get("name"),
            )
        ordered = sorted(items, key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")))
        if args.prompt_index < 1 or args.prompt_index > len(ordered):
            raise ValueError(f"--prompt-index is out of range (1..{len(ordered)})")
        return ordered[args.prompt_index - 1], t(
            args.locale,
            "resolution_topic_prompt_index",
            index=args.prompt_index,
        )
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
    return matches[0], t(args.locale, "resolution_project_catalog")


def _replace_query_values(value, values):
    if not isinstance(value, str):
        return value
    return value.format(**values)


def _request_params(spec, args, start, end, values):
    if spec.date_style == "analytics":
        params = _analytics_params(args, start, end)
        if not spec.accepts_platform:
            params.pop("platform", None)
    elif spec.date_style == "competitor":
        params = {"date_from": start, "date_to": end}
        platforms = _platforms(args.platform)
        if spec.accepts_platform and platforms:
            params["platform"] = platforms
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
    if spec.alias in ("competitor_topics", "competitor_prompts"):
        params["types"] = _platforms(args.prompt_type) or ["visibility"]
        tags = _platforms(args.tag_id)
        if tags:
            params["tags"] = tags
    if spec.alias == "competitor_overview":
        if values.get("filter_topic_ids"):
            params["topic_id"] = values["filter_topic_ids"]
        if values.get("filter_prompt_ids"):
            params["prompt_id"] = values["filter_prompt_ids"]
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
            resolution = t(args.locale, "resolution_topic_report_id")
        else:
            params["q"] = args.topic.strip()
            resolution = t(args.locale, "resolution_topic_report_name")
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
            entity = {"content": args.prompt or t(args.locale, "selected_prompt")}
        if _looks_like_uuid(reference):
            params["prompt_id"] = str(reference).strip()
            resolution = resolution or t(args.locale, "resolution_prompt_report_id")
        else:
            params["q"] = str(reference).strip()
            resolution = t(args.locale, "resolution_prompt_report_text")
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
    capabilities, warning = discover_capabilities(client, locale=args.locale)
    feature, endpoint = mapping
    if not supports(capabilities, feature):
        fallback = warning or t(args.locale, "warning_feature_disabled", feature=feature)
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
                "warning": t(args.locale, "warning_route_unavailable", endpoint=endpoint),
            }
        raise
    if data.get("schema_version") != "1.0":
        return {
            "used": False,
            "warning": t(args.locale, "warning_schema_unsupported"),
        }
    payloads = _native_payloads(scenario, data)
    errors = {}
    if scenario.name in ("executive-overview", "traffic-overview"):
        path = f"/api/projects/{client.project_id}/ai-agent/overview-kpi"
        try:
            payloads["cloudflare_ai"] = client.get(
                path, _traffic_params(args, start, end, accepts_platform=True),
            ) or {}
        except ApiError as exc:
            if exc.status_code in (401, 403, 409, 422):
                raise
            errors["cloudflare_ai"] = str(exc)
    entity_key = "topic" if scenario.name in ("topic-detail", "topic-lifecycle") else (
        "prompt" if scenario.name in ("prompt-performance", "prompt-executions") else None
    )
    resolved_entity = data.get(entity_key) if entity_key else None
    if isinstance(resolved_entity, dict):
        entity = resolved_entity
    return {
        "used": True,
        "payloads": payloads,
        "errors": errors,
        "metadata": data,
        "entity": entity,
        "resolution": resolution,
        "warning": warning,
    }


def _label(key, locale="en-US"):
    return display_label(key, locale)


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


def _is_hidden_presentation_key(key):
    normalized = str(key or "").lower()
    return any(part in normalized for part in HIDDEN_PRESENTATION_KEY_PARTS)


def _drop_hidden_presentation_fields(value):
    if isinstance(value, dict):
        return {
            key: _drop_hidden_presentation_fields(item)
            for key, item in value.items()
            if not _is_hidden_presentation_key(key)
        }
    if isinstance(value, list):
        return [_drop_hidden_presentation_fields(item) for item in value]
    return value


def _report_data_traffic(payloads, scenario):
    report_data = payloads.get("report_data")
    if not isinstance(report_data, dict):
        return {}
    if scenario.name == "executive-overview":
        return report_data.get("traffic") or {}
    if scenario.name == "traffic-overview":
        return report_data
    return {}


def _find_ga4_ai_payload(payloads, scenario):
    for alias in ("ga4_ai", "referrals"):
        value = payloads.get(alias)
        if isinstance(value, dict):
            return value
    traffic = _report_data_traffic(payloads, scenario)
    ga4 = traffic.get("ga4") if isinstance(traffic, dict) else None
    return (ga4 or {}).get("ai_referrals") if isinstance(ga4, dict) else None


def _normalize_ga4_ai(payload):
    if not isinstance(payload, dict):
        return None
    rate = _numeric(payload.get("ai_referral_rate"))
    rate_percent = rate * 100 if rate is not None and abs(rate) <= 1 else rate
    return {
        "metrics": {
            "ai_referral_sessions": payload.get("total_sessions"),
            "ai_referral_users": payload.get("total_active_users"),
            "ai_referral_rate": rate_percent,
        },
        "daily": [
            {
                "date": item.get("date"),
                "sessions": item.get("sessions"),
                "active_users": item.get("active_users"),
            }
            for item in payload.get("daily") or []
            if isinstance(item, dict)
        ],
    }


def _find_cloudflare_ai_payload(payloads, scenario):
    direct = payloads.get("cloudflare_ai")
    if isinstance(direct, dict):
        return direct
    traffic = _report_data_traffic(payloads, scenario)
    ai_agent = traffic.get("ai_agent") if isinstance(traffic, dict) else None
    if not isinstance(ai_agent, dict):
        return None
    metrics = ai_agent.get("metrics") or {}
    return {
        "ai_citations": metrics.get("ai_citations"),
        "ai_index": metrics.get("ai_index"),
        "ai_training": metrics.get("ai_training"),
        "platform_leaderboards": {},
    }


def _normalize_cf_period_metric(value):
    if not isinstance(value, dict):
        return value
    return {
        "current": value.get("current"),
        "previous": value.get("prev"),
        "change": value.get("delta"),
        "unit": "http_requests",
        "daily": value.get("daily") or [],
        "prev_daily": value.get("prev_daily") or [],
    }


def _normalize_cloudflare_ai(payload):
    if not isinstance(payload, dict):
        return None
    metric_sources = {
        "ai_assistant": "ai_citations",
        "ai_search": "ai_index",
        "ai_training": "ai_training",
    }
    metrics = {
        key: _normalize_cf_period_metric(payload.get(source_key))
        for key, source_key in metric_sources.items()
        if payload.get(source_key) is not None
    }
    leaderboards = payload.get("platform_leaderboards") or {}
    platforms = {}
    for metric_key, source_key in metric_sources.items():
        for item in leaderboards.get(source_key) or []:
            if not isinstance(item, dict):
                continue
            platform_key = str(
                item.get("platform_id") or item.get("display_name") or "unknown"
            )
            row = platforms.setdefault(platform_key, {
                "platform": item.get("display_name") or platform_key,
                "ai_assistant": 0,
                "ai_search": 0,
                "ai_training": 0,
            })
            row[metric_key] = item.get("requests") or 0
    platform_rows = sorted(
        platforms.values(),
        key=lambda row: max(
            _numeric(row.get(key)) or 0
            for key in ("ai_assistant", "ai_search", "ai_training")
        ),
        reverse=True,
    )
    return {"metrics": metrics, "platform_distribution": platform_rows}


def _presentation_payloads(payloads, scenario):
    cleaned = _drop_hidden_presentation_fields(copy.deepcopy(payloads))
    if scenario.name == "competitor-rankings":
        payload = cleaned.get("competitor_rankings") or {}
        rows = [
            {
                "rank": item.get("rank"),
                "name": item.get("name"),
                "domain": item.get("domain"),
                "visibility_score": item.get("current"),
                "is_our_brand": item.get("is_our_brand"),
            }
            for item in payload.get("competitors") or []
            if isinstance(item, dict)
        ]
        own = next((item for item in rows if item.get("is_our_brand")), None)
        metrics = {"brand_count": len(rows)}
        if own:
            metrics.update({
                "our_visibility_rank": own.get("rank"),
                "our_visibility_score": own.get("visibility_score"),
            })
        return {"competitor_rankings": {"metrics": metrics, "items": rows}}
    if scenario.name == "competitor-overview":
        payload = cleaned.get("competitor_overview") or {}
        competitor = payload.get("competitor") or {}
        ours = payload.get("our_brand") or {}
        visibility = payload.get("visibility") or {}
        competitor_visibility = visibility.get("competitor") or {}
        our_visibility = visibility.get("ours") or {}
        metrics = {
            "competitor_visibility_score": competitor_visibility.get("visibility_score"),
            "our_visibility_score": our_visibility.get("visibility_score"),
            "competitor_share_of_voice": competitor_visibility.get("share_of_voice"),
            "our_share_of_voice": our_visibility.get("share_of_voice"),
        }
        comparison = [
            {
                "name": competitor.get("name") or t("en-US", "selected_competitor"),
                "visibility_score": competitor_visibility.get("visibility_score"),
                "share_of_voice": competitor_visibility.get("share_of_voice"),
            },
            {
                "name": ours.get("name") or "Our brand",
                "visibility_score": our_visibility.get("visibility_score"),
                "share_of_voice": our_visibility.get("share_of_voice"),
                "is_our_brand": True,
            },
        ]
        topic_rankings = []
        for item in payload.get("topic_rankings") or []:
            competitor_result = item.get("competitor") or {}
            our_result = item.get("ours") or {}
            topic_rankings.append({
                "name": item.get("topic_name"),
                "prompt_count": item.get("prompt_count"),
                "competitor_rank": competitor_result.get("rank"),
                "competitor_score": competitor_result.get("score"),
                "our_rank": our_result.get("rank"),
                "our_score": our_result.get("score"),
            })
        sentiment = payload.get("sentiment") or {}
        competitor_sentiment = sentiment.get("competitor") or {}
        our_sentiment = sentiment.get("ours") or {}
        metrics.update({
            "competitor_classified_count": competitor_sentiment.get("classified_count"),
            "competitor_unclassified_count": competitor_sentiment.get("unclassified_count"),
            "our_classified_count": our_sentiment.get("classified_count"),
            "our_unclassified_count": our_sentiment.get("unclassified_count"),
        })
        return {
            "competitor_overview": {
                "metrics": metrics,
                "comparison": comparison,
                "topic_rankings": topic_rankings,
            },
            "competitor_sentiment": {
                "sentiment_distribution": {
                    key: competitor_sentiment.get(key)
                    for key in ("positive", "neutral", "negative")
                },
            },
            "our_sentiment": {
                "sentiment_distribution": {
                    key: our_sentiment.get(key)
                    for key in ("positive", "neutral", "negative")
                },
            },
        }
    if scenario.name not in AI_TRAFFIC_PRESENTATION_SCENARIOS:
        return cleaned

    output = {}
    if scenario.name == "executive-overview":
        report_data = cleaned.get("report_data")
        if isinstance(report_data, dict):
            report_data = copy.deepcopy(report_data)
            report_data.pop("traffic", None)
            output["report_data"] = report_data
        for alias, value in cleaned.items():
            if alias not in {
                "report_data", "traffic", "ga4", "ga4_ai", "referrals",
                "cloudflare", "cloudflare_ai", "worker", "ai_agent",
            }:
                output[alias] = value

    if scenario.name in GA4_AI_PRESENTATION_SCENARIOS:
        ga4 = _normalize_ga4_ai(_find_ga4_ai_payload(cleaned, scenario))
        if ga4:
            output["ga4_ai"] = ga4
    if scenario.name in CLOUDFLARE_AI_PRESENTATION_SCENARIOS:
        cloudflare = _normalize_cloudflare_ai(
            _find_cloudflare_ai_payload(cleaned, scenario)
        )
        if cloudflare:
            output["cloudflare_ai"] = cloudflare
    return output


def _comparison_metric(key, value, locale="en-US"):
    current = value.get("current")
    change = value.get("change")
    if change is None:
        change = value.get("delta_pct") if value.get("delta_pct") is not None else value.get("delta")
    return {
        "label": _label(key, locale), "value": current, "change": change,
        "format": _format_for(key, current), "direction": _direction(key, change),
        "note": localize_unit(value.get("unit"), locale),
    }


def _collect_metrics(payloads, limit=8, locale="en-US"):
    metrics, seen = [], set()

    def add(key, value):
        if key in seen or len(metrics) >= limit:
            return
        if key in INTERNAL_KEYS or key in PRESENTATION_META_KEYS or str(key).endswith("_id"):
            return
        if isinstance(value, dict) and "current" in value:
            metric = _comparison_metric(key, value, locale)
        elif _numeric(value) is not None:
            metric = {"label": _label(key, locale), "value": value, "format": _format_for(key, value)}
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
            if key in PRESENTATION_META_KEYS or key in ("total", "page", "limit", "pages", "period_days"):
                continue
            add(key, value)
    return metrics


def _series_from_list(name, points, color=None, locale="en-US", preferred_keys=None):
    if not isinstance(points, list) or not points:
        return []
    numeric_keys = []
    for point in points:
        if isinstance(point, dict):
            numeric_keys.extend(key for key, value in point.items() if key not in DATE_KEYS and _numeric(value) is not None)
    numeric_keys = list(dict.fromkeys(numeric_keys))
    if preferred_keys:
        numeric_keys = [key for key in preferred_keys if key in numeric_keys]
    numeric_keys = numeric_keys[:4]
    output = []
    for key in numeric_keys:
        data = []
        for index, point in enumerate(points):
            if not isinstance(point, dict):
                continue
            x = next((point.get(date_key) for date_key in DATE_KEYS if point.get(date_key) is not None), index + 1)
            data.append({"x": x, "y": point.get(key)})
        series_name = name if key == "value" and len(numeric_keys) == 1 else f"{name} · {_label(key, locale)}"
        output.append({"name": series_name, "points": data, "color": color})
    return output


def _trend_series(name, current, previous=None, locale="en-US", preferred_keys=None):
    series = _series_from_list(
        name, current, locale=locale, preferred_keys=preferred_keys,
    )
    if not series:
        return []
    previous_series = _series_from_list(
        name, previous, locale=locale, preferred_keys=preferred_keys,
    )
    for item in previous_series:
        item["name"] = f"{item['name']} · {t(locale, 'previous_period_label')}"
        item["dash"] = True
    return series + previous_series


def _preferred_trend_metrics(key):
    return PREFERRED_TREND_METRICS.get(str(key).lower())


def _hide_worker_trend(scenario, alias, path=()):
    if scenario.name not in COMPOSITE_REPORTS_WITHOUT_WORKER_TREND:
        return False
    names = {str(alias).lower(), *(str(item).lower() for item in path)}
    return "worker" in names


def _category_number(value):
    if isinstance(value, dict):
        for key in ("current", "value", "count", "total", "requests", "sessions", "page_views", "score"):
            number = _numeric(value.get(key))
            if number is not None:
                return number
        return None
    return _numeric(value)


def _category_items(values, locale="en-US"):
    if not isinstance(values, dict):
        return []
    items = []
    for key, value in values.items():
        number = _category_number(value)
        if number is not None:
            items.append({"label": _label(key, locale), "value": number})
    return items


def _named_dicts(value, path=(), depth=0):
    if not isinstance(value, dict) or depth > 3:
        return
    for key, item in value.items():
        if key in PRESENTATION_META_KEYS:
            continue
        if key == "summary" and isinstance(item, dict):
            yield from _named_dicts(item, path, depth + 1)
            continue
        current_path = path + (key,)
        if isinstance(item, dict):
            yield current_path, item
            yield from _named_dicts(item, current_path, depth + 1)


def _ranked_chart(rows, title, list_key=None, locale="en-US"):
    if not isinstance(rows, list) or not rows:
        return None
    label_keys = ("name", "title", "content", "path", "page_path", "landing_page", "domain", "source", "platform", "bot_name", "status")
    value_keys = ("visibility_score", "share_of_voice", "requests", "sessions", "page_views", "visits", "score", "count", "total", "value")
    label_key = next((key for key in label_keys if any(isinstance(row, dict) and row.get(key) not in (None, "") for row in rows)), None)
    value_key = next((key for key in value_keys if any(isinstance(row, dict) and _numeric(row.get(key)) is not None for row in rows)), None)
    if not label_key or not value_key:
        return None
    items = [
        {"label": row.get(label_key), "value": row.get(value_key)}
        for row in rows if isinstance(row, dict) and _numeric(row.get(value_key)) is not None
    ]
    items.sort(key=lambda item: _numeric(item.get("value")) or 0, reverse=True)
    if not items:
        return None
    additive_values = {"requests", "sessions", "page_views", "visits", "count", "total", "value"}
    treemap_lists = {"citation_sources", "pages", "results"}
    chart_type = (
        "treemap"
        if list_key in treemap_lists and value_key in additive_values and len(items) >= 4
        else "bar_chart"
    )
    return {
        "type": chart_type,
        "title": title,
        "items": items[:12],
        "format": _format_for(value_key),
        "description": t(locale, "chart_desc_treemap" if chart_type == "treemap" else "chart_desc_bar"),
    }


def _scatter_chart(rows, title, locale="en-US"):
    if not isinstance(rows, list) or len(rows) < 3:
        return None
    label_keys = ("name", "title", "content", "path", "page_path", "domain", "source", "platform")
    numeric_keys = (
        "visibility_score", "average_position", "share_of_voice", "citation_rate",
        "requests", "sessions", "page_views", "visits", "score", "rank",
    )
    label_key = next((key for key in label_keys if any(isinstance(row, dict) and row.get(key) for row in rows)), None)
    available = [
        key for key in numeric_keys
        if sum(isinstance(row, dict) and _numeric(row.get(key)) is not None for row in rows) >= 3
    ]
    if not label_key or len(available) < 2:
        return None
    x_key, y_key = available[:2]
    points = [
        {"label": row.get(label_key), "x": row.get(x_key), "y": row.get(y_key)}
        for row in rows
        if isinstance(row, dict) and _numeric(row.get(x_key)) is not None and _numeric(row.get(y_key)) is not None
    ]
    if len(points) < 3:
        return None
    x_label, y_label = _label(x_key, locale), _label(y_key, locale)
    chart = {
        "type": "scatter_plot",
        "title": t(locale, "chart_relationship", x=x_label, y=y_label),
        "description": t(locale, "chart_desc_scatter"),
        "x_label": x_label,
        "y_label": y_label,
        "x_format": _format_for(x_key),
        "y_format": _format_for(y_key),
        "points": points[:40],
    }
    bounded_percent_keys = {
        "visibility_score", "share_of_voice", "citation_rate", "recommendation_rate",
        "first_recommendation_rate", "top3_rate",
    }
    lower_is_better_keys = {"average_position", "rank", "visibility_rank", "citation_rank"}
    for axis, key in (("x", x_key), ("y", y_key)):
        if key in bounded_percent_keys:
            chart[f"{axis}_min"] = 0
            chart[f"{axis}_max"] = 100
        if key in lower_is_better_keys:
            values = [_numeric(point.get(axis)) for point in points]
            chart[f"{axis}_min"] = 1
            chart[f"{axis}_max"] = max(2, math.ceil(max(value for value in values if value is not None)))
            chart[f"{axis}_reverse"] = True
    return chart


def _timeline_chart(rows, title, scenario, locale="en-US"):
    timeline_scenarios = {
        "prompt-executions", "content-pipeline", "brand-jobs",
        "wordpress-publications", "worker-events", "operations-overview",
    }
    if scenario.name not in timeline_scenarios or not isinstance(rows, list):
        return None
    date_key = next((key for key in DATE_KEYS if any(isinstance(row, dict) and row.get(key) for row in rows)), None)
    if not date_key:
        return None
    label_keys = ("title", "name", "content", "type", "path", "page_path", "platform")
    label_key = next((key for key in label_keys if any(isinstance(row, dict) and row.get(key) for row in rows)), None)
    if not label_key:
        return None
    items = []
    for row in rows:
        if not isinstance(row, dict) or not row.get(date_key):
            continue
        description = row.get("error") or row.get("message") or row.get("current_step")
        items.append({
            "date": row.get(date_key),
            "label": row.get(label_key),
            "status": row.get("status") or row.get("job_status") or row.get("publish_status"),
            "description": description,
        })
    items.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
    if not items:
        return None
    return {
        "type": "timeline", "title": title,
        "description": t(locale, "chart_desc_timeline"), "items": items[:12],
    }


def _funnel_chart(rows, title, locale="en-US"):
    if not isinstance(rows, list) or len(rows) < 2:
        return None
    label_keys = ("stage", "name", "label", "status", "type")
    value_keys = ("value", "count", "total", "users", "sessions", "requests")
    label_key = next((key for key in label_keys if all(isinstance(row, dict) and row.get(key) for row in rows)), None)
    value_key = next((key for key in value_keys if all(isinstance(row, dict) and _numeric(row.get(key)) is not None for row in rows)), None)
    if not label_key or not value_key:
        return None
    items = [{"label": row.get(label_key), "value": row.get(value_key)} for row in rows]
    values = [_numeric(item["value"]) for item in items]
    if any(value < 0 for value in values) or any(values[index] < values[index + 1] for index in range(len(values) - 1)):
        return None
    return {
        "type": "funnel", "title": title,
        "description": t(locale, "chart_desc_funnel"),
        "items": items, "format": _format_for(value_key),
    }


def _numeric_metrics(value, path=(), depth=0):
    if not isinstance(value, dict) or depth > 5:
        return
    if path and _numeric(value.get("current")) is not None:
        yield path, value.get("current")
    for key, item in value.items():
        if key in PRESENTATION_META_KEYS or key in ("current", "previous", "change"):
            continue
        current_path = path + (key,)
        if isinstance(item, dict):
            yield from _numeric_metrics(item, current_path, depth + 1)
        elif _numeric(item) is not None:
            yield current_path, item


def _bounded_charts(payload, alias, locale="en-US"):
    gauges, progress, seen = [], [], set()
    for path, value in _numeric_metrics(payload):
        key = path[-1]
        normalized = str(key).lower()
        number = _numeric(value)
        if number is None or not 0 <= number <= 100 or key in seen:
            continue
        label = _label(key, locale)
        if "score" in normalized and not any(token in normalized for token in ("rank", "position")):
            gauges.append({
                "type": "gauge", "title": label,
                "description": t(locale, "chart_desc_gauge"),
                "value": number, "min": 0, "max": 100, "format": _format_for(key),
            })
            seen.add(key)
        elif any(token in normalized for token in ("rate", "share", "progress", "coverage", "percent", "pct")):
            progress.append({"label": label, "value": number, "max": 100})
            seen.add(key)
    charts = gauges[:1]
    if progress:
        charts.append({
            "type": "progress_bar",
            "title": t(locale, "chart_progress"),
            "description": t(locale, "chart_desc_progress"),
            "items": progress[:6],
            "format": "percent",
        })
    return charts


def _chart_title(alias, path, locale="en-US"):
    structural = {"report_data", "metrics", "kpis", "execution_summary"}
    parts = [item for item in path if item not in structural]
    if alias not in structural and (not parts or parts[0] != alias):
        parts.insert(0, alias)
    return " · ".join(_label(item, locale) for item in parts)


def _collect_charts(payloads, scenario, locale="en-US"):
    max_charts = 10
    charts = []
    matrix = payloads.get("matrix")
    if isinstance(matrix, dict):
        platforms = matrix.get("platforms") or []
        competitors = matrix.get("competitors") or matrix.get("rows") or []
        if platforms and competitors:
            charts.append({
                "type": "heatmap_table", "title": t(locale, "cross_platform_comparison"),
                "description": t(locale, "chart_desc_heatmap"),
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
    cloudflare_ai = payloads.get("cloudflare_ai")
    platform_distribution = (
        cloudflare_ai.get("platform_distribution")
        if isinstance(cloudflare_ai, dict) else None
    )
    if platform_distribution:
        metric_keys = ("ai_assistant", "ai_search", "ai_training")
        charts.append({
            "type": "heatmap_table",
            "title": t(locale, "cloudflare_platform_distribution"),
            "description": t(locale, "cloudflare_platform_distribution_desc"),
            "columns": [_label(key, locale) for key in metric_keys],
            "rows": [
                {
                    "label": item.get("platform"),
                    "values": {
                        _label(key, locale): item.get(key)
                        for key in metric_keys
                    },
                }
                for item in platform_distribution[:12]
            ],
            "format": "integer",
        })
    for alias, payload in payloads.items():
        if not isinstance(payload, dict) or len(charts) >= max_charts:
            continue
        for path, value in _named_dicts(payload):
            if len(charts) >= max_charts:
                break
            key = path[-1]
            if _hide_worker_trend(scenario, alias, path):
                continue
            metric_trend = value.get("trend") or value.get("daily")
            if isinstance(metric_trend, list) and metric_trend:
                previous = (
                    value.get("prev_trend") or value.get("previous_trend")
                    or value.get("prev_daily")
                )
                preferred = _preferred_trend_metrics(key)
                series = _trend_series(
                    _label(key, locale), metric_trend, previous,
                    locale=locale, preferred_keys=preferred,
                )
                if not series:
                    continue
                format_key = next((item for item in preferred or () if _format_for(item)), key)
                charts.append({
                    "type": "line_chart",
                    "title": t(locale, "trend", name=_label(key, locale)),
                    "description": t(locale, "chart_desc_line"),
                    "series": series,
                    "format": _format_for(format_key),
                })
        for chart in _bounded_charts(payload, alias, locale):
            if len(charts) >= max_charts:
                break
            charts.append(chart)
        kpi_series = []
        for item in payload.get("kpis") or []:
            if not isinstance(item, dict):
                continue
            metric_name = item.get("label") or _label(item.get("key") or "kpi", locale)
            kpi_series.extend(_series_from_list(str(metric_name), item.get("daily"), locale=locale)[:1])
            if len(kpi_series) >= 4:
                break
        if kpi_series and len(charts) < max_charts:
            charts.append({
                "type": "line_chart",
                "title": t(locale, "kpi_trend", name=_label(alias, locale)),
                "description": t(locale, "chart_desc_line"),
                "series": kpi_series[:4],
            })
        for key in ("daily", "trend"):
            if _hide_worker_trend(scenario, alias):
                continue
            points = payload.get(key)
            preferred = _preferred_trend_metrics(alias)
            previous = payload.get("prev_daily") if key == "daily" else payload.get("previous_trend")
            series = _trend_series(
                _label(alias, locale), points, previous,
                locale=locale, preferred_keys=preferred,
            )
            if series and len(charts) < max_charts:
                format_key = next((item for item in preferred or () if _format_for(item)), alias)
                charts.append({
                    "type": "line_chart",
                    "title": t(locale, "trend", name=_label(alias, locale)),
                    "description": t(locale, "chart_desc_line"),
                    "series": series,
                    "format": _format_for(format_key),
                })
        links = payload.get("links")
        if isinstance(links, list) and links and len(charts) < max_charts:
            items = sorted(links, key=lambda item: _numeric(item.get("value")) or 0, reverse=True)[:15]
            charts.append({
                "type": "bar_chart", "title": t(locale, "top_flows", name=_label(alias, locale)),
                "description": t(locale, "chart_desc_bar"),
                "items": [{"label": f"{item.get('source')} → {item.get('target')}", "value": item.get("value")} for item in items],
                "format": "integer",
            })
        donut_keys = {"distribution", "sentiment_distribution", "status_counts", "publish_status_counts"}
        comparison_keys = {"by_platform", "platform_counts", "source_counts", "channel_counts", "counts"}
        funnel_keys = {"funnel", "stages", "pipeline_stages", "conversion_funnel"}
        for path, values in _named_dicts(payload):
            if len(charts) >= max_charts:
                break
            key = path[-1]
            items = _category_items(values, locale)
            if not items or len(items) > 12:
                continue
            title = _chart_title(alias, path, locale)
            format_key = next(
                (item for item in reversed(path) if _format_for(item) is not None),
                key,
            )
            chart_format = _format_for(format_key) or "integer"
            positive_values = [max(0, item["value"]) for item in items]
            if key in funnel_keys and len(items) >= 2 and all(
                positive_values[index] >= positive_values[index + 1]
                for index in range(len(positive_values) - 1)
            ):
                charts.append({
                    "type": "funnel", "title": title,
                    "description": t(locale, "chart_desc_funnel"),
                    "items": items, "format": chart_format,
                })
            elif key in donut_keys and len(items) >= 2 and sum(positive_values) > 0:
                charts.append({
                    "type": "pie_chart", "variant": "donut", "title": title,
                    "description": t(locale, "chart_desc_pie"),
                    "items": items, "format": chart_format,
                })
            elif key in comparison_keys:
                charts.append({
                    "type": "bar_chart", "title": title,
                    "description": t(locale, "chart_desc_bar"),
                    "items": items, "format": chart_format,
                })
        ranked_keys = {
            "items", "rows", "topics", "prompts", "pages", "results",
            "citation_sources", "platforms", "executions", "jobs", "publications", "events",
            "comparison", "topic_rankings",
            "funnel", "stages", "pipeline_stages", "conversion_funnel",
        }
        for key, rows in _payload_lists(payload):
            if len(charts) >= max_charts or key not in ranked_keys:
                continue
            title = _chart_title(alias, (key,), locale)
            if key in funnel_keys:
                funnel = _funnel_chart(rows, title, locale)
                if funnel:
                    charts.append(funnel)
                continue
            timeline = _timeline_chart(rows, t(locale, "chart_recent_activity"), scenario, locale)
            if timeline and len(charts) < max_charts:
                charts.append(timeline)
            chart = _ranked_chart(rows, title, key, locale)
            if chart and len(charts) < max_charts:
                charts.append(chart)
            scatter = _scatter_chart(rows, title, locale)
            if scatter and len(charts) < max_charts:
                charts.append(scatter)
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
            if key in PRESENTATION_META_KEYS:
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


def _table(title, rows, show_ids=False, note=None, locale="en-US"):
    rows = [_sanitize(item, show_ids) for item in rows if isinstance(item, dict)]
    keys = _public_keys(rows, show_ids)
    columns = [
        {
            "key": key, "label": _label(key, locale), "format": _format_for(key),
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
        if key in PRESENTATION_META_KEYS:
            continue
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


def _catalog_tables(payloads, show_ids, locale="en-US"):
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
        item["topic"] = topic_map.get(topic_id) or t(locale, "unknown_topic")
    return [
        _table(t(locale, "topics"), topics, show_ids, locale=locale),
        _table(t(locale, "prompts"), prompts, show_ids, locale=locale),
    ]


def _lifecycle_table(payloads, show_ids, locale="en-US"):
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
        row["cohort"] = t(locale, "cohort_initial") if index < pivot else t(locale, "cohort_later")
        row["ordinal"] = index + 1
    return _table(
        t(locale, "prompt_lifecycle_cohorts"),
        rows,
        show_ids,
        t(locale, "lifecycle_note"),
        locale,
    )


def _account_table(payloads, show_ids, locale="en-US"):
    account = payloads.get("account") or {}
    rows = [
        {"field": t(locale, "created_at"), "value": account.get("created_at")},
        {"field": t(locale, "account_name"), "value": account.get("name")},
        {"field": t(locale, "phone"), "value": account.get("phone")},
        {"field": t(locale, "email"), "value": account.get("email")},
    ]
    return _table(t(locale, "account_information"), rows, show_ids, locale=locale)


def _collect_tables(payloads, scenario, show_ids=False, locale="en-US"):
    if scenario.name == "catalog":
        return _catalog_tables(payloads, show_ids, locale)
    if scenario.name == "topic-lifecycle":
        return [_lifecycle_table(payloads, show_ids, locale)]
    if scenario.name == "account-info":
        return [_account_table(payloads, show_ids, locale)]
    tables = []
    for alias, payload in payloads.items():
        payload_tables = _payload_lists(payload)
        for key, rows in payload_tables:
            if key in ("kpis", "summary"):
                continue
            tables.append(_table(
                f"{_label(alias, locale)} · {_label(key, locale)}",
                rows[:100],
                show_ids,
                locale=locale,
            ))
            if len(tables) >= 10:
                return tables
        if scenario.density in ("detail", "status") and isinstance(payload, dict):
            safe_payload = _sanitize(payload, show_ids)
            scalar_rows = []
            for key, value in safe_payload.items():
                if key in PRESENTATION_META_KEYS or key == "summary":
                    continue
                if isinstance(value, (dict, list)):
                    continue
                if isinstance(value, str) and len(value) > 500:
                    continue
                scalar_rows.append({"field": _label(key, locale), "value": value})
            if scalar_rows:
                tables.insert(0, _table(
                    t(locale, "details", name=_label(alias, locale)),
                    scalar_rows,
                    show_ids,
                    locale=locale,
                ))
    return tables


def _page_opportunity_rules(payloads, locale="en-US"):
    findings, rows = [], []
    health = payloads.get("health") or {}
    report = health.get("report") if isinstance(health, dict) else None
    report = report or (health if isinstance(health, dict) else {})
    performance_score = report.get("performance_score")
    if performance_score is None:
        performance_score = report.get("performance")
    score = _numeric(performance_score)
    if score is None:
        rows.append({
            "priority": t(locale, "priority_medium"),
            "area": t(locale, "area_performance"),
            "recommendation": t(locale, "recommend_pagespeed_missing"),
        })
    elif score < 50:
        rows.append({
            "priority": t(locale, "priority_high"),
            "area": t(locale, "area_performance"),
            "recommendation": t(locale, "recommend_performance_low"),
        })
    elif score < 90:
        rows.append({
            "priority": t(locale, "priority_medium"),
            "area": t(locale, "area_performance"),
            "recommendation": t(locale, "recommend_performance_medium"),
        })
    kpi = payloads.get("kpi") or {}
    values = kpi.get("kpis") if isinstance(kpi, dict) else {}
    values = values if isinstance(values, dict) else {}
    citation = values.get("ai_citation")
    citation = citation.get("current") if isinstance(citation, dict) else citation
    if _numeric(citation) == 0:
        rows.append({
            "priority": t(locale, "priority_high"),
            "area": t(locale, "area_ai_citations"),
            "recommendation": t(locale, "recommend_citations"),
        })
    training = values.get("ai_training")
    training = training.get("current") if isinstance(training, dict) else training
    if _numeric(training) == 0:
        rows.append({
            "priority": t(locale, "priority_medium"),
            "area": t(locale, "area_crawler_access"),
            "recommendation": t(locale, "recommend_crawler"),
        })
    opportunities = _first_list(payloads.get("opportunities") or {}, ("items", "opportunities"))
    findings.append(t(
        locale,
        "page_checks",
        actions=len(rows),
        opportunities=len(opportunities),
    ))
    return rows, findings


def _insights(metrics, tables, errors, scenario, locale="en-US"):
    if scenario.name == "account-info":
        return [t(locale, "account_loaded")]
    output = []
    comparable = [item for item in metrics if _numeric(item.get("value")) is not None]
    changed = [item for item in comparable if _numeric(item.get("change")) not in (None, 0)]
    if changed:
        item = max(changed, key=lambda row: abs(_numeric(row.get("change"))))
        output.append(t(
            locale,
            "largest_change",
            label=item["label"],
            change=item.get("change"),
        ))
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
                output.append(t(
                    locale,
                    "table_leader",
                    name=leader.get(label_cols[0]["key"]),
                    table=table.get("title"),
                    metric=numeric[0].get("label"),
                ))
                break
    if errors:
        output.append(t(locale, "report_partial", sources=", ".join(errors)))
    if not output:
        output.append(t(locale, "insufficient_data"))
    return output[:3]


def _next_actions(scenario, args, locale="en-US"):
    actions = {
        "visibility": ["next_compare_platform", "next_weakest_topic", "next_citation_sources"],
        "topics": ["next_lowest_topic", "next_topic_prompts", "next_topic_citations"],
        "prompt-performance": ["next_prompt_history", "next_prompt_platform", "next_prompt_urls"],
        "ai-pages": ["next_leading_page", "next_page_opportunities", "next_bot_human"],
        "page-detail": ["next_generate_page_opportunities", "next_page_logs", "next_related_pages"],
        "content-pipeline": ["next_failed_content", "next_latest_content", "next_publish_readiness"],
        "account-info": ["next_projects", "next_integration_health"],
        "competitor-rankings": ["next_competitor_overview", "next_compare_platform", "next_other_window"],
        "competitor-overview": ["next_competitor_topics", "next_compare_platform", "next_other_window"],
        "competitor-topics": ["next_competitor_prompts", "next_compare_platform", "next_other_window"],
        "competitor-prompts": ["next_compare_platform", "next_other_window", "next_competitor_topics"],
    }
    keys = actions.get(
        scenario.name,
        ["next_other_window", "next_narrow_platform", "next_important_row"],
    )
    return [t(locale, key) for key in keys[:3]]


def _mask_path(path, show_ids=False):
    if show_ids:
        return path
    value = str(path)
    patterns = (
        (r"(/projects/)[^/?]+", r"\1<project>"),
        (r"(/competitors/)(?!visibility-rankings(?:[/?]|$))[^/?]+", r"\1<competitor>"),
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
            and not _is_hidden_presentation_key(key)
        }
    if isinstance(value, list):
        return [_sanitize(item, show_ids) for item in value]
    return value


def _load_project_name(client, args, project_scoped):
    if not project_scoped:
        return None
    explicit = str(getattr(args, "project_name", "") or "").strip()
    if explicit:
        return explicit
    try:
        project = client.get(f"/api/projects/{client.project_id}") or {}
    except ApiError:
        return None
    if not isinstance(project, dict):
        return None
    return project.get("name") or project.get("domain") or project.get("url")


def _entity_display_name(scenario, args, entity, payloads, locale):
    if scenario.name.startswith("competitor-"):
        for payload in payloads.values():
            if not isinstance(payload, dict):
                continue
            competitor = payload.get("competitor")
            if isinstance(competitor, dict) and competitor.get("name"):
                return str(competitor["name"])
        if getattr(args, "competitor", None):
            return str(args.competitor)
    if isinstance(entity, dict):
        value = entity.get("name") or entity.get("content") or entity.get("title") or entity.get("path")
        if value:
            return str(value)
    if scenario.name in ("topic-detail", "topic-lifecycle") and args.topic:
        return str(args.topic)
    if scenario.name in ("prompt-performance", "prompt-executions") and args.prompt:
        return str(args.prompt)
    if scenario.name in ("page-detail", "page-health", "page-opportunities") and args.path:
        return str(args.path)
    if scenario.name in ("content-detail", "opportunity-detail"):
        for payload in payloads.values():
            if isinstance(payload, dict):
                value = payload.get("title") or payload.get("name")
                if value:
                    return str(value)
    return None


def _user_facing_title(scenario, locale, project_name, entity_name):
    if entity_name and scenario.name in ("topic-detail", "topic-lifecycle"):
        return t(locale, "title_topic_analysis", entity=entity_name)
    if entity_name and scenario.name in ("prompt-performance", "prompt-executions"):
        return t(locale, "title_prompt_analysis", entity=entity_name)
    if entity_name and scenario.name in ("page-detail", "page-health", "page-opportunities"):
        return t(locale, "title_page_analysis", entity=entity_name)
    if entity_name and scenario.name == "competitor-overview":
        return t(locale, "title_competitor_analysis", entity=entity_name)
    if entity_name and scenario.name == "competitor-topics":
        return t(locale, "title_competitor_topic_analysis", entity=entity_name)
    if entity_name and scenario.name == "competitor-prompts":
        return t(locale, "title_competitor_prompt_analysis", entity=entity_name)
    if project_name:
        project_title = str(project_name)
        if locale == "zh-CN":
            if not project_title.endswith("项目"):
                project_title += "项目"
        elif not project_title.lower().endswith("project"):
            project_title += " Project"
        if scenario.name == "executive-overview":
            return t(locale, "title_project_analysis", project=project_title)
        if scenario.name == "visibility":
            return t(locale, "title_project_visibility", project=project_title)
        scenario_title = scenario.title_zh if locale == "zh-CN" else scenario.title
        return t(locale, "title_project_scenario", project=project_title, scenario=scenario_title)
    return scenario.title_zh if locale == "zh-CN" else scenario.title


def _user_facing_subtitle(scenario, locale, project_name, entity_name):
    if entity_name and scenario.name in ("topic-detail", "topic-lifecycle"):
        return t(locale, "subtitle_topic_entity", entity=entity_name)
    if entity_name and scenario.name in ("prompt-performance", "prompt-executions"):
        return t(locale, "subtitle_prompt_entity", entity=entity_name)
    if entity_name and scenario.name in ("page-detail", "page-health", "page-opportunities"):
        return t(locale, "subtitle_page_entity", entity=entity_name)
    description_key = f"description_{scenario.name}"
    if scenario.description:
        return t(locale, description_key)
    if project_name:
        scenario_title = scenario.title_zh if locale == "zh-CN" else scenario.title
        return t(locale, "subtitle_project_scenario", scenario=scenario_title)
    return t(locale, f"subtitle_{scenario.density}")


def build_report(
    scenario, args, client, payloads, errors, start, end, entity=None,
    resolution=None, native_metadata=None, workflow_warning=None, project_name=None,
):
    locale = normalize_locale(
        args.locale, args.topic, args.prompt, getattr(args, "competitor", None),
    )
    entity_name = _entity_display_name(scenario, args, entity, payloads, locale)
    title = _user_facing_title(scenario, locale, project_name, entity_name)
    subtitle = _user_facing_subtitle(scenario, locale, project_name, entity_name)
    project_scoped = any("{project_id}" in spec.path for spec in scenario.requests)
    project_label = project_name or t(locale, "current_project")
    if project_scoped and args.show_ids:
        project_label = f"{project_label} ({client.project_id})"
    context = [
        {
            "label": t(locale, "project") if project_scoped else t(locale, "account"),
            "value": (
                project_label if project_scoped
                else t(locale, "current_account")
            ),
        },
        {"label": t(locale, "range"), "value": f"{start} → {end}"},
        {"label": t(locale, "period"), "value": args.period},
    ]
    platforms = _platforms(args.platform)
    if platforms:
        context.append({"label": t(locale, "platform"), "value": ", ".join(platforms)})
    if any(spec.paging != "none" for spec in scenario.requests):
        context.extend([
            {"label": t(locale, "page"), "value": args.page},
            {"label": t(locale, "page_size"), "value": args.limit},
        ])
    if entity_name:
        context.append({
            "label": t(locale, "entity"),
            "value": entity_name,
        })
    if scenario.name == "competitor-prompts" and (
        getattr(args, "topic", None) or getattr(args, "topic_id", None)
    ):
        context.append({
            "label": _label("topic", locale),
            "value": getattr(args, "topic", None) or args.topic_id,
        })
    presentation_payloads = _presentation_payloads(payloads, scenario)
    metric_limit = 12 if scenario.name in AI_TRAFFIC_PRESENTATION_SCENARIOS else 8
    metrics = _collect_metrics(
        presentation_payloads, limit=metric_limit, locale=locale,
    )
    charts = _collect_charts(presentation_payloads, scenario, locale)
    tables = _collect_tables(
        presentation_payloads, scenario, args.show_ids, locale,
    )
    extra_insights = []
    if scenario.name == "page-opportunities":
        rows, extra_insights = _page_opportunity_rules(payloads, locale)
        tables.insert(0, _table(
            t(locale, "deterministic_recommendations"),
            rows,
            args.show_ids,
            locale=locale,
        ))
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
        warnings.append(t(locale, "warning_mixed_units"))
    if scenario.name in ("page-health", "page-detail", "page-opportunities"):
        warnings.append(t(locale, "warning_cached_pagespeed"))
    sources = []
    if native_metadata:
        for source in native_metadata.get("sources") or []:
            units = source.get("units") or {}
            sources.append({
                "name": _label(source.get("name"), locale),
                "status": source.get("status"),
                "as_of": source.get("as_of"),
                "units": units,
                "unit": ", ".join(
                    f"{_label(key, locale)}: {localize_unit(value, locale)}"
                    for key, value in units.items()
                ) or localize_unit("records", locale),
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
                "name": _label(spec.alias, locale), "status": status, "as_of": end,
                "unit": localize_unit(SOURCE_UNITS.get(spec.alias, "records"), locale),
            })
    audit_fields = [
        {"label": t(locale, "scenario"), "value": scenario.name},
        {"label": t(locale, "density"), "value": _label(scenario.density, locale)},
        {"label": t(locale, "locale"), "value": locale},
        {"label": t(locale, "timezone"), "value": args.timezone},
        {"label": t(locale, "concurrency_limit"), "value": "4"},
    ]
    if any(spec.paging != "none" for spec in scenario.requests):
        audit_fields.extend([
            {"label": t(locale, "page"), "value": args.page},
            {"label": t(locale, "page_size"), "value": args.limit},
        ])
    if resolution:
        audit_fields.append({"label": t(locale, "entity_resolution"), "value": resolution})
    report = {
        "schema_version": "1.0",
        "report_type": scenario.name,
        "title": title,
        "subtitle": subtitle,
        "generated_at": now_iso(),
        "locale": locale,
        "timezone": args.timezone,
        "context": context,
        "metrics": metrics,
        "charts": charts,
        "tables": tables,
        "insights": (extra_insights + _insights(metrics, tables, errors, scenario, locale))[:3],
        "next_actions": _next_actions(scenario, args, locale),
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
        if requirement == "topic":
            has_topic = bool(args.topic) or (
                scenario.name == "competitor-prompts" and bool(args.topic_id)
            )
            if not has_topic:
                raise ValueError(
                    f"{scenario.name} requires --topic-id or --topic <ID or exact name>"
                )
        if requirement == "prompt" and not (args.prompt_id or args.prompt or args.topic):
            raise ValueError(f"{scenario.name} requires --prompt-id, --prompt, or --topic")
        if requirement == "path" and not args.path:
            raise ValueError(f"{scenario.name} requires --path /page/path")
        if requirement == "resource-id" and not args.resource_id:
            raise ValueError(f"{scenario.name} requires --resource-id")
        if requirement == "competitor" and not (args.competitor_id or args.competitor):
            raise ValueError(
                f"{scenario.name} requires --competitor-id or --competitor <exact name/domain>"
            )


def run_report(args, client=None):
    args.locale = normalize_locale(args.locale, args.topic, args.prompt, args.competitor)
    scenario = get_scenario(args.scenario)
    _validate_requirements(scenario, args)
    if args.page < 1 or args.limit < 1:
        raise ValueError("--page and --limit must be positive integers")
    start, end = _window(args)
    project_required = any("{project_id}" in spec.path for spec in scenario.requests)
    if client is None:
        key, base = get_api_config()
        project_id = get_project_id(args.project_id) if project_required else args.project_id
        client = ReportClient(key, base, project_id)
    project_name = _load_project_name(client, args, project_required)
    values = {
        "project_id": client.project_id,
        "topic_id": "",
        "prompt_id": "",
        "competitor_id": "",
        "filter_topic_ids": [],
        "filter_prompt_ids": [],
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
            native.get("errors") or {},
            start,
            end,
            native.get("entity"),
            native.get("resolution"),
            native_metadata=native.get("metadata"),
            workflow_warning=native.get("warning"),
            project_name=project_name,
        )
    workflow_warning = native.get("warning") if native else None
    if "competitor" in scenario.requires:
        entity, resolution = _resolve_competitor(client, args)
        values["competitor_id"] = quote(str(entity["id"]), safe="")
    if "topic" in scenario.requires and scenario.name == "competitor-prompts":
        if args.topic_id:
            values["topic_id"] = quote(str(args.topic_id), safe="")
        else:
            topic = _resolve_topic(client, args.topic, analytics_params)
            values["topic_id"] = quote(str(topic["id"]), safe="")
    elif "topic" in scenario.requires:
        entity = _resolve_topic(client, args.topic, analytics_params)
        values["topic_id"] = quote(str(entity["id"]), safe="")
        resolution = t(args.locale, "resolution_topic_legacy")
    if "prompt" in scenario.requires:
        entity, resolution = _resolve_prompt(client, args, analytics_params)
        values["prompt_id"] = quote(str(entity.get("id") or entity.get("prompt_id")), safe="")
    if scenario.name == "competitor-overview":
        topic_filters = _platforms(args.filter_topic_id)
        if args.topic_id:
            topic_filters.append(str(args.topic_id))
        elif args.topic:
            topic = _resolve_topic(client, args.topic, analytics_params)
            topic_filters.append(str(topic["id"]))
        prompt_filters = _platforms(args.filter_prompt_id)
        if args.prompt_id:
            prompt_filters.append(str(args.prompt_id))
        values["filter_topic_ids"] = list(dict.fromkeys(topic_filters))
        values["filter_prompt_ids"] = list(dict.fromkeys(prompt_filters))
    payloads, errors = _fetch_scenario(client, scenario, args, start, end, values)
    return build_report(
        scenario, args, client, payloads, errors, start, end, entity, resolution,
        workflow_warning=workflow_warning, project_name=project_name,
    )


def _resolve_output_format(args):
    if args.json:
        return "json"
    if args.format != "auto":
        return args.format
    return get_scenario(args.scenario).default_format


def emit_report(report, args):
    output_format = _resolve_output_format(args)
    if output_format == "json":
        print_json(report)
        return None
    if output_format in ("markdown", "both"):
        print(render_markdown(report), end="")
    path = None
    if output_format in ("html", "both"):
        path = write_html(report, args.output, args.output_dir)
        locale = normalize_locale(report.get("locale"))
        link_label = "打开 HTML 报告" if locale == "zh-CN" else "Open HTML report"
        print(f"\nREPORT_TITLE: {report.get('title')}")
        print(f"REPORT_FILE: {path}")
        print(f"REPORT_PREVIEW: {path}")
        for finding in (report.get("insights") or [])[:3]:
            text = finding.get("body") if isinstance(finding, dict) else finding
            print(f"REPORT_FINDING: {' '.join(str(text).split())}")
        for action in (report.get("next_actions") or [])[:3]:
            print(f"REPORT_NEXT: {' '.join(str(action).split())}")
        print(f"REPORT_LINK: [{link_label}](<{path}>)")
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Adgine GEO scenario reports (scenario-aware HTML or inline output)"
    )
    parser.add_argument("scenario", nargs="?", choices=sorted(SCENARIOS), help="Report scenario")
    parser.add_argument("--list-scenarios", action="store_true", help="List all P1-P3 report scenarios")
    parser.add_argument("--project-id", help="Project ID, or use GEO_PROJECT_ID")
    parser.add_argument("--project-name", help="Known project name for the report title; otherwise loaded from GEO-Api")
    parser.add_argument("--period", choices=["7d", "14d", "30d", "90d"], default="7d")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD; defaults to yesterday")
    parser.add_argument("--granularity", choices=["day", "week", "month"], default="day")
    parser.add_argument("--platform", action="append", help="Platform code; repeat or use comma-separated values")
    parser.add_argument("--topic", help="Topic ID or exact name")
    parser.add_argument("--topic-id", help="Explicit Topic ID (fastest for competitor reports)")
    parser.add_argument("--prompt", help="Prompt ID or text")
    parser.add_argument("--prompt-id", help="Explicit Prompt ID (fastest)")
    parser.add_argument("--filter-topic-id", action="append", help="Optional Topic ID filter for competitor overview; repeat or comma-separate")
    parser.add_argument("--filter-prompt-id", action="append", help="Optional Prompt ID filter for competitor overview; repeat or comma-separate")
    parser.add_argument("--competitor", help="Competitor ID, exact name, or exact domain")
    parser.add_argument("--competitor-id", help="Explicit competitor relation ID (fastest)")
    parser.add_argument("--type", dest="prompt_type", action="append", help="Prompt type filter; repeat or comma-separate (defaults to visibility)")
    parser.add_argument("--tag-id", action="append", help="Topic tag UUID filter; repeat or comma-separate")
    parser.add_argument("--prompt-index", type=int, default=1, help="Stable 1-based index within Topic")
    parser.add_argument("--path", help="Exact website path beginning with /")
    parser.add_argument("--resource-id", help="Opportunity/content/task identifier")
    parser.add_argument("--metric", choices=["visibility", "visibility_score", "sov", "share_of_voice"])
    parser.add_argument("--page", type=int, default=1, help="1-based result page")
    parser.add_argument("--limit", type=int, default=DEFAULT_PAGE_SIZE, help="Rows per page (default: 40)")
    parser.add_argument(
        "--locale",
        default=os.environ.get("GEO_REPORT_LOCALE", "auto"),
        help="Report language: auto, en-US, or zh-CN (default: auto)",
    )
    parser.add_argument("--timezone", default=os.environ.get("GEO_REPORT_TIMEZONE", "UTC"))
    parser.add_argument(
        "--format",
        choices=["auto", "html", "markdown", "json", "both"],
        default="auto",
        help="Output format; auto uses the scenario default",
    )
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
