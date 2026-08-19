import os
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def read(relative):
    with open(os.path.join(ROOT, relative), encoding="utf-8") as handle:
        return handle.read()


class ExistingSkillContractTests(unittest.TestCase):
    def test_visibility_analytics_uses_date_from_to(self):
        for relative in (
            "adgine-geo-visibility/scripts/get_topic_metrics.py",
            "adgine-geo-visibility/scripts/get_prompt_metrics.py",
            "adgine-geo-visibility/scripts/get_matrix.py",
            "adgine-geo-visibility/scripts/get_execution.py",
        ):
            source = read(relative)
            self.assertIn('"date_from"', source, relative)
            self.assertIn('"date_to"', source, relative)

    def test_ga4_uses_current_schema_and_offset_paging(self):
        source = read("adgine-geo-integrations/scripts/ga4_data.py")
        self.assertIn('"total_sessions"', source)
        self.assertIn('"total_active_users"', source)
        self.assertIn('"total_page_views"', source)
        self.assertIn('"offset": (args.page - 1) * args.limit', source)
        self.assertIn('(data or {}).get("items", [])', source)

    def test_dashboard_visibility_uses_metrics_container(self):
        source = read("adgine-geo-dashboard/scripts/get_visibility_overview.py")
        self.assertIn('data.get("metrics")', source)
        self.assertIn('visibility.get("trend")', source)
        self.assertNotIn('data.get("current_score")', source)

    def test_pagespeed_refresh_uses_query_parameter(self):
        page_detail = read("adgine-geo-aiagent/scripts/page_detail.py")
        performance = read("adgine-geo-performance/scripts/analyze_page.py")
        self.assertIn("health/refresh?path=", page_detail)
        self.assertIn("health/refresh?{urllib.parse.urlencode(query_params)}", performance)
        self.assertNotIn('body={"path": args.path}', page_detail)

    def test_paginated_queries_default_to_40_rows(self):
        scripts = (
            "adgine-geo-projects/scripts/list_projects.py",
            "adgine-geo-topics/scripts/manage_topics.py",
            "adgine-geo-topics/scripts/manage_prompts.py",
            "adgine-geo-citation/scripts/get_results.py",
            "adgine-geo-content/scripts/list_content.py",
            "adgine-geo-content/scripts/manage_jobs.py",
            "adgine-geo-brand/scripts/list_jobs.py",
            "adgine-geo-visibility/scripts/get_execution.py",
            "adgine-geo-integrations/scripts/ga4_data.py",
            "adgine-geo-integrations/scripts/cloudflare_worker.py",
            "adgine-geo-aiagent/scripts/page_analytics.py",
            "adgine-geo-aiagent/scripts/human_traffic.py",
            "adgine-geo-aiagent/scripts/page_detail.py",
        )
        for relative in scripts:
            source = read(relative)
            self.assertIn("default=40", source, relative)
            for old_default in ("default=20", "default=50", "default=100"):
                self.assertNotIn(old_default, source, relative)
        self.assertIn("DEFAULT_PAGE_SIZE = 40", read("adgine-geo-reports/scripts/report.py"))

    def test_non_paginated_domain_search_respects_backend_cap(self):
        source = read("adgine-geo-domains/scripts/search_domains.py")
        self.assertIn("default=20", source)
        self.assertIn("backend-capped at 20", source)

    def test_aiagent_paging_matches_backend_contracts(self):
        page_analytics = read("adgine-geo-aiagent/scripts/page_analytics.py")
        human_traffic = read("adgine-geo-aiagent/scripts/human_traffic.py")
        page_detail = read("adgine-geo-aiagent/scripts/page_detail.py")
        executions = read("adgine-geo-visibility/scripts/get_execution.py")
        prompts = read("adgine-geo-topics/scripts/manage_prompts.py")
        citation_results = read("adgine-geo-citation/scripts/get_results.py")
        self.assertGreaterEqual(page_analytics.count('params["offset"] = (args.page - 1) * args.limit'), 2)
        self.assertGreaterEqual(human_traffic.count('params["offset"] = (args.page - 1) * args.limit'), 2)
        self.assertIn('params["page"] = args.page', page_detail)
        self.assertIn('{"page": args.page, "page_size": args.limit}', executions)
        self.assertGreaterEqual(prompts.count('{"page": args.page, "limit": args.limit}'), 2)
        self.assertIn('params={"page": args.page, "limit": args.limit}', citation_results)
        self.assertIn('"page_size": args.limit', citation_results)

    def test_all_shared_clients_are_identical(self):
        canonical = read("adgine-geo-visibility/scripts/_client.py")
        clients = []
        for name in os.listdir(ROOT):
            path = os.path.join(ROOT, name, "scripts", "_client.py")
            if name.startswith("adgine-geo-") and os.path.isfile(path):
                clients.append(path)
        self.assertGreaterEqual(len(clients), 19)
        for path in clients:
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), canonical, path)


if __name__ == "__main__":
    unittest.main()
