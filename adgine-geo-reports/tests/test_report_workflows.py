import os
import re
import sys
import tempfile
import unittest

os.environ.setdefault("GEO_SKIP_VERSION_CHECK", "1")
SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from report import _resolve_output_format, parse_args, run_report  # noqa: E402
from _client import ApiError  # noqa: E402
from _reporting import render_html  # noqa: E402


def visible_html(rendered):
    """Return only markup that can contribute visible report content."""
    return re.sub(r"<script\b[^>]*>.*?</script>", "", rendered, flags=re.IGNORECASE | re.DOTALL)


class FakeClient:
    def __init__(self):
        self.project_id = "project-secret-id"
        self.base = "https://api.example.test"
        self.calls = []

    def get(self, path, params=None):
        self.calls.append({"path": path, "params": params, "duration_ms": 1, "status": "ok"})
        if path == "/api/projects/project-secret-id":
            return {"id": "project-secret-id", "name": "Coffee Lab", "domain": "coffee.example"}
        if path == "/api/auth/me":
            return {
                "id": "user-secret-id",
                "created_at": "2025-01-02T03:04:05Z",
                "name": "Alice Example",
                "phone": "+1 555 0100",
                "email": "alice@example.test",
                "subscription": {"plan": "secret-plan"},
                "rules": ["unrelated-rule"],
            }
        if path == "/api/projects/project-secret-id/competitors":
            return {
                "items": [{
                    "id": "competitor-secret-id",
                    "project_id": "project-secret-id",
                    "name": "Acme",
                    "domain": "https://www.acme.example/",
                }],
                "total": 1,
            }
        if path.endswith("/competitors/visibility-rankings"):
            return {
                "date_range": {"from": "2026-08-12", "to": "2026-08-18"},
                "competitors": [
                    {"rank": 1, "competitor_id": "competitor-secret-id", "name": "Acme", "domain": "acme.example", "is_our_brand": False, "current": 61.5},
                    {"rank": 2, "competitor_id": "our-secret-id", "name": "Coffee Lab", "domain": "coffee.example", "is_our_brand": True, "current": 48.0},
                ],
            }
        if path.endswith("/competitors/competitor-secret-id/overview"):
            return {
                "competitor_id": "competitor-secret-id",
                "competitor": {"name": "Acme", "domain": "acme.example"},
                "our_brand": {"name": "Coffee Lab", "domain": "coffee.example"},
                "visibility": {
                    "competitor": {"visibility_score": 61.5, "share_of_voice": 32.0},
                    "ours": {"visibility_score": 48.0, "share_of_voice": 25.0},
                },
                "sentiment": {
                    "competitor": {"positive": 60, "neutral": 30, "negative": 10, "classified_count": 10, "unclassified_count": 2},
                    "ours": {"positive": 55, "neutral": 35, "negative": 10, "classified_count": 8, "unclassified_count": 1},
                },
                "topic_rankings": [{
                    "topic_id": "topic-secret-id", "topic_name": "Coffee", "prompt_count": 4,
                    "competitor": {"rank": 1, "score": 65}, "ours": {"rank": 2, "score": 52},
                }],
            }
        if path.endswith("/competitors/competitor-secret-id/topics"):
            return {
                "competitor": {"competitor_id": "competitor-secret-id", "name": "Acme", "domain": "acme.example"},
                "items": [{"topic_id": "topic-secret-id", "name": "Coffee", "prompt_count": 4, "visibility_score": 65, "visibility_rank": 1, "share_of_voice": 35, "average_position": 1.5, "executions": 12}],
            }
        if path.endswith("/competitors/competitor-secret-id/topics/topic-secret-id/prompts"):
            return {
                "competitor": {"competitor_id": "competitor-secret-id", "name": "Acme", "domain": "acme.example"},
                "topic": {"id": "topic-secret-id", "name": "Coffee"},
                "items": [{"prompt_id": "prompt-secret-id", "content": "Best coffee?", "platforms": ["openai"], "visibility_score": 70, "visibility_rank": 1, "share_of_voice": 40, "average_position": 1.2, "executions": 5}],
            }
        if path.endswith("/report-data/capabilities"):
            return {
                "schema_version": "1.0",
                "features": {
                    "topic_performance": True,
                    "prompt_performance": True,
                },
            }
        if path.endswith("/report-data/topic-performance"):
            topic_name = (params or {}).get("q") or "Coffee"
            return {
                "schema_version": "1.0",
                "requested_range": {"from": "2026-08-05", "to": "2026-08-18"},
                "effective_range": {"from": "2026-08-05", "to": "2026-08-18"},
                "as_of": "2026-08-19T00:00:00Z",
                "partial": False,
                "warnings": [],
                "sources": [{
                    "name": "citation_tests", "status": "available",
                    "units": {"visibility_score": "percent"},
                    "date_basis": "analyzed_at",
                }],
                "topic": {"id": "topic-secret-id", "name": topic_name},
                "metrics": {"visibility_score": {"current": 30, "previous": 20, "change": 10, "unit": "percent"}},
                "prompts": [{"prompt_id": "prompt-secret-id", "content": "Best coffee?", "visibility_score": 40}],
            }
        if path.endswith("/report-data/prompt-performance"):
            return {
                "schema_version": "1.0",
                "requested_range": {"from": "2026-08-05", "to": "2026-08-18"},
                "effective_range": {"from": "2026-08-05", "to": "2026-08-18"},
                "as_of": "2026-08-19T00:00:00Z",
                "partial": False,
                "warnings": [],
                "sources": [{
                    "name": "citation_tests", "status": "available",
                    "units": {"visibility_score": "percent"},
                    "date_basis": "analyzed_at",
                }],
                "prompt": {"id": "prompt-secret-id", "content": "Best coffee?"},
                "visibility_score": {"current": 40, "previous": 35, "change": 5, "unit": "percent"},
                "average_position": {"current": 2, "previous": 3, "change": -1, "unit": "rank"},
            }
        if path.endswith("/analytics/topics"):
            return {"items": [{"topic_id": "topic-secret-id", "name": "Coffee", "visibility_score": 30}]}
        if "/analytics/topics/topic-secret-id/prompts" in path:
            return {"topic": {"id": "topic-secret-id", "name": "Coffee"}, "items": [{"prompt_id": "prompt-secret-id", "content": "Best coffee?", "visibility_score": 40, "executions": 5}]}
        if "/analytics/prompts/" in path and path.endswith("/overview"):
            return {"prompt": {"id": "prompt-secret-id", "content": "Best coffee?"}, "visibility_score": {"current": 40, "change": 5, "trend": []}, "average_position": {"current": 2, "change": -1, "trend": []}}
        if path.endswith("/analytics/visibility"):
            return {"visibility_score": {"current": 50, "change": 2, "trend": [{"date": "2026-08-18", "value": 50}]}, "share_of_voice": {"current": 20, "change": 1}}
        if path.endswith("/integrations/ga4/pages"):
            return {"items": [{"path": "/coffee", "page_views": 12}], "total": 1}
        raise AssertionError(f"Unexpected path: {path}")

    def fetch_all(self, path, params=None, paging="page", limit=40, max_items=1000):
        self.calls.append({"path": path, "params": params, "duration_ms": 1, "status": "ok"})
        if path.endswith("/prompts"):
            return {"items": [{"id": "prompt-secret-id", "content": "Best coffee?"}], "total": 1}
        raise AssertionError(f"Unexpected paginated path: {path}")


class FailingReportDataClient(FakeClient):
    def __init__(self, failure):
        super().__init__()
        self.base += f"/{failure.status_code}-{(failure.payload or {}).get('code')}"
        self.failure = failure

    def get(self, path, params=None):
        if path.endswith("/report-data/prompt-performance"):
            self.calls.append({"path": path, "params": params, "duration_ms": 1, "status": "error"})
            raise self.failure
        return super().get(path, params)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.cache_dir = tempfile.TemporaryDirectory()
        os.environ["GEO_REPORT_CACHE_DIR"] = self.cache_dir.name

    def tearDown(self):
        self.cache_dir.cleanup()
        os.environ.pop("GEO_REPORT_CACHE_DIR", None)

    def test_visibility_loads_project_name_and_business_data(self):
        client = FakeClient()
        args = parse_args(["visibility", "--period", "7d"])
        report = run_report(args, client=client)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(report["report_type"], "visibility")
        self.assertEqual(report["title"], "Coffee Lab Project Visibility Analysis")
        self.assertEqual(report["context"][0]["value"], "Coffee Lab")
        self.assertNotIn("project-secret-id", str(report))

    def test_scenario_defaults_choose_inline_only_for_small_results(self):
        for scenario in ("projects", "account-info", "worker-deployment", "saas-task", "opportunity-detail"):
            with self.subTest(scenario=scenario):
                args = parse_args([scenario])
                self.assertEqual(_resolve_output_format(args), "markdown")
        self.assertEqual(
            _resolve_output_format(parse_args(["visibility"])),
            "html",
        )

    def test_explicit_format_overrides_scenario_default(self):
        args = parse_args(["account-info", "--format", "html"])
        self.assertEqual(_resolve_output_format(args), "html")
        args = parse_args(["visibility", "--format", "markdown"])
        self.assertEqual(_resolve_output_format(args), "markdown")
        args = parse_args(["account-info", "--json"])
        self.assertEqual(_resolve_output_format(args), "json")

    def test_prompt_id_uses_capability_plus_one_business_call(self):
        client = FakeClient()
        prompt_id = "11111111-1111-4111-8111-111111111111"
        args = parse_args(["prompt-performance", "--prompt-id", prompt_id, "--period", "14d"])
        report = run_report(args, client=client)
        self.assertEqual(len(client.calls), 3)
        self.assertTrue(client.calls[2]["path"].endswith("/report-data/prompt-performance"))
        self.assertEqual(client.calls[2]["params"]["prompt_id"], prompt_id)
        self.assertEqual(report["title"], "Prompt Analysis: Best coffee?")
        self.assertEqual(report["context"][-1]["value"], "Best coffee?")

    def test_topic_name_is_two_calls_and_ids_are_hidden(self):
        client = FakeClient()
        args = parse_args(["topic-detail", "--topic", "Coffee", "--period", "14d"])
        report = run_report(args, client=client)
        self.assertEqual(len(client.calls), 3)
        self.assertTrue(client.calls[2]["path"].endswith("/report-data/topic-performance"))
        self.assertEqual(client.calls[2]["params"]["q"], "Coffee")
        self.assertNotIn("topic-secret-id", str(report))
        self.assertIn("Coffee", str(report))
        self.assertEqual(report["coverage"]["sources"][0]["date_basis"], "analyzed_at")
        html = render_html(report)
        self.assertIn("Coffee", html)
        self.assertNotIn("citation_tests", html)

    def test_chinese_topic_auto_generates_fully_localized_report(self):
        client = FakeClient()
        args = parse_args([
            "topic-detail", "--topic", "数独游戏网站", "--period", "7d",
            "--locale", "auto",
        ])
        report = run_report(args, client=client)
        self.assertEqual(report["locale"], "zh-CN")
        self.assertEqual(report["title"], "主题分析：数独游戏网站")
        self.assertEqual(report["context"][0]["label"], "项目")
        self.assertEqual(report["metrics"][0]["label"], "AI 可见性得分")
        self.assertIn("对比", report["next_actions"][0])
        html = render_html(report)
        visible = visible_html(html)
        for expected in ("核心发现", "生成时间"):
            self.assertIn(expected, visible)
        for hidden in ("数据覆盖情况", "查询审计与数据质量", "Schema", "数据源"):
            self.assertNotIn(hidden, visible)
        self.assertNotIn("Key findings", visible)

    def test_explicit_english_overrides_chinese_entity_text(self):
        client = FakeClient()
        args = parse_args([
            "topic-detail", "--topic", "数独游戏网站", "--locale", "en-US",
        ])
        report = run_report(args, client=client)
        self.assertEqual(report["locale"], "en-US")
        self.assertEqual(report["title"], "Topic Analysis: 数独游戏网站")
        self.assertEqual(report["context"][0]["label"], "Project")

    def test_report_data_5xx_does_not_fall_back(self):
        client = FailingReportDataClient(ApiError("down", status_code=503, payload={"code": 50304}))
        with self.assertRaises(ApiError):
            run_report(parse_args([
                "prompt-performance", "--prompt-id", "11111111-1111-4111-8111-111111111111",
            ]), client=client)
        self.assertEqual(len(client.calls), 3)

    def test_entity_404_does_not_fall_back(self):
        client = FailingReportDataClient(ApiError("missing", status_code=404, payload={"code": 40406}))
        with self.assertRaises(ApiError):
            run_report(parse_args([
                "prompt-performance", "--prompt-id", "11111111-1111-4111-8111-111111111111",
            ]), client=client)
        self.assertEqual(len(client.calls), 3)

    def test_route_404_uses_legacy_endpoint_with_warning(self):
        client = FailingReportDataClient(ApiError("route missing", status_code=404, payload={"code": 40400}))
        report = run_report(parse_args([
            "prompt-performance", "--prompt-id", "11111111-1111-4111-8111-111111111111",
        ]), client=client)
        self.assertEqual(len(client.calls), 4)
        self.assertIn("legacy API workflow", " ".join(report["audit"]["warnings"]))

    def test_account_info_exposes_only_requested_profile_fields(self):
        client = FakeClient()
        report = run_report(parse_args(["account-info"]), client=client)
        rendered = str(report)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["path"], "/api/auth/me")
        for expected in ("2025-01-02T03:04:05Z", "Alice Example", "+1 555 0100", "alice@example.test"):
            self.assertIn(expected, rendered)
        for hidden in ("user-secret-id", "secret-plan", "unrelated-rule"):
            self.assertNotIn(hidden, rendered)
        self.assertNotIn("subscription", " ".join(report["next_actions"]).lower())
        self.assertNotIn("积分", " ".join(report["next_actions"]))
        self.assertNotIn({"label": "Page size", "value": 40}, report["context"])
        html = render_html(report)
        self.assertIn("Alice Example", html)
        self.assertIn("alice@example.test", html)
        self.assertNotIn("user-secret-id", html)
        self.assertNotIn("secret-plan", html)

    def test_explicit_project_name_avoids_project_detail_call(self):
        client = FakeClient()
        report = run_report(parse_args([
            "visibility", "--project-name", "Known Project", "--locale", "en-US",
        ]), client=client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(report["title"], "Known Project Visibility Analysis")

    def test_offset_paging_advances_in_pages_of_40(self):
        client = FakeClient()
        report = run_report(parse_args(["ga4-pages", "--page", "2"]), client=client)
        self.assertEqual(client.calls[1]["params"]["offset"], 40)
        self.assertEqual(client.calls[1]["params"]["limit"], 40)
        self.assertIn({"label": "Page size", "value": 40}, report["context"])

    def test_competitor_rankings_treats_api_response_as_complete_set(self):
        client = FakeClient()
        report = run_report(parse_args([
            "competitor-rankings", "--project-name", "Coffee Lab", "--period", "7d",
        ]), client=client)
        self.assertEqual(len(client.calls), 1)
        self.assertTrue(client.calls[0]["path"].endswith("/competitors/visibility-rankings"))
        self.assertEqual(report["metrics"][0]["value"], 2)
        self.assertIn("Acme", str(report))
        self.assertNotIn("competitor-secret-id", str(report))
        self.assertNotIn("line_chart", {chart["type"] for chart in report["charts"]})

    def test_competitor_name_resolves_from_items_then_calls_overview(self):
        client = FakeClient()
        report = run_report(parse_args([
            "competitor-overview", "--project-name", "Coffee Lab",
            "--competitor", "www.acme.example", "--locale", "en-US",
        ]), client=client)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["path"], "/api/projects/project-secret-id/competitors")
        self.assertTrue(client.calls[1]["path"].endswith("/competitors/competitor-secret-id/overview"))
        self.assertEqual(report["title"], "Competitor Analysis: Acme")
        self.assertTrue(any(chart["type"] == "pie_chart" for chart in report["charts"]))
        self.assertNotIn("competitor-secret-id", str(report))

    def test_competitor_overview_sends_repeatable_topic_and_prompt_filters(self):
        client = FakeClient()
        run_report(parse_args([
            "competitor-overview", "--project-name", "Coffee Lab",
            "--competitor-id", "competitor-secret-id",
            "--filter-topic-id", "topic-a,topic-b", "--filter-topic-id", "topic-c",
            "--filter-prompt-id", "prompt-a", "--filter-prompt-id", "prompt-b,prompt-c",
        ]), client=client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["params"]["topic_id"], ["topic-a", "topic-b", "topic-c"])
        self.assertEqual(client.calls[0]["params"]["prompt_id"], ["prompt-a", "prompt-b", "prompt-c"])

    def test_competitor_prompt_filters_match_existing_api_contract(self):
        client = FakeClient()
        report = run_report(parse_args([
            "competitor-prompts", "--project-name", "Coffee Lab",
            "--competitor-id", "competitor-secret-id", "--topic-id", "topic-secret-id",
            "--platform", "openai,gemini", "--tag-id", "tag-1", "--locale", "zh-CN",
        ]), client=client)
        self.assertEqual(len(client.calls), 1)
        call = client.calls[0]
        self.assertTrue(call["path"].endswith("/competitors/competitor-secret-id/topics/topic-secret-id/prompts"))
        self.assertEqual(call["params"]["platform"], ["openai", "gemini"])
        self.assertEqual(call["params"]["types"], ["visibility"])
        self.assertEqual(call["params"]["tags"], ["tag-1"])
        self.assertEqual(report["title"], "竞争对手 Prompt 分析：Acme")


if __name__ == "__main__":
    unittest.main()
