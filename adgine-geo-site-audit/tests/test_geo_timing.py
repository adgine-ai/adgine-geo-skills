import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import geo_timing  # noqa: E402


class GeoTimingTests(unittest.TestCase):
    def test_artifact_summary_reads_existing_timings_without_markers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            collect = tmp / "collect.json"
            score = tmp / "score.json"
            summary_json = tmp / "summary.json"

            collect.write_text(
                json.dumps({
                    "meta": {
                        "report_generation_elapsed_seconds": 12.3,
                        "timings": {
                            "total_collection_seconds": 12.3,
                            "notfound_probe_seconds": 1.2,
                        },
                    }
                }),
                encoding="utf-8",
            )
            score.write_text(
                json.dumps({
                    "timings": {
                        "total_score_module_seconds": 0.2,
                        "score_calculation_seconds": 0.1,
                    }
                }),
                encoding="utf-8",
            )

            self.assertEqual(
                geo_timing.main([
                    "artifacts",
                    "--label",
                    "example.com",
                    "--collect-json",
                    str(collect),
                    "--score-json",
                    str(score),
                    "--ui-elapsed-seconds",
                    "20",
                    "--output",
                    str(summary_json),
                ]),
                0,
            )

            summary = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["measurement_mode"], "artifact_summary")
            self.assertEqual(summary["known_script_seconds"], 12.5)
            self.assertEqual(summary["total_workflow_seconds"], 20.0)
            self.assertEqual(summary["untracked_agent_overhead_seconds"], 7.5)
            self.assertEqual(summary["attachments"]["collect"]["timings"]["notfound_probe_seconds"], 1.2)
            self.assertEqual(summary["attachments"]["score"]["total_seconds"], 0.2)

    def test_ledger_marks_named_spans_and_attaches_collect_timings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            ledger = tmp / "timing.json"
            collect = tmp / "collect.json"
            summary_json = tmp / "summary.json"
            summary_md = tmp / "summary.md"

            self.assertEqual(geo_timing.main(["start", str(ledger), "--label", "example.com"]), 0)
            self.assertEqual(geo_timing.main(["mark", str(ledger), "collect_start"]), 0)
            self.assertEqual(geo_timing.main(["mark", str(ledger), "collect_end"]), 0)

            collect.write_text(
                json.dumps({
                    "meta": {
                        "report_generation_elapsed_seconds": 12.3,
                        "timings": {
                            "total_collection_seconds": 12.3,
                            "notfound_probe_seconds": 1.2,
                        },
                    }
                }),
                encoding="utf-8",
            )
            self.assertEqual(geo_timing.main(["attach", str(ledger), "collect", str(collect)]), 0)
            self.assertEqual(
                geo_timing.main([
                    "summary",
                    str(ledger),
                    "--output",
                    str(summary_json),
                    "--report",
                    str(summary_md),
                ]),
                0,
            )

            summary = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["label"], "example.com")
            self.assertEqual(summary["attachments"]["collect"]["total_seconds"], 12.3)
            self.assertEqual(summary["attachments"]["collect"]["timings"]["notfound_probe_seconds"], 1.2)
            self.assertEqual(summary["named_spans"][0]["name"], "collect")
            self.assertIn("Attached Script Timings", summary_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
