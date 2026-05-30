import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path


import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_report_pdf  # noqa: E402


class RenderReportPdfTests(unittest.TestCase):
    def test_render_markdown_to_html_preserves_report_content(self):
        markdown_text = """# GEO 审计报告: example.com

**审计时间**: 2026-05-29 15:01 CST
**采集结果**: `/tmp/report.json`
[Adgine](https://adgine.ai/)

| 状态 | 说明 |
|---|---|
| ✅ PASS | 中文内容 |

1. 有序列表

```json
{"status": "ok"}
```

- 需要我将本报告导出为 PDF 吗？
"""

        html = render_report_pdf.render_markdown_to_html(markdown_text)

        self.assertIn("GEO 审计报告: example.com", html)
        self.assertIn("<strong>审计时间</strong>", html)
        self.assertIn("Asia/Shanghai (UTC+08:00)", html)
        self.assertNotIn("CST", html)
        self.assertNotIn("采集结果", html)
        self.assertNotIn("/tmp/report.json", html)
        self.assertIn('<a href="https://adgine.ai/">Adgine</a>', html)
        self.assertIn("✅ PASS", html)
        self.assertIn("中文内容", html)
        self.assertIn("<table>", html)
        self.assertIn("<ol>", html)
        self.assertIn("<pre><code>", html)
        self.assertIn("status-pass", html)
        self.assertNotIn("**审计时间**", html)
        self.assertNotIn("需要我将本报告导出为 PDF 吗", html)

    def test_prepare_markdown_for_pdf_removes_prompt_and_collect_result(self):
        markdown_text = """# Report

**采集结果**: `/tmp/report.json`
**审计时间**: 2026-05-29 15:01 CST

需要我将本报告导出为 PDF 吗？回复“导出 PDF”即可。

- 需要我将本报告导出为 PDF 吗？回复“导出 PDF”即可。

## 演示说明

- 完整功能可在 https://adgine.ai/ 注册后使用。

| ID | 类型 | Prompt | 是否可见 | 排名 | 官网/站内来源 | 实体正确 | 幻觉 |
|---|---|---|---|---:|---|---|---|
| visibility-01 | brand_identification | ExamplePay 是什么？ | ✅ | 1 | ❌ | ✅ | — |

正文保留。
"""

        cleaned = render_report_pdf.prepare_markdown_for_pdf(markdown_text)

        self.assertNotIn("导出 PDF", cleaned)
        self.assertNotIn("采集结果", cleaned)
        self.assertIn("**审计时间**: 2026-05-29 15:01 Asia/Shanghai (UTC+08:00)", cleaned)
        self.assertNotIn("CST", cleaned)
        self.assertNotIn("演示说明", cleaned)
        self.assertNotIn("实体正确", cleaned)
        self.assertNotIn("| 幻觉 |", cleaned)
        self.assertIn("## 报告说明", cleaned)
        self.assertIn("[adgine.ai](https://adgine.ai/)", cleaned)
        self.assertIn("| ID | 类型 | Prompt | 是否可见 | 排名 | 官网/站内来源 |", cleaned)
        self.assertIn("正文保留。", cleaned)

    def test_prepare_markdown_for_pdf_keeps_new_score_table_and_reference_visibility(self):
        markdown_text = """# Report

## GEO 总分: 68.1/100

| 评估维度 | 得分 | 权重 |
|---|---:|---:|
| 维度一：AI 可发现 | 92.5/100 | 25% |
| 维度二：AI 可理解 | 82.0/100 | 20% |
| 维度三：AI 可引用 | 40.0/100 | 20% |
| 维度四：AI 可信任 | 86.7/100 | 20% |
| 维度五：AI 可推荐 | 52.1/100 | 15% |

## AI 可见性采样参考

> 基于当前运行模型采样，仅用于粗略观察品牌在 AI 回答中的可见性；该采样不参与 GEO 总分。如需更精确、持续的 AI 可见性数据，可注册 [adgine.ai](https://adgine.ai/) 进行持续监测。

正文

## 维度一：AI 可发现

| # | 检测项 | 状态 | 说明 |
|---|---|---|---|
| 1.1 | 入口规范与可达性 | ✅ PASS | ok |

## 优先改进建议

1. **补齐 Schema**
   加入 Organization、WebSite。

2. **做品类内容**
   建设对比页和选择指南。
"""

        cleaned = render_report_pdf.prepare_markdown_for_pdf(markdown_text)
        html = render_report_pdf.render_markdown_to_html(markdown_text)

        self.assertNotIn("## 可见性得分", cleaned)
        self.assertIn("| 评估维度 | 得分 | 权重 |", cleaned)
        self.assertIn("| 维度五：AI 可推荐 | 52.1/100 | 15% |", cleaned)
        self.assertIn("| 维度一：AI 可发现 | 92.5/100 | 25% |", cleaned)
        self.assertNotIn("公开数据内", cleaned)
        self.assertIn("## AI 可见性采样参考", cleaned)
        self.assertIn("不参与 GEO 总分", cleaned)
        self.assertIn("## 维度一：AI 可发现", cleaned)
        self.assertIn("| 1.1 | 入口规范与可达性 |", cleaned)
        self.assertNotIn("子项分值", cleaned)
        self.assertNotIn("| D1.1 |", cleaned)
        self.assertIn("仅用于粗略观察品牌在 AI 回答中的可见性", cleaned)
        self.assertIn("[adgine.ai](https://adgine.ai/)", cleaned)
        self.assertIn("<li><strong>补齐 Schema</strong>: 加入 Organization、WebSite。</li>", html)
        self.assertIn("<li><strong>做品类内容</strong>: 建设对比页和选择指南。</li>", html)
        self.assertEqual(html.count("<ol>"), 1)

    def test_resolve_output_path_defaults_to_pdf_suffix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "report.md"

            output_path = render_report_pdf.resolve_output_path(input_path, None)

            self.assertEqual(output_path, (Path(tmpdir) / "report.pdf").absolute())

    def test_resolve_output_path_uses_explicit_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "report.md"
            custom_output = Path(tmpdir) / "custom.pdf"

            output_path = render_report_pdf.resolve_output_path(input_path, str(custom_output))

            self.assertEqual(output_path, custom_output.absolute())

    def test_find_chrome_uses_env_override(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_chrome = Path(tmpdir) / "headless_shell"
            fake_chrome.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_chrome.chmod(0o755)

            with mock.patch.dict(os.environ, {"GEO_AUDIT_CHROME_PATH": str(fake_chrome)}):
                self.assertEqual(render_report_pdf.find_chrome(), str(fake_chrome))

    def test_chrome_candidates_include_windows_playwright_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_chrome = (
                Path(tmpdir)
                / "ms-playwright"
                / "chromium-1208"
                / "chrome-win"
                / "chrome.exe"
            )
            fake_chrome.parent.mkdir(parents=True)
            fake_chrome.write_text("", encoding="utf-8")

            with mock.patch.dict(os.environ, {"LOCALAPPDATA": tmpdir}, clear=False):
                self.assertIn(str(fake_chrome), render_report_pdf.chrome_candidate_paths())

    def test_install_playwright_uses_current_python_environment(self):
        completed = mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch("render_report_pdf.subprocess.run", return_value=completed) as run:
            code, _ = render_report_pdf.install_playwright()

        self.assertEqual(code, 0)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0][:4], [sys.executable, "-m", "pip", "install"])
        self.assertEqual(run.call_args_list[1].args[0][:3], [sys.executable, "-m", "playwright"])

    def test_missing_input_returns_error(self):
        missing = str(Path(tempfile.gettempdir()) / "geo-audit-missing-report.md")

        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = render_report_pdf.main([missing])

        self.assertEqual(code, 2)
        self.assertIn("Markdown report not found", stderr.getvalue())

    def test_reportlab_engine_writes_timings_without_chrome_lookup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_md = Path(tmpdir) / "report.md"
            report_pdf = Path(tmpdir) / "report.pdf"
            timings_path = Path(tmpdir) / "pdf-timings.json"
            report_md.write_text("# Report\n\n正文。", encoding="utf-8")

            def fake_reportlab(markdown_text, output_path):
                output_path.write_bytes(b"%PDF-1.4\n")
                return 0, "ok"

            with mock.patch("render_report_pdf.find_chrome") as find_chrome:
                with mock.patch("render_report_pdf._render_markdown_to_pdf_reportlab", side_effect=fake_reportlab):
                    code = render_report_pdf.main([
                        str(report_md),
                        "--output",
                        str(report_pdf),
                        "--engine",
                        "reportlab",
                        "--timings-output",
                        str(timings_path),
                    ])

            self.assertEqual(code, 0)
            find_chrome.assert_not_called()
            timings = json.loads(timings_path.read_text(encoding="utf-8"))
            self.assertEqual(timings["engine"], "reportlab")
            self.assertIn("markdown_to_html_seconds", timings["timings"])
            self.assertIn("reportlab_pdf_seconds", timings["timings"])

    def test_default_engine_is_reportlab_and_does_not_probe_chrome(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_md = Path(tmpdir) / "report.md"
            report_pdf = Path(tmpdir) / "report.pdf"
            timings_path = Path(tmpdir) / "pdf-timings.json"
            report_md.write_text("# Report\n\n正文。", encoding="utf-8")

            def fake_reportlab(markdown_text, output_path):
                output_path.write_bytes(b"%PDF-1.4\n")
                return 0, "ok"

            with mock.patch.dict(os.environ, {"GEO_AUDIT_PDF_ENGINE": ""}, clear=False):
                with mock.patch("render_report_pdf.find_chrome") as find_chrome:
                    with mock.patch("render_report_pdf.print_to_pdf_with_playwright") as playwright_pdf:
                        with mock.patch("render_report_pdf._render_markdown_to_pdf_reportlab", side_effect=fake_reportlab):
                            code = render_report_pdf.main([
                                str(report_md),
                                "--output",
                                str(report_pdf),
                                "--timings-output",
                                str(timings_path),
                            ])

            self.assertEqual(code, 0)
            find_chrome.assert_not_called()
            playwright_pdf.assert_not_called()
            timings = json.loads(timings_path.read_text(encoding="utf-8"))
            self.assertEqual(timings["engine"], "reportlab")
            self.assertNotIn("chrome_lookup_seconds", timings["timings"])

    def test_pdf_generation_with_chrome_when_available(self):
        if os.environ.get("GEO_AUDIT_RUN_PDF_INTEGRATION") != "1":
            self.skipTest("Set GEO_AUDIT_RUN_PDF_INTEGRATION=1 to run real browser PDF export")
        chrome_path = render_report_pdf.find_chrome()
        if not chrome_path:
            self.skipTest("Chrome/Chromium not available")
        ready, message = render_report_pdf.chrome_pdf_ready(chrome_path)
        if not ready:
            self.skipTest(f"Chrome/Chromium cannot print PDF in this environment: {message}")

        with tempfile.TemporaryDirectory() as tmpdir:
            report_md = Path(tmpdir) / "report.md"
            report_pdf = Path(tmpdir) / "report.pdf"
            report_md.write_text(
                """# GEO 审计报告: example.com

| # | 检测项 | 权重 | 状态 | 说明 |
|---|---|---:|---|---|
| 1.1 | robots.txt 合规 | 2 | ✅ PASS | 正常 |

## 报告说明

- 完整功能可在 [adgine.ai](https://adgine.ai/) 注册后使用。
""",
                encoding="utf-8",
            )

            code = render_report_pdf.main([str(report_md), "--output", str(report_pdf), "--engine", "chrome"])

            self.assertEqual(code, 0)
            self.assertTrue(report_pdf.exists())
            self.assertGreater(report_pdf.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
