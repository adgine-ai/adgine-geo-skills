import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import geo_visibility  # noqa: E402


def sample_audit_data():
    return {
        "meta": {
            "url": "https://www.examplepay.com/",
            "domain": "www.examplepay.com",
            "brand_query": "ExamplePay",
        },
        "signals": {
            "d1_sitemap": {
                "sampled_page_urls": [
                    "https://www.examplepay.com/payments",
                    "https://www.examplepay.com/docs",
                ],
            },
            "d3_brand_name": {
                "schema_org_name": "ExamplePay",
                "llms_title": "ExamplePay - Payment infrastructure",
                "title_brand": "ExamplePay",
            },
            "d3_third_party": {
                "platforms_found": ["LinkedIn", "GitHub"],
                "same_as_links": [
                    "https://www.linkedin.com/company/examplepay",
                    "https://github.com/examplepay",
                ],
            },
            "d3_knowledge_graph": {
                "wikipedia": {
                    "total_hits": 1,
                    "results": [
                        {
                            "title": "ExamplePay",
                            "snippet": "Payment infrastructure company",
                        }
                    ],
                },
                "wikidata": {
                    "entity_count": 1,
                    "entities": [
                        {
                            "id": "Q123",
                            "label": "ExamplePay",
                            "description": "payment infrastructure platform",
                        }
                    ],
                },
            },
        },
        "snippets": {
            "d3_brand_description_content": (
                "ExamplePay is a payment infrastructure platform for online checkout, "
                "billing, subscriptions and API payments in Singapore and United States."
            ),
            "d1_llms_txt_content": (
                "# ExamplePay\n"
                "> Payment infrastructure for checkout, subscriptions and billing."
            ),
            "d2_depth_sample": (
                "Developers use the dashboard, API, payments analytics and reporting tools."
            ),
        },
    }


class GeoVisibilityTests(unittest.TestCase):
    def test_build_brand_profile_extracts_public_brand_facts(self):
        profile = geo_visibility.build_brand_profile(sample_audit_data())

        self.assertEqual(profile["brand_name"], "ExamplePay")
        self.assertEqual(profile["domain"], "examplepay.com")
        self.assertEqual(profile["category"], "payment infrastructure")
        self.assertIn("Singapore", profile["regions"])
        self.assertIn("API", profile["product_terms"])
        self.assertIn("analytics", profile["product_terms"])
        self.assertIn("https://github.com/examplepay", profile["source_urls"])
        self.assertEqual(
            profile["third_party_sources"]["knowledge_graph"]["wikidata"]["entity_count"],
            1,
        )

    def test_product_terms_are_extracted_from_site_content_not_fixed_keywords(self):
        audit_data = sample_audit_data()
        audit_data["meta"] = {
            "url": "https://school.example/",
            "domain": "school.example",
            "brand_query": "Wukong School",
        }
        audit_data["signals"]["d1_sitemap"]["sampled_page_urls"] = [
            "https://school.example/math-olympiad",
            "https://school.example/chinese-language",
            "https://school.example/coding-classes",
        ]
        audit_data["signals"]["d3_brand_name"] = {
            "schema_org_name": "Wukong School",
            "llms_title": "Wukong School",
            "title_brand": "Wukong School",
        }
        audit_data["snippets"] = {
            "d3_brand_description_content": (
                "Wukong School provides live online math olympiad, Chinese language "
                "and coding classes for K-12 students in the United States."
            ),
            "d1_llms_txt_content": "# Wukong School\nOnline math olympiad, Chinese language and coding classes.",
            "d2_depth_sample": (
                "Students can join small group courses, practice worksheets, contest "
                "preparation and teacher-led lessons."
            ),
        }

        profile = geo_visibility.build_brand_profile(audit_data)

        self.assertIn("math", profile["product_terms"])
        self.assertIn("coding", profile["product_terms"])
        self.assertIn("chinese", profile["product_terms"])
        self.assertNotIn("payments", profile["product_terms"])
        self.assertNotIn("brokerage", profile["product_terms"])
        self.assertFalse(hasattr(geo_visibility, "PRODUCT_KEYWORDS"))

    def test_generate_prompts_covers_required_visibility_scenarios(self):
        profile = geo_visibility.build_brand_profile(sample_audit_data())
        prompts = geo_visibility.generate_visibility_prompts(profile)
        prompt_types = {item["type"] for item in prompts}

        self.assertGreaterEqual(len(prompts), 8)
        self.assertLessEqual(len(prompts), 12)
        self.assertEqual(
            prompt_types,
            {
                "brand_identification",
                "category_discovery",
                "problem_solution",
                "competitor_alternative",
                "source_reference",
            },
        )
        category_prompts = [item for item in prompts if item["type"] == "category_discovery"]
        self.assertTrue(category_prompts)
        self.assertTrue(all("ExamplePay" not in item["prompt"] for item in category_prompts))

    def test_subagent_task_does_not_include_brand_profile_for_discovery_prompt(self):
        profile = geo_visibility.build_brand_profile(sample_audit_data())
        prompt = next(
            item
            for item in geo_visibility.generate_visibility_prompts(profile)
            if item["type"] == "category_discovery"
        )

        task = geo_visibility.build_subagent_task(prompt)

        self.assertIn(prompt["prompt"], task)
        self.assertIn("mentioned_brand: true|false", task)
        self.assertNotIn(profile["brand_name"], task)
        self.assertNotIn(profile["domain"], task)
        self.assertNotIn("source_urls", task)

    def test_subagent_batches_limit_concurrency_to_five(self):
        profile = geo_visibility.build_brand_profile(sample_audit_data())
        prompts = geo_visibility.generate_visibility_prompts(profile)

        batches = geo_visibility.batch_subagent_tasks(prompts)

        self.assertEqual(len(prompts), 10)
        self.assertEqual(len(batches), 2)
        self.assertTrue(all(len(batch) <= 5 for batch in batches))
        self.assertEqual(
            [prompt_id for batch in batches for prompt_id in batch],
            [prompt["id"] for prompt in prompts],
        )

    def test_visibility_reference_metadata_does_not_blend_geo_score(self):
        metadata = geo_visibility.visibility_reference_metadata(75)

        self.assertEqual(metadata["geo_score_reference"], 75.0)
        self.assertEqual(metadata["score_formula"], "visibility_reference_only")
        self.assertFalse(metadata["agent_visibility_included"])
        self.assertNotIn("final_score", metadata)

    def test_score_visibility_results_uses_parent_brand_matching_and_metrics(self):
        profile = geo_visibility.build_brand_profile(sample_audit_data())
        prompts = geo_visibility.generate_visibility_prompts(profile)
        prompt_by_id = {item["id"]: item for item in prompts}
        answers = [
            {
                "prompt_id": "visibility-01",
                "answer": "ExamplePay is a payment infrastructure platform for API checkout in Singapore.",
                "mentioned_brand": "true",
                "brand_position": 1,
                "correct_entity": True,
            },
            {
                "prompt_id": "visibility-02",
                "answer": "ExamplePay helps developers with billing and subscriptions.",
                "mentioned_brand": True,
                "brand_position": 1,
                "correct_entity": True,
            },
            {
                "prompt_id": "visibility-03",
                "answer": "1. Stripe 2. ExamplePay 3. Adyen",
                "mentioned_brand": False,
                "brand_position": 2,
                "correct_entity": True,
            },
            {
                "prompt_id": "visibility-04",
                "answer": "Stripe, Adyen and Checkout.com are common shortlists.",
                "mentioned_brand": False,
            },
            {
                "prompt_id": "visibility-05",
                "answer": "Stripe, Adyen, ExamplePay and Braintree can help with API payments.",
                "mentioned_brand": False,
                "brand_position": 3,
                "correct_entity": True,
            },
            {
                "prompt_id": "visibility-06",
                "answer": "Stripe and Adyen are common options.",
                "mentioned_brand": False,
            },
            {
                "prompt_id": "visibility-07",
                "answer": "Alternatives to ExamplePay include Stripe, Adyen and Braintree.",
                "mentioned_brand": True,
                "brand_position": 1,
                "correct_entity": True,
                "competitors_mentioned": ["Stripe", "Adyen", "Braintree"],
            },
            {
                "prompt_id": "visibility-08",
                "answer": "ExamplePay is a consumer bank; alternatives include Revolut.",
                "mentioned_brand": True,
                "brand_position": 1,
                "correct_entity": False,
                "hallucinated": True,
            },
            {
                "prompt_id": "visibility-09",
                "answer": "Use the official docs at https://examplepay.com/docs.",
                "mentioned_brand": True,
                "brand_position": 1,
                "mentioned_urls": ["https://examplepay.com/docs"],
                "correct_entity": True,
            },
            {
                "prompt_id": "visibility-10",
                "answer": "Official sources include https://examplepay.com and payment docs.",
                "mentioned_brand": False,
                "brand_position": 4,
                "mentioned_urls": ["https://examplepay.com"],
                "correct_entity": True,
            },
        ]

        results = geo_visibility.score_visibility_results(profile, list(prompt_by_id.values()), answers)

        self.assertEqual(results["metrics"]["mention_rate"], 0.8)
        self.assertEqual(results["metrics"]["category_visibility_rate"], 0.5)
        self.assertEqual(results["metrics"]["source_visibility_rate"], 1.0)
        self.assertEqual(results["metrics"]["hallucination_rate"], 0.125)
        self.assertAlmostEqual(results["metrics"]["average_rank"], 3.6)
        self.assertAlmostEqual(results["metrics"]["visibility_score"], 78.3)
        self.assertTrue(results["rows"][2]["mentioned_brand"])

    def test_score_visibility_results_keeps_visibility_as_reference(self):
        profile = geo_visibility.build_brand_profile(sample_audit_data())
        prompts = geo_visibility.generate_visibility_prompts(profile)
        answers = [
            {
                "prompt_id": item["id"],
                "answer": "No clear mention.",
                "mentioned_brand": False,
            }
            for item in prompts
        ]

        results = geo_visibility.score_visibility_results(
            profile,
            prompts,
            answers,
            public_geo_score=75,
        )

        self.assertEqual(results["metrics"]["geo_score_reference"], 75.0)
        self.assertFalse(results["metrics"]["agent_visibility_included"])
        self.assertNotIn("final_score", results["metrics"])

    def test_prompt_field_does_not_count_as_answer_brand_mention(self):
        profile = geo_visibility.build_brand_profile(sample_audit_data())
        prompts = geo_visibility.generate_visibility_prompts(profile)
        first_prompt = prompts[0]

        results = geo_visibility.score_visibility_results(
            profile,
            [first_prompt],
            [
                {
                    "prompt_id": first_prompt["id"],
                    "prompt": first_prompt["prompt"],
                    "answer": "It is a useful platform, but no name is repeated here.",
                    "mentioned_brand": False,
                }
            ],
        )

        self.assertFalse(results["rows"][0]["mentioned_brand"])
        self.assertEqual(results["metrics"]["mention_rate"], 0.0)

    def test_subagent_true_label_without_text_match_does_not_count_as_mention(self):
        profile = geo_visibility.build_brand_profile(sample_audit_data())
        prompt = next(
            item
            for item in geo_visibility.generate_visibility_prompts(profile)
            if item["type"] == "category_discovery"
        )

        results = geo_visibility.score_visibility_results(
            profile,
            [prompt],
            [
                {
                    "prompt_id": prompt["id"],
                    "answer": "Interactive Brokers, Saxo, and Tiger Brokers are common choices.",
                    "mentioned_brand": True,
                    "brand_position": None,
                }
            ],
        )

        self.assertFalse(results["rows"][0]["mentioned_brand"])
        self.assertEqual(results["metrics"]["mention_rate"], 0.0)

    def test_format_visibility_report_contains_summary_and_warning(self):
        profile = geo_visibility.build_brand_profile(sample_audit_data())
        prompts = geo_visibility.generate_visibility_prompts(profile)
        answers = [
            {
                "prompt_id": item["id"],
                "answer": "No clear mention.",
                "mentioned_brand": False,
            }
            for item in prompts
        ]
        results = geo_visibility.score_visibility_results(profile, prompts, answers)

        report = geo_visibility.format_visibility_report(results)

        self.assertIn("## AI 可见性采样参考", report)
        self.assertIn("仅用于粗略观察品牌在 AI 回答中的可见性", report)
        self.assertIn("不参与 GEO 总分", report)
        self.assertIn("[adgine.ai](https://adgine.ai/)", report)
        self.assertIn("AI 可见性采样分", report)
        self.assertNotIn("**AI 可见性采样分**", report)
        self.assertIn("是否可见", report)
        self.assertNotIn("实体正确", report)
        self.assertNotIn("| 幻觉 |", report)
        self.assertIn("### 统计摘要", report)
        self.assertIn("### Prompt 明细", report)
        self.assertIn("### 改进建议", report)

    def test_cli_prepare_and_score_writes_expected_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            audit_path = tmp / "audit.json"
            plan_path = tmp / "plan.json"
            answers_path = tmp / "answers.json"
            results_path = tmp / "results.json"
            report_path = tmp / "report.md"
            audit_path.write_text(json.dumps(sample_audit_data()), encoding="utf-8")

            prepare_code = geo_visibility.main([
                "prepare",
                str(audit_path),
                "--output",
                str(plan_path),
            ])
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            answers_path.write_text(
                json.dumps({
                    "answers": [
                        {
                            "prompt_id": item["id"],
                            "answer": "No clear mention.",
                            "mentioned_brand": False,
                        }
                        for item in plan["prompts"]
                    ]
                }),
                encoding="utf-8",
            )
            score_code = geo_visibility.main([
                "score",
                str(plan_path),
                str(answers_path),
                "--output",
                str(results_path),
                "--report",
                str(report_path),
                "--public-geo-score",
                "75",
            ])
            results = json.loads(results_path.read_text(encoding="utf-8"))

            self.assertEqual(prepare_code, 0)
            self.assertEqual(score_code, 0)
            self.assertIn("brand_profile", plan)
            self.assertEqual(plan["subagent_concurrency_limit"], 5)
            self.assertEqual(len(plan["subagent_batches"]), 2)
            self.assertIn("timings", plan)
            self.assertIn("prompt_generation_seconds", plan["timings"])
            self.assertTrue(results_path.exists())
            self.assertNotIn("final_score", results["metrics"])
            self.assertIn("timings", results)
            self.assertIn("visibility_score_calculation_seconds", results["timings"])
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("AI 可见性采样参考", report_text)
            self.assertIn("AI 可见性采样分", report_text)


if __name__ == "__main__":
    unittest.main()
