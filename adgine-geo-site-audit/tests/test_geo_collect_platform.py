import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import geo_collect  # noqa: E402


class GeoCollectPlatformTests(unittest.TestCase):
    def test_default_subpage_sample_is_twenty(self):
        self.assertEqual(geo_collect.MAX_SUBPAGES, 20)

    def test_bounded_workers_caps_concurrency(self):
        self.assertEqual(geo_collect._bounded_workers(0), 1)
        self.assertEqual(geo_collect._bounded_workers(6), 6)
        self.assertEqual(geo_collect._bounded_workers(100), 12)

    def test_chrome_candidates_include_windows_playwright_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_chrome = (
                Path(tmpdir)
                / "ms-playwright"
                / "chromium_headless_shell-1208"
                / "chrome-win"
                / "headless_shell.exe"
            )
            fake_chrome.parent.mkdir(parents=True)
            fake_chrome.write_text("", encoding="utf-8")

            with mock.patch.dict(os.environ, {"LOCALAPPDATA": tmpdir}, clear=False):
                self.assertIn(str(fake_chrome), geo_collect._chrome_candidate_paths())


class ParseHtmlTests(unittest.TestCase):
    """Tests for _parse_html including lang and schema extraction."""

    def test_extracts_html_lang(self):
        html = '<html lang="zh-CN"><head><title>Test</title></head><body></body></html>'
        info = geo_collect._parse_html(html, "https://example.com")
        self.assertEqual(info["html_lang"], "zh-CN")

    def test_html_lang_empty_when_missing(self):
        html = '<html><head><title>Test</title></head><body></body></html>'
        info = geo_collect._parse_html(html, "https://example.com")
        self.assertEqual(info["html_lang"], "")

    def test_extracts_schema_from_graph_format(self):
        html = '''<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
  {"@type":"Organization","name":"Test Org"},
  {"@type":"WebSite","name":"Test Site"}
]}
</script>
</head><body></body></html>'''
        info = geo_collect._parse_html(html, "https://example.com")
        self.assertIn("Organization", info["schema_types"])
        self.assertIn("WebSite", info["schema_types"])

    def test_schema_not_extracted_from_decomposed_scripts(self):
        """Regression: schema must be extracted before script decompose."""
        html = '''<html><head>
<script type="application/ld+json">
{"@type":"Organization","name":"Test"}
</script>
</head><body><p>Hello</p></body></html>'''
        info = geo_collect._parse_html(html, "https://example.com")
        self.assertIn("Organization", info["schema_types"])
        # body_text should NOT contain JSON-LD content
        self.assertNotIn("Organization", info["body_text"])

    def test_extracts_internal_and_external_links(self):
        """Link extraction classifies by netloc."""
        html = '''<html><head><title>T</title></head><body>
<a href="/about">About</a>
<a href="https://example.com/pricing">Pricing</a>
<a href="https://other.com/ref">External</a>
<a href="mailto:a@b.com">Mail</a>
<a href="#section">Fragment</a>
<a href="javascript:void(0)">JS</a>
</body></html>'''
        info = geo_collect._parse_html(html, "https://example.com")
        self.assertIn("https://example.com/about", info["internal_links"])
        self.assertIn("https://example.com/pricing", info["internal_links"])
        self.assertIn("https://other.com/ref", info["external_links"])
        # mailto, fragment, javascript should be excluded
        all_links = info["internal_links"] + info["external_links"]
        self.assertTrue(all("mailto:" not in l for l in all_links))
        self.assertTrue(all(l.startswith("http") for l in all_links))

    def test_links_empty_without_base_url(self):
        html = '<html><body><a href="/x">X</a></body></html>'
        info = geo_collect._parse_html(html, "")
        self.assertEqual(info["internal_links"], [])
        self.assertEqual(info["external_links"], [])


class CollectD5Tests(unittest.TestCase):
    """Tests for _collect_d5 signal generation."""

    def setUp(self):
        self.homepage_info = {
            "internal_links": ["/blog/", "/pricing/", "/signup/"],
            "external_links": ["https://youtube.com/@test", "https://linkedin.com/company/test"],
            "body_text": "Sign up for free trial Get started today Contact us Download now",
            "html_lang": "en",
            "hreflang_count": 0,
        }
        self.sub_page_infos = [
            {"internal_links": ["/blog/post-1/"], "external_links": []},
            {"internal_links": ["/docs/guide/"], "external_links": ["https://github.com/test/repo"]},
        ]
        self.homepage_result = {"ok": True, "final_url": "https://example.com/", "url": "https://example.com/"}
        self.sub_page_results = [
            {"ok": True, "final_url": "https://example.com/blog/post-1/", "url": "https://example.com/blog/post-1/"},
            {"ok": True, "final_url": "https://example.com/docs/guide/", "url": "https://example.com/docs/guide/"},
        ]

    def test_detects_blog_and_resource_hub(self):
        signals, _ = geo_collect._collect_d5(
            self.homepage_info, self.sub_page_infos,
            self.homepage_result, self.sub_page_results,
        )
        self.assertTrue(signals["d5_content_assets"]["blog_detected"])
        self.assertTrue(signals["d5_content_assets"]["resource_hub_detected"])

    def test_detects_pricing_and_signup(self):
        signals, _ = geo_collect._collect_d5(
            self.homepage_info, self.sub_page_infos,
            self.homepage_result, self.sub_page_results,
        )
        self.assertTrue(signals["d5_content_assets"]["pricing_detected"])
        self.assertIn("signup", signals["d5_content_assets"]["conversion_pages"])

    def test_detects_external_platforms(self):
        signals, _ = geo_collect._collect_d5(
            self.homepage_info, self.sub_page_infos,
            self.homepage_result, self.sub_page_results,
        )
        platforms = signals["d5_content_assets"]["external_platforms"]
        self.assertIn("YouTube", platforms)
        self.assertIn("LinkedIn", platforms)
        self.assertIn("GitHub", platforms)

    def test_detects_homepage_cta(self):
        signals, _ = geo_collect._collect_d5(
            self.homepage_info, self.sub_page_infos,
            self.homepage_result, self.sub_page_results,
        )
        self.assertTrue(signals["d5_cta"]["has_clear_cta"])
        self.assertIn("sign up", signals["d5_cta"]["homepage_cta_keywords"])

    def test_empty_subpages_does_not_crash(self):
        signals, _ = geo_collect._collect_d5(
            self.homepage_info, [],
            self.homepage_result, [],
        )
        self.assertIsNotNone(signals["d5_content_assets"])


if __name__ == "__main__":
    unittest.main()
