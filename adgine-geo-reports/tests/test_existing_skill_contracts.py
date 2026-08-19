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
            "adgine-geo-content/scripts/manage_media.py",
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

    def test_topics_match_current_prompt_mutation_contracts(self):
        prompts = read("adgine-geo-topics/scripts/manage_prompts.py")
        generation = read("adgine-geo-topics/scripts/generate_prompts.py")
        tags = read("adgine-geo-topics/scripts/manage_prompt_tags.py")
        topics = read("adgine-geo-topics/scripts/manage_topics.py")
        self.assertIn('body["types"] = None', prompts)
        self.assertIn('body["tag_ids"] = []', prompts)
        self.assertIn('body["platforms"] = _csv(args.platforms)', prompts)
        self.assertNotIn('default="English"', prompts)
        self.assertNotIn('default="US"', prompts)
        self.assertIn('body["additional_instructions"]', generation)
        self.assertIn('/prompts/tags', tags)
        self.assertIn('"DELETE"', tags)
        self.assertIn('body["language"] = args.language', topics)
        self.assertIn('body["region"] = args.region', topics)

    def test_project_and_saas_mutations_match_current_schemas(self):
        project = read("adgine-geo-projects/scripts/manage_project.py")
        saas = read("adgine-geo-saas/scripts/create_website.py")
        project_update = project.split('elif args.action == "update":', 1)[1].split("# ── DELETE", 1)[0]
        self.assertIn('body["metadata_override"] = metadata', project)
        self.assertIn('body = {"name": args.name}', project_update)
        self.assertNotIn('body["url"]', project_update)
        self.assertNotIn('body["description"]', project_update)
        self.assertIn('add_mutually_exclusive_group(required=True)', saas)
        self.assertIn('"theme_id": args.theme_id', saas)
        self.assertNotIn('"industry"', saas)

    def test_content_mutations_match_current_content_and_job_schemas(self):
        outline = read("adgine-geo-content/scripts/generate_outline.py")
        article = read("adgine-geo-content/scripts/generate_article.py")
        content = read("adgine-geo-content/scripts/manage_content.py")
        jobs = read("adgine-geo-content/scripts/manage_jobs.py")
        refine = read("adgine-geo-content/scripts/refine_article.py")
        cover = read("adgine-geo-content/scripts/generate_cover.py")
        media = read("adgine-geo-content/scripts/manage_media.py")
        self.assertIn('body["article_type"]', outline)
        self.assertIn('body["article_strategy"]', outline)
        self.assertIn('body["language"] = args.language', article)
        self.assertIn('body["full_content"]', content)
        self.assertIn('/publish-status', content)
        self.assertIn('/versions/{version_id}', content)
        self.assertNotIn('body["article_body"]', content)
        self.assertNotIn('body["status"]', content)
        self.assertIn('/content/jobs', jobs)
        self.assertNotIn('/outline-jobs', jobs)
        self.assertNotIn('/article-jobs', jobs)
        self.assertIn('/refine-article', refine)
        self.assertIn('/generate-cover', cover)
        self.assertIn('/api/uploads/images', media)
        self.assertIn('/media', media)


if __name__ == "__main__":
    unittest.main()
