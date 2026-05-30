import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import geo_score  # noqa: E402


class GeoScoreTests(unittest.TestCase):
    def test_score_table_matches_evaluation_spreadsheet_shape(self):
        self.assertEqual(geo_score.validate_config(), [])
        self.assertEqual(len(geo_score.DIMENSIONS), 5)
        self.assertEqual(sum(len(dimension.items) for dimension in geo_score.DIMENSIONS), 30)
        self.assertEqual(
            [dimension.short_label for dimension in geo_score.DIMENSIONS],
            ["AI 可发现", "AI 可理解", "AI 可引用", "AI 可信任", "AI 可推荐"],
        )
        self.assertEqual(
            [dimension.weight for dimension in geo_score.DIMENSIONS],
            [0.25, 0.20, 0.20, 0.20, 0.15],
        )
        self.assertEqual(
            [len(dimension.items) for dimension in geo_score.DIMENSIONS],
            [7, 7, 5, 5, 6],
        )
        self.assertTrue(all(sum(item.points for item in dimension.items) == 100 for dimension in geo_score.DIMENSIONS))
        self.assertEqual(geo_score.item_map()["1.4"].warn_coefficient, 0.2)
        self.assertEqual(geo_score.item_map()["4.1"].warn_coefficient, 0.3)

    def test_status_coefficients_and_na_error_denominator_handling(self):
        payload = {
            "items": {
                item.id: {"status": "PASS", "note": "ok"}
                for item in geo_score.iter_items()
            }
        }
        payload["items"]["1.1"] = {"status": "WARN", "note": "needs work"}
        payload["items"]["1.2"] = {"status": "FAIL", "note": "bad"}
        payload["items"]["1.3"] = {"status": "N/A", "note": "not applicable"}
        payload["items"]["1.4"] = {"status": "ERROR", "note": "timeout"}

        results = geo_score.score_assessment(payload)
        discoverability = results["dimensions"][0]

        self.assertEqual(discoverability["effective_points"], 64)
        self.assertEqual(discoverability["score"], 55)
        self.assertEqual(discoverability["items"][0]["badge"], "⚠️ WARN")
        self.assertEqual(discoverability["items"][2]["badge"], "➖ N/A")

    def test_p0_caps_apply_to_dimension_cross_dimension_and_final_score(self):
        payload = {
            "items": {
                item.id: {"status": "PASS", "note": "ok"}
                for item in geo_score.iter_items()
            }
        }
        payload["items"]["1.4"] = {"status": "FAIL", "note": "AI crawler blocked"}

        results = geo_score.score_assessment(payload)
        scores = {dimension["short_label"]: dimension["score"] for dimension in results["dimensions"]}

        self.assertEqual(scores["AI 可发现"], 55)
        self.assertEqual(scores["AI 可理解"], 100)
        self.assertEqual(scores["AI 可引用"], 70)
        self.assertEqual(scores["AI 可信任"], 100)
        self.assertEqual(scores["AI 可推荐"], 65)
        self.assertEqual(results["raw_final_score"], 77)
        self.assertEqual(results["final_score"], 70)
        self.assertEqual(len(results["caps"]), 4)

    def test_strict_v3_dimension_caps_apply(self):
        payload = {
            "items": {
                item.id: {"status": "PASS", "note": "ok"}
                for item in geo_score.iter_items()
            }
        }
        payload["items"]["3.1"] = {"status": "FAIL", "note": "No quotable answers"}
        payload["items"]["4.1"] = {"status": "FAIL", "note": "Unclear entity"}
        payload["items"]["5.1"] = {"status": "FAIL", "note": "No AI platform coverage"}

        results = geo_score.score_assessment(payload)
        scores = {dimension["short_label"]: dimension["score"] for dimension in results["dimensions"]}

        self.assertEqual(scores["AI 可引用"], 65)
        self.assertEqual(scores["AI 可信任"], 55)
        self.assertEqual(scores["AI 可推荐"], 60)
        self.assertEqual(results["final_score"], 78)
        self.assertEqual(len(results["caps"]), 3)

    def test_markdown_report_contains_all_30_items_and_no_visibility_score_row(self):
        payload = {
            "items": {
                item.id: {"status": "PASS", "note": f"{item.name} ok"}
                for item in geo_score.iter_items()
            }
        }
        results = geo_score.score_assessment(payload)
        report = geo_score.render_markdown_report(results)

        self.assertIn("## GEO 总分: 100/100", report)
        self.assertIn("| 维度五：AI 可推荐 | 100/100 | 15% |", report)
        self.assertEqual(report.count("| ✅ PASS |"), 30)
        self.assertNotIn("子项分值", report)
        self.assertIn("| # | 检测项 | 状态 | 说明 |", report)
        self.assertIn("| 1.1 | 入口规范与可达性 | ✅ PASS | 入口规范与可达性 ok |", report)
        self.assertNotIn("AI 可见性采样分", report)
        self.assertNotIn("70%", report)

    def test_sitemap_quality_rule_requires_fail_when_sitemap_missing(self):
        sitemap_item = geo_score.item_map()["1.7"]

        self.assertIn("没有可用 sitemap 时直接记不通过", sitemap_item.score_rule)

    def test_cli_validate_and_score(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            assessment_path = tmp / "assessment.json"
            results_path = tmp / "results.json"
            report_path = tmp / "report.md"
            assessment_path.write_text(
                json.dumps({
                    "items": {
                        item.id: {"status": "PASS", "note": "ok"}
                        for item in geo_score.iter_items()
                    }
                }),
                encoding="utf-8",
            )

            validate_code = geo_score.main(["validate"])
            score_code = geo_score.main([
                "score",
                str(assessment_path),
                "--output",
                str(results_path),
                "--report",
                str(report_path),
            ])

            self.assertEqual(validate_code, 0)
            self.assertEqual(score_code, 0)
            results = json.loads(results_path.read_text(encoding="utf-8"))
            self.assertEqual(results["final_score"], 100)
            self.assertIn("timings", results)
            self.assertIn("score_calculation_seconds", results["timings"])
            self.assertIn("total_score_module_seconds", results["timings"])
            self.assertIn("维度一：AI 可发现", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
