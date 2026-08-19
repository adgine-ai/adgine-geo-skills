import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("GEO_SKIP_VERSION_CHECK", "1")
SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import _client  # noqa: E402
from _contracts import SCENARIOS  # noqa: E402
from report import REPORT_DATA_SCENARIOS  # noqa: E402


class ContractRegistryTests(unittest.TestCase):
    def test_p1_p2_p3_are_all_implemented(self):
        phases = {scenario.phase for scenario in SCENARIOS.values()}
        self.assertEqual(phases, {"P1", "P2", "P3"})
        self.assertGreaterEqual(len(SCENARIOS), 35)

    def test_high_frequency_contracts_match_geo_api(self):
        topics = SCENARIOS["topics"].requests[0]
        prompt = SCENARIOS["prompt-performance"].requests[0]
        ga4_pages = SCENARIOS["ga4-pages"].requests[0]
        executions = SCENARIOS["prompt-executions"].requests[0]
        account = SCENARIOS["account-info"].requests[0]
        ai_pages = SCENARIOS["ai-pages"].requests[0]
        ai_human_pages = SCENARIOS["ai-humans"].requests[2]
        self.assertEqual(topics.date_style, "analytics")
        self.assertIn("/analytics/topics", topics.path)
        self.assertIn("/analytics/prompts/{prompt_id}/overview", prompt.path)
        self.assertEqual(ga4_pages.paging, "offset")
        self.assertEqual(executions.paging, "page_size")
        self.assertEqual(account.path, "/api/auth/me")
        self.assertEqual(ai_pages.paging, "offset")
        self.assertEqual(ai_human_pages.paging, "offset")

    def test_page_health_is_get_only_and_cached(self):
        request = SCENARIOS["page-health"].requests[0]
        self.assertEqual(request.path.rsplit("/", 1)[-1], "health")
        self.assertNotIn("refresh", request.path)

    def test_report_data_feature_surface_matches_backend_v1(self):
        expected = {
            "executive_overview",
            "topic_performance",
            "prompt_performance",
            "traffic_overview",
            "pages",
            "page_detail",
            "data_freshness",
            "content_pipeline",
            "operations_overview",
        }
        self.assertEqual({feature for feature, _ in REPORT_DATA_SCENARIOS.values()}, expected)
        self.assertTrue(all(scenario in SCENARIOS for scenario in REPORT_DATA_SCENARIOS))


class ClientSerializationTests(unittest.TestCase):
    def test_lists_repeat_and_booleans_are_lowercase(self):
        with mock.patch.object(_client, "_do_request", return_value={}) as request:
            _client.api_get(
                "/api/example", "key", "https://example.test",
                params={"platform": ["chatgpt", "gemini"], "include_trend": True},
            )
        url = request.call_args.args[1]
        self.assertIn("platform=chatgpt&platform=gemini", url)
        self.assertIn("include_trend=true", url)

    def test_report_call_can_raise_instead_of_exiting(self):
        error = _client.ApiError("not found", status_code=404)
        with mock.patch.object(_client, "_do_request", side_effect=error):
            with self.assertRaises(_client.ApiError):
                _client.api_get(
                    "/api/missing", "key", "https://example.test",
                    exit_on_error=False,
                )


if __name__ == "__main__":
    unittest.main()
