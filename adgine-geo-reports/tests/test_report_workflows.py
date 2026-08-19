import os
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


class FakeClient:
    def __init__(self):
        self.project_id = "project-secret-id"
        self.base = "https://api.example.test"
        self.calls = []

    def get(self, path, params=None):
        self.calls.append({"path": path, "params": params, "duration_ms": 1, "status": "ok"})
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
        if path.endswith("/report-data/capabilities"):
            return {
                "schema_version": "1.0",
                "features": {
                    "topic_performance": True,
                    "prompt_performance": True,
                },
            }
        if path.endswith("/report-data/topic-performance"):
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
                "topic": {"id": "topic-secret-id", "name": "Coffee"},
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

    def test_visibility_is_one_api_call(self):
        client = FakeClient()
        args = parse_args(["visibility", "--period", "7d"])
        report = run_report(args, client=client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(report["report_type"], "visibility")
        self.assertNotIn("project-secret-id", str(report))

    def test_scenario_defaults_choose_inline_only_for_small_results(self):
        for scenario in ("account-info", "worker-deployment", "saas-task", "opportunity-detail"):
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
        self.assertEqual(len(client.calls), 2)
        self.assertTrue(client.calls[1]["path"].endswith("/report-data/prompt-performance"))
        self.assertEqual(client.calls[1]["params"]["prompt_id"], prompt_id)
        self.assertEqual(report["context"][-1]["value"], "Selected prompt")

    def test_topic_name_is_two_calls_and_ids_are_hidden(self):
        client = FakeClient()
        args = parse_args(["topic-detail", "--topic", "Coffee", "--period", "14d"])
        report = run_report(args, client=client)
        self.assertEqual(len(client.calls), 2)
        self.assertTrue(client.calls[1]["path"].endswith("/report-data/topic-performance"))
        self.assertEqual(client.calls[1]["params"]["q"], "Coffee")
        self.assertNotIn("topic-secret-id", str(report))
        self.assertIn("Coffee", str(report))
        self.assertEqual(report["coverage"]["sources"][0]["date_basis"], "analyzed_at")
        html = render_html(report)
        self.assertIn("Coffee", html)
        self.assertIn("citation_tests", html)

    def test_chinese_topic_auto_generates_fully_localized_report(self):
        client = FakeClient()
        args = parse_args([
            "topic-detail", "--topic", "数独游戏网站", "--period", "7d",
            "--locale", "auto",
        ])
        report = run_report(args, client=client)
        self.assertEqual(report["locale"], "zh-CN")
        self.assertEqual(report["title"], "Topic 详细分析")
        self.assertEqual(report["context"][0]["label"], "项目")
        self.assertEqual(report["metrics"][0]["label"], "AI 可见性得分")
        self.assertIn("对比", report["next_actions"][0])
        html = render_html(report)
        for expected in ("核心发现", "数据覆盖情况", "查询审计与数据质量", "生成时间"):
            self.assertIn(expected, html)
        self.assertNotIn("Key findings", html)

    def test_explicit_english_overrides_chinese_entity_text(self):
        client = FakeClient()
        args = parse_args([
            "topic-detail", "--topic", "数独游戏网站", "--locale", "en-US",
        ])
        report = run_report(args, client=client)
        self.assertEqual(report["locale"], "en-US")
        self.assertEqual(report["title"], "Topic Detail")
        self.assertEqual(report["context"][0]["label"], "Project")

    def test_report_data_5xx_does_not_fall_back(self):
        client = FailingReportDataClient(ApiError("down", status_code=503, payload={"code": 50304}))
        with self.assertRaises(ApiError):
            run_report(parse_args([
                "prompt-performance", "--prompt-id", "11111111-1111-4111-8111-111111111111",
            ]), client=client)
        self.assertEqual(len(client.calls), 2)

    def test_entity_404_does_not_fall_back(self):
        client = FailingReportDataClient(ApiError("missing", status_code=404, payload={"code": 40406}))
        with self.assertRaises(ApiError):
            run_report(parse_args([
                "prompt-performance", "--prompt-id", "11111111-1111-4111-8111-111111111111",
            ]), client=client)
        self.assertEqual(len(client.calls), 2)

    def test_route_404_uses_legacy_endpoint_with_warning(self):
        client = FailingReportDataClient(ApiError("route missing", status_code=404, payload={"code": 40400}))
        report = run_report(parse_args([
            "prompt-performance", "--prompt-id", "11111111-1111-4111-8111-111111111111",
        ]), client=client)
        self.assertEqual(len(client.calls), 3)
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
        self.assertNotIn({"label": "Page size", "value": 40}, report["context"])
        html = render_html(report)
        self.assertIn("Alice Example", html)
        self.assertIn("alice@example.test", html)
        self.assertNotIn("user-secret-id", html)
        self.assertNotIn("secret-plan", html)

    def test_offset_paging_advances_in_pages_of_40(self):
        client = FakeClient()
        report = run_report(parse_args(["ga4-pages", "--page", "2"]), client=client)
        self.assertEqual(client.calls[0]["params"]["offset"], 40)
        self.assertEqual(client.calls[0]["params"]["limit"], 40)
        self.assertIn({"label": "Page size", "value": 40}, report["context"])


if __name__ == "__main__":
    unittest.main()
