import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

os.environ.setdefault("GEO_SKIP_VERSION_CHECK", "1")
SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from _reporting import _render_scatter, render_html, render_markdown, write_html  # noqa: E402
from _contracts import SCENARIOS, get_scenario  # noqa: E402
from _i18n import label, normalize_locale  # noqa: E402
from report import (  # noqa: E402
    SUPPORTED_CHART_TYPES,
    _collect_charts,
    _mask_path,
    _presentation_payloads,
    _sanitize,
    _table,
    build_report,
    emit_report,
)


def sample_report():
    return {
        "schema_version": "1.0",
        "report_type": "visibility",
        "locale": "en-US",
        "title": "Visibility <Report>",
        "subtitle": "Offline & auditable",
        "generated_at": "2026-08-19T10:00:00+08:00",
        "context": [{"label": "Range", "value": "2026-08-01 → 2026-08-07"}],
        "metrics": [{"label": "Visibility", "value": 42.5, "change": 3.2, "format": "percent", "direction": "good"}],
        "charts": [{"type": "bar", "title": "Brands", "items": [{"label": "A very long brand", "value": 42.5}], "format": "percent"}],
        "tables": [{"title": "Rows", "columns": [{"key": "name", "label": "Name"}, {"key": "score", "label": "Score", "align": "right", "format": "percent"}], "rows": [{"name": "A&B", "score": 42.5}]}],
        "insights": ["Visibility increased."],
        "next_actions": ["Compare platforms"],
        "coverage": {"requested_range": {"from": "2026-08-01", "to": "2026-08-07"}, "sources": [{"name": "visibility", "status": "ok", "as_of": "2026-08-07", "unit": "percent"}]},
        "audit": {"fields": [], "api_calls": [], "warnings": []},
    }


class RenderingTests(unittest.TestCase):
    def test_competitor_audit_masks_ids_but_keeps_static_ranking_route(self):
        self.assertEqual(
            _mask_path("/api/projects/p/competitors/visibility-rankings"),
            "/api/projects/<project>/competitors/visibility-rankings",
        )
        self.assertEqual(
            _mask_path("/api/projects/p/competitors/c/overview"),
            "/api/projects/<project>/competitors/<competitor>/overview",
        )

    def test_html_is_offline_escaped_and_embeds_public_json(self):
        rendered = render_html(sample_report())
        self.assertIn("Visibility &lt;Report&gt;", rendered)
        self.assertIn("A&amp;B", rendered)
        self.assertNotIn("https://cdn", rendered)
        self.assertIn('id="adgine-report-data"', rendered)
        embedded = rendered.split('id="adgine-report-data">', 1)[1].split("</script>", 1)[0]
        data = json.loads(embedded)
        self.assertNotIn("next_actions", data)
        self.assertNotIn("schema_version", data)
        self.assertNotIn("coverage", data)
        self.assertNotIn("audit", data)
        self.assertNotIn("schema", rendered.lower())
        self.assertNotIn("Data coverage", rendered)
        self.assertNotIn("Query audit", rendered)

    def test_write_html_uses_requested_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_html(sample_report(), output_dir=directory)
            self.assertTrue(os.path.isfile(path))
            self.assertTrue(path.startswith(directory))

    def test_html_emits_mandatory_workbuddy_link(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(
                json=False,
                format="html",
                output=None,
                output_dir=directory,
                scenario="visibility",
            )
            stream = io.StringIO()
            with redirect_stdout(stream):
                path = emit_report(sample_report(), args)
            output = stream.getvalue()
            self.assertTrue(os.path.isfile(path))
            self.assertIn(f"REPORT_FILE: {path}", output)
            self.assertIn(f"REPORT_PREVIEW: {path}", output)
            link = f"REPORT_LINK: [Open HTML report](<{path}>)"
            self.assertIn(link, output)
            self.assertTrue(output.rstrip().endswith(link))
            self.assertLess(output.index("REPORT_FINDING:"), output.index(link))
            self.assertLess(output.index("REPORT_NEXT:"), output.index(link))

    def test_chinese_html_emits_localized_workbuddy_link(self):
        report = sample_report()
        report["locale"] = "zh-CN"
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(
                json=False,
                format="html",
                output=None,
                output_dir=directory,
                scenario="visibility",
            )
            stream = io.StringIO()
            with redirect_stdout(stream):
                path = emit_report(report, args)
            link = f"REPORT_LINK: [打开 HTML 报告](<{path}>)"
            output = stream.getvalue()
            self.assertIn(link, output)
            self.assertTrue(output.rstrip().endswith(link))

    def test_chinese_html_localizes_shared_report_chrome(self):
        report = sample_report()
        report.update({
            "locale": "zh-CN",
            "title": "AI 可见性分析",
            "subtitle": "只读分析报告",
            "context": [{"label": "日期范围", "value": "2026-08-01 → 2026-08-07"}],
            "metrics": [{
                "label": "AI 可见性得分", "value": 42.5, "change": 3.2,
                "format": "percent", "direction": "good",
            }],
            "insights": ["AI 可见性得分有所提升。"],
        })
        rendered = render_html(report)
        self.assertIn('<html lang="zh-CN">', rendered)
        self.assertIn("Adgine GEO · 国际版报告", rendered)
        self.assertIn("较上一周期 +3.2%", rendered)
        self.assertIn("核心发现", rendered)
        self.assertNotIn("数据覆盖情况", rendered)
        self.assertNotIn("查询审计与数据质量", rendered)
        self.assertNotIn("Schema", rendered)
        self.assertNotIn("数据源", rendered)
        self.assertNotIn("Key findings", rendered)

    def test_locale_auto_and_field_labels_support_chinese_and_english(self):
        self.assertEqual(normalize_locale("auto", "主题最近一周表现"), "zh-CN")
        self.assertEqual(normalize_locale("auto", "Topic performance last week"), "en-US")
        self.assertEqual(normalize_locale("en-US", "中文请求"), "en-US")
        self.assertEqual(label("visibility_score", "zh-CN"), "AI 可见性得分")
        self.assertEqual(label("visibility_score", "en-US"), "Visibility Score")

    def test_all_scenarios_build_in_both_supported_languages(self):
        client = SimpleNamespace(project_id="project-id", calls=[])
        base_args = {
            "topic": None,
            "prompt": None,
            "show_ids": False,
            "platform": [],
            "page": 1,
            "limit": 40,
            "path": None,
            "period": "7d",
            "timezone": "UTC",
        }
        for scenario in SCENARIOS.values():
            for locale in ("en-US", "zh-CN"):
                with self.subTest(scenario=scenario.name, locale=locale):
                    args = SimpleNamespace(locale=locale, **base_args)
                    report = build_report(
                        scenario, args, client, {}, {}, "2026-08-01", "2026-08-07",
                    )
                    expected_title = scenario.title_zh if locale == "zh-CN" else scenario.title
                    self.assertEqual(report["title"], expected_title)
                    self.assertEqual(report["locale"], locale)
                    rendered = render_html(report)
                    self.assertIn(f'<html lang="{locale}">', rendered)
                    self.assertNotIn("{{", rendered)

    def test_markdown_uses_same_contract(self):
        rendered = render_markdown(sample_report())
        self.assertIn("42.5%", rendered)
        self.assertIn("## Rows", rendered)

    def test_ids_optional_but_secrets_always_removed(self):
        value = {"project_id": "p", "nested": {"wp_password": "secret", "name": "ok"}}
        self.assertNotIn("project_id", _sanitize(value, False))
        debug = _sanitize(value, True)
        self.assertEqual(debug["project_id"], "p")
        self.assertNotIn("wp_password", debug["nested"])

    def test_nested_secrets_are_removed_before_table_serialization(self):
        table = _table(
            "Integrations",
            [{"service": "wordpress", "extra_data": {"wp_password": "secret", "site": "example.test"}}],
        )
        self.assertNotIn("secret", json.dumps(table))
        self.assertIn("example.test", json.dumps(table))

    def test_ai_kpi_daily_series_become_line_charts(self):
        payloads = {
            "overview": {
                "kpis": [
                    {
                        "key": "ai_citation",
                        "label": "AI Citation",
                        "current": 3,
                        "daily": [
                            {"date": "2026-08-18", "value": 1},
                            {"date": "2026-08-19", "value": 2},
                        ],
                    }
                ]
            }
        }
        charts = _collect_charts(payloads, get_scenario("ai-bots"))
        self.assertEqual(charts[0]["type"], "line_chart")
        self.assertEqual(charts[0]["series"][0]["points"][1]["y"], 2)

    def test_nested_metric_renders_current_and_previous_lines(self):
        payloads = {
            "report_data": {
                "metrics": {
                    "visibility_score": {
                        "trend": [{"date": "2026-08-18", "value": 40}],
                        "prev_trend": [{"date": "2026-08-11", "value": 35}],
                    }
                }
            }
        }
        charts = _collect_charts(payloads, get_scenario("topic-detail"), "en-US")
        self.assertEqual(charts[0]["type"], "line_chart")
        self.assertEqual(charts[0]["format"], "percent")
        self.assertEqual(len(charts[0]["series"]), 2)
        self.assertTrue(charts[0]["series"][1]["dash"])

    def test_executive_traffic_trends_use_backend_metric_fields_and_hide_worker(self):
        payloads = {
            "report_data": {
                "traffic": {
                    "ga4": {
                        "daily": [
                            {"date": "2026-08-18", "sessions": 12, "active_users": 9, "page_views": 20},
                            {"date": "2026-08-19", "sessions": 15, "active_users": 11, "page_views": 27},
                        ],
                        "ai_referrals": {
                            "daily": [
                                {"date": "2026-08-18", "sessions": 2, "active_users": 2},
                                {"date": "2026-08-19", "sessions": 4, "active_users": 3},
                            ],
                        },
                    },
                    "cloudflare": {
                        "daily": [
                            {"date": "2026-08-18", "requests_total": 120, "requests_cached": 72, "page_views": 18},
                            {"date": "2026-08-19", "requests_total": 160, "requests_cached": 96, "page_views": 24},
                        ],
                    },
                    "worker": {
                        "daily": [
                            {"date": "2026-08-18", "traffic_type": "ai_search", "requests": 7},
                        ],
                    },
                },
            },
        }
        charts = _collect_charts(payloads, get_scenario("executive-overview"), "zh-CN")
        by_title = {chart["title"]: chart for chart in charts}

        self.assertEqual(
            [point["y"] for point in by_title["GA4趋势"]["series"][0]["points"]],
            [12, 15],
        )
        self.assertEqual(len(by_title["GA4趋势"]["series"]), 3)
        self.assertEqual(
            [point["y"] for point in by_title["AI 引荐趋势"]["series"][0]["points"]],
            [2, 4],
        )
        self.assertEqual(
            [point["y"] for point in by_title["Cloudflare趋势"]["series"][0]["points"]],
            [120, 160],
        )
        self.assertNotIn("Worker趋势", by_title)
        self.assertNotIn("Worker趋势", render_html({**sample_report(), "locale": "zh-CN", "charts": charts}))

    def test_dedicated_worker_report_keeps_its_requested_trend(self):
        charts = _collect_charts({
            "worker": {
                "daily": [
                    {"date": "2026-08-18", "traffic_type": "ai_search", "requests": 7},
                    {"date": "2026-08-19", "traffic_type": "ai_search", "requests": 9},
                ],
            },
        }, get_scenario("worker-traffic"), "zh-CN")
        worker = next(chart for chart in charts if chart["title"] == "Worker趋势")
        self.assertEqual([point["y"] for point in worker["series"][0]["points"]], [7, 9])

    def test_customer_traffic_projection_keeps_only_supported_ai_metrics(self):
        payloads = {
            "report_data": {
                "traffic": {
                    "ga4": {
                        "total_sessions": {"current": 1000},
                        "ai_referrals": {
                            "total_sessions": 30,
                            "total_active_users": 22,
                            "ai_referral_rate": 0.03,
                            "daily": [{"date": "2026-08-19", "sessions": 5, "active_users": 4}],
                            "items": [{"source": "chatgpt.com", "sessions": 20, "page_views": 40}],
                        },
                    },
                    "cloudflare": {"total_requests": {"current": 5000}},
                    "worker": {"daily": [{"date": "2026-08-19", "requests": 12}]},
                },
                "revenue": 999,
                "transactions": 8,
            },
            "cloudflare_ai": {
                "ai_citations": {
                    "current": 12, "prev": 8, "delta": 4,
                    "daily": [{"date": "2026-08-19", "value": 12}],
                    "prev_daily": [{"date": "2026-08-19", "value": 8}],
                },
                "ai_index": {"current": 20, "prev": 15, "delta": 5, "daily": []},
                "ai_training": {"current": 9, "prev": 10, "delta": -1, "daily": []},
                "human_referrals": {"current": 7},
                "platform_leaderboards": {
                    "ai_citations": [{"platform_id": "openai", "display_name": "OpenAI", "requests": 8}],
                    "ai_index": [{"platform_id": "openai", "display_name": "OpenAI", "requests": 6}],
                    "ai_training": [{"platform_id": "anthropic", "display_name": "Anthropic", "requests": 4}],
                },
            },
        }
        projected = _presentation_payloads(
            payloads, get_scenario("executive-overview"),
        )

        self.assertEqual(set(projected["ga4_ai"]["metrics"]), {
            "ai_referral_sessions", "ai_referral_users", "ai_referral_rate",
        })
        self.assertEqual(projected["ga4_ai"]["metrics"]["ai_referral_rate"], 3)
        self.assertEqual(set(projected["cloudflare_ai"]["metrics"]), {
            "ai_assistant", "ai_search", "ai_training",
        })
        rendered = json.dumps(projected, ensure_ascii=False)
        for hidden in (
            "revenue", "transactions", "total_requests", "page_views",
            "human_referrals", "worker",
        ):
            self.assertNotIn(hidden, rendered)
        charts = _collect_charts(projected, get_scenario("executive-overview"), "zh-CN")
        platform = next(
            chart for chart in charts
            if chart["title"] == "Cloudflare AI 平台分布"
        )
        self.assertEqual(platform["type"], "heatmap_table")
        self.assertEqual(
            platform["columns"],
            ["AI 助手访问", "AI 搜索抓取", "AI 训练抓取"],
        )
        assistant = next(
            chart for chart in charts if chart["title"] == "AI 助手访问趋势"
        )
        self.assertEqual(len(assistant["series"]), 2)
        self.assertTrue(assistant["series"][1]["dash"])

    def test_revenue_and_transactions_are_always_removed_from_reports(self):
        sanitized = _sanitize({
            "name": "Example",
            "revenue": 100,
            "purchase_revenue": 80,
            "transactions": 3,
            "nested": {"transaction_count": 3, "sessions": 9},
        }, True)
        self.assertEqual(sanitized, {
            "name": "Example", "nested": {"sessions": 9},
        })

    def test_distribution_becomes_donut_chart(self):
        payloads = {
            "report_data": {
                "summary": {
                    "status_counts": {"completed": 7, "failed": 2, "pending": 1},
                }
            }
        }
        charts = _collect_charts(payloads, get_scenario("content-pipeline"), "zh-CN")
        donut = next(chart for chart in charts if chart["type"] == "pie_chart")
        self.assertNotIn("摘要", donut["title"])
        rendered = render_html({**sample_report(), "locale": "zh-CN", "charts": [donut]})
        self.assertIn('class="donut-layout"', rendered)

    def test_standard_chart_type_contract_is_complete(self):
        self.assertEqual(set(SUPPORTED_CHART_TYPES), {
            "bar_chart", "line_chart", "pie_chart", "gauge", "funnel",
            "scatter_plot", "treemap", "heatmap_table", "progress_bar", "timeline",
        })

    def test_all_standard_chart_types_render_offline(self):
        charts = [
            {"type": "bar_chart", "title": "Bar", "items": [{"label": "A", "value": 3}]},
            {"type": "line_chart", "title": "Line", "series": [{"name": "A", "points": [{"x": "2026-08-19", "y": 3}]}]},
            {"type": "pie_chart", "title": "Pie", "items": [{"label": "A", "value": 3}, {"label": "B", "value": 2}]},
            {"type": "gauge", "title": "Gauge", "value": 72, "format": "percent"},
            {"type": "funnel", "title": "Funnel", "items": [{"label": "Visit", "value": 100}, {"label": "Lead", "value": 40}]},
            {"type": "scatter_plot", "title": "Scatter", "x_label": "X", "y_label": "Y", "points": [{"label": "A", "x": 1, "y": 2}]},
            {"type": "treemap", "title": "Treemap", "items": [{"label": "A", "value": 3}, {"label": "B", "value": 2}]},
            {"type": "heatmap_table", "title": "Heatmap", "columns": ["X"], "rows": [{"label": "A", "values": {"X": 3}}]},
            {"type": "progress_bar", "title": "Progress", "items": [{"label": "A", "value": 72, "max": 100}], "format": "percent"},
            {"type": "timeline", "title": "Timeline", "items": [{"date": "2026-08-19", "label": "Created", "status": "completed"}]},
        ]
        rendered = render_html({**sample_report(), "charts": charts})
        for chart_type in SUPPORTED_CHART_TYPES:
            self.assertIn(f'data-chart-type="{chart_type}"', rendered)
        self.assertNotIn("https://cdn", rendered)

    def test_scatter_renders_formatted_ticks_and_reverses_position_axis(self):
        rendered = _render_scatter({
            "x_label": "AI Visibility Score",
            "y_label": "Average Position",
            "x_format": "percent",
            "x_min": 0,
            "x_max": 100,
            "y_min": 1,
            "y_max": 5,
            "y_reverse": True,
            "points": [
                {"label": "Best", "x": 25, "y": 1},
                {"label": "Worst", "x": 75, "y": 5},
            ],
        })
        self.assertIn('class="svg-value axis-tick x-tick">0.0%</text>', rendered)
        self.assertIn('class="svg-value axis-tick x-tick">100.0%</text>', rendered)
        self.assertIn('class="svg-value axis-tick y-tick">1</text>', rendered)
        self.assertIn('class="svg-value axis-tick y-tick">5</text>', rendered)
        self.assertIn('<circle cx="241.5" cy="24.0"', rendered)
        self.assertIn('<circle cx="568.5" cy="288.0"', rendered)

    def test_data_shape_selects_gauge_progress_funnel_scatter_treemap_and_timeline(self):
        bounded = _collect_charts({
            "report_data": {
                "metrics": {
                    "visibility_score": {"current": 72},
                    "share_of_voice": {"current": 18},
                }
            }
        }, get_scenario("visibility"), "en-US")
        self.assertIn("gauge", {chart["type"] for chart in bounded})
        self.assertIn("progress_bar", {chart["type"] for chart in bounded})

        funnel = _collect_charts({
            "flow": {"conversion_funnel": {"visits": 100, "leads": 40, "customers": 10}}
        }, get_scenario("ai-flow"), "en-US")
        self.assertIn("funnel", {chart["type"] for chart in funnel})

        rows = [
            {"path": f"/p/{index}", "sessions": 100 - index * 10, "page_views": 150 - index * 8}
            for index in range(4)
        ]
        page_charts = _collect_charts({"pages": {"pages": rows}}, get_scenario("ga4-pages"), "en-US")
        self.assertIn("treemap", {chart["type"] for chart in page_charts})
        self.assertIn("scatter_plot", {chart["type"] for chart in page_charts})

        relationship_rows = [
            {"name": f"Topic {index}", "visibility_score": 20 + index * 10, "average_position": index + 1}
            for index in range(4)
        ]
        relationship_charts = _collect_charts(
            {"topics": {"items": relationship_rows}}, get_scenario("topics"), "en-US",
        )
        relationship = next(chart for chart in relationship_charts if chart["type"] == "scatter_plot")
        self.assertEqual((relationship["x_min"], relationship["x_max"]), (0, 100))
        self.assertEqual((relationship["y_min"], relationship["y_max"]), (1, 4))
        self.assertTrue(relationship["y_reverse"])

        timeline = _collect_charts({
            "jobs": {"jobs": [
                {"type": "outline", "status": "completed", "created_at": "2026-08-19T10:00:00Z"},
                {"type": "article", "status": "running", "created_at": "2026-08-19T11:00:00Z"},
            ]}
        }, get_scenario("content-pipeline"), "en-US")
        self.assertIn("timeline", {chart["type"] for chart in timeline})


if __name__ == "__main__":
    unittest.main()
