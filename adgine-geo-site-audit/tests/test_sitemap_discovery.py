import gzip
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import geo_collect  # noqa: E402


class FakeResponse:
    def __init__(self, url, status_code=200, text="", content=None, headers=None):
        self.url = url
        self.status_code = status_code
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.encoding = "utf-8"
        self.headers = headers or {}
        self.ok = 200 <= status_code < 400


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.requested = []

    def get(self, url, **kwargs):
        self.requested.append(url)
        if url in self.routes:
            value = self.routes[url]
            if isinstance(value, FakeResponse):
                return value
            status, text = value
            return FakeResponse(url, status, text)
        return FakeResponse(url, 404, "")


class SitemapDiscoveryTests(unittest.TestCase):
    def test_wordpress_robots_disallows_do_not_block_root(self):
        robots = """User-agent: *
Disallow: /wp-admin/
Disallow: /wp-json/
Disallow: /xmlrpc.php
Disallow: /wp-login.php
Disallow: /wp-includes/
Disallow: /cart/
Disallow: /checkout/
Disallow: /my-account/
Disallow: /?s=
Disallow: /search/
"""

        parsed = geo_collect._parse_robots_rules(robots)
        wildcard_disallows = parsed["rules"]["*"]

        self.assertFalse(
            any(geo_collect._robots_rule_blocks_root(rule) for rule in wildcard_disallows)
        )

    def test_root_blocking_robots_rules_are_detected(self):
        for rule in ["/", "/*", "/$", "/*$"]:
            with self.subTest(rule=rule):
                self.assertTrue(geo_collect._robots_rule_blocks_root(rule))

    def test_detects_vercel_security_checkpoint(self):
        result = geo_collect._detect_access_blocker({
            "url": "https://www.wukongsch.com/",
            "status": 429,
            "headers": {
                "Server": "Vercel",
                "X-Vercel-Mitigated": "challenge",
                "X-Vercel-Challenge-Token": "token",
            },
            "text": "<title>Vercel Security Checkpoint</title>We're verifying your browser",
            "final_url": "https://www.wukongsch.com/",
        })

        self.assertTrue(result["detected"])
        self.assertEqual(result["provider"], "Vercel")
        self.assertIn("X-Vercel-Mitigated: challenge", result["evidence"])
        self.assertEqual(result["affected_urls"][0]["status"], 429)

    def test_prioritizes_conversion_trust_and_citation_over_sitemap_order(self):
        urls = [
            "https://stripe.com/legal/ssa",
            "https://stripe.com/privacy",
            "https://stripe.com/payments",
            "https://stripe.com/billing",
            "https://stripe.com/docs/payments",
            "https://stripe.com/customers",
            "https://stripe.com/pricing",
            "https://stripe.com/reports/annual-letter",
        ]

        sampled = geo_collect._prioritize_sitemap_page_urls(urls, 5)
        sampled_urls = [item["url"] for item in sampled]
        sampled_categories = {item["category"] for item in sampled}

        self.assertIn("https://stripe.com/payments", sampled_urls)
        self.assertIn("https://stripe.com/legal/ssa", sampled_urls)
        self.assertIn("conversion", sampled_categories)
        self.assertIn("trust", sampled_categories)
        self.assertIn("citation", sampled_categories)
        self.assertEqual(sampled[0]["category"], "conversion")
        self.assertEqual(sampled[1]["category"], "trust")
        self.assertEqual(sampled[2]["category"], "citation")

    def test_falls_back_to_low_value_pages_when_no_better_pages_exist(self):
        urls = [
            "https://example.com/legal/terms",
            "https://example.com/privacy",
        ]

        sampled = geo_collect._prioritize_sitemap_page_urls(urls, 2)

        self.assertEqual(len(sampled), 2)
        self.assertEqual({item["category"] for item in sampled}, {"trust"})

    def test_keeps_one_representative_for_each_important_template(self):
        urls = [
            "https://example.com/features/realtime",
            "https://example.com/about",
            "https://example.com/blog/post-a",
            "https://example.com/careers/designer",
            "https://example.com/careers/engineer",
            "https://example.com/partners/acme",
            "https://example.com/partners/contoso",
        ]

        sampled = geo_collect._prioritize_sitemap_page_urls(urls, 5)
        sampled_pairs = {(item["category"], item["template_key"]) for item in sampled}

        self.assertIn(("conversion", "conversion"), sampled_pairs)
        self.assertIn(("trust", "trust"), sampled_pairs)
        self.assertIn(("citation", "citation"), sampled_pairs)
        self.assertIn(("template", "careers"), sampled_pairs)
        self.assertIn(("template", "partners"), sampled_pairs)

    def test_technical_entries_come_before_high_risk_validation_urls(self):
        urls = [
            "https://example.com/search?q=x",
            "https://example.com/component/FAQ",
            "https://example.com/sitemap.xml",
            "https://example.com/llms.txt",
            "https://example.com/fallback/test",
            "https://example.com/synthetic-404",
            "https://example.com/bot-blocked/path",
        ]

        sampled = geo_collect._prioritize_sitemap_page_urls(urls, 7)
        categories = [item["category"] for item in sampled]

        self.assertEqual(categories[:2], ["technical_entry", "technical_entry"])
        self.assertEqual(categories[2:], ["risk_validation"] * 5)

    def test_extracts_same_origin_homepage_links_as_sitemap_fallback_candidates(self):
        html = """
        <a href="/pricing?utm_source=nav">Pricing</a>
        <a href="/about#team">About</a>
        <a href="https://example.com/blog/how-to-choose">Guide</a>
        <a href="https://other.example.com/product">External</a>
        <a href="/assets/logo.svg">Logo</a>
        <a href="mailto:hello@example.com">Email</a>
        <a href="/pricing">Duplicate pricing</a>
        """

        urls = geo_collect._extract_homepage_candidate_urls(html, "https://example.com/")

        self.assertEqual(
            urls,
            [
                "https://example.com/pricing",
                "https://example.com/about",
                "https://example.com/blog/how-to-choose",
            ],
        )

    def test_uses_homepage_links_for_subpage_sampling_when_sitemap_has_no_urls(self):
        html = """
        <a href="/blog/how-to-choose">Guide</a>
        <a href="/pricing">Pricing</a>
        <a href="/about">About</a>
        <a href="/careers/designer">Careers</a>
        """

        entries, source, homepage_candidates = geo_collect._select_subpage_sample_entries(
            {"page_urls": []},
            html,
            "https://example.com/",
            3,
        )

        self.assertEqual(source, "homepage_links")
        self.assertEqual(len(homepage_candidates), 4)
        self.assertEqual([item["category"] for item in entries], ["conversion", "trust", "citation"])
        self.assertEqual(
            [item["url"] for item in entries],
            [
                "https://example.com/pricing",
                "https://example.com/about",
                "https://example.com/blog/how-to-choose",
            ],
        )

    def test_keeps_sitemap_sampling_when_sitemap_urls_exist(self):
        entries, source, homepage_candidates = geo_collect._select_subpage_sample_entries(
            {"page_urls": ["https://example.com/docs"]},
            '<a href="/pricing">Pricing</a>',
            "https://example.com/",
            1,
        )

        self.assertEqual(source, "sitemap")
        self.assertEqual(homepage_candidates, [])
        self.assertEqual(entries[0]["url"], "https://example.com/docs")

    def test_discovers_common_sitemap_subdirectory_path(self):
        routes = {
            "https://stripe.com/sitemap/sitemap.xml": (
                200,
                """<?xml version="1.0"?>
                <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                  <url>
                    <loc>https://stripe.com/payments</loc>
                    <lastmod>2026-05-01</lastmod>
                  </url>
                </urlset>""",
            )
        }

        result = geo_collect._discover_sitemaps(
            FakeSession(routes),
            "https://stripe.com/",
            {"text": "", "status": 404, "ok": False},
        )

        self.assertTrue(result["exists"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["url_count"], 1)
        self.assertEqual(result["page_urls"], ["https://stripe.com/payments"])
        self.assertIn("https://stripe.com/sitemap/sitemap.xml", result["sitemap_urls"])

    def test_skips_common_sitemap_fallback_when_robots_sitemap_works(self):
        robots = "User-agent: *\nSitemap: https://example.com/custom-sitemap.xml\n"
        routes = {
            "https://example.com/custom-sitemap.xml": (
                200,
                """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                  <url><loc>https://example.com/from-robots</loc></url>
                </urlset>""",
            ),
            "https://example.com/sitemap.xml": (
                200,
                """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                  <url><loc>https://example.com/from-fallback</loc></url>
                </urlset>""",
            ),
        }
        fake_session = FakeSession(routes)

        result = geo_collect._discover_sitemaps(
            fake_session,
            "https://example.com/",
            {"text": robots, "status": 200, "ok": True},
        )

        self.assertEqual(result["page_urls"], ["https://example.com/from-robots"])
        self.assertNotIn("https://example.com/sitemap.xml", fake_session.requested)

    def test_uses_common_sitemap_fallback_when_robots_sitemap_fails(self):
        robots = "User-agent: *\nSitemap: https://example.com/missing-sitemap.xml\n"
        routes = {
            "https://example.com/sitemap.xml": (
                200,
                """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                  <url><loc>https://example.com/from-fallback</loc></url>
                </urlset>""",
            ),
        }
        fake_session = FakeSession(routes)

        result = geo_collect._discover_sitemaps(
            fake_session,
            "https://example.com/",
            {"text": robots, "status": 200, "ok": True},
        )

        self.assertEqual(result["page_urls"], ["https://example.com/from-fallback"])
        self.assertIn("https://example.com/missing-sitemap.xml", fake_session.requested)
        self.assertIn("https://example.com/sitemap.xml", fake_session.requested)

    def test_decodes_gzipped_sitemap_candidate(self):
        sitemap = b"""<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/gzipped</loc></url>
        </urlset>"""
        gz_url = "https://example.com/sitemap.xml.gz"
        routes = {
            gz_url: FakeResponse(
                gz_url,
                200,
                content=gzip.compress(sitemap),
                headers={"Content-Type": "application/x-gzip"},
            )
        }

        result = geo_collect._discover_sitemaps(
            FakeSession(routes),
            "https://example.com/",
            {"text": "", "status": 404, "ok": False},
        )

        self.assertTrue(result["exists"])
        self.assertEqual(result["page_urls"], ["https://example.com/gzipped"])

    def test_follows_sitemap_indexes_from_robots(self):
        robots = "User-agent: *\nDisallow:\nSitemap: https://example.com/sitemap.xml\n"
        routes = {
            "https://example.com/sitemap.xml": (
                200,
                """<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                  <sitemap>
                    <loc>https://example.com/products.xml</loc>
                    <lastmod>2026-01-10</lastmod>
                  </sitemap>
                  <sitemap>
                    <loc>https://example.com/blog.xml</loc>
                    <lastmod>2026-02-20</lastmod>
                  </sitemap>
                </sitemapindex>""",
            ),
            "https://example.com/products.xml": (
                200,
                """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                  <url><loc>https://example.com/a</loc><lastmod>2026-03-01</lastmod></url>
                  <url><loc>https://example.com/b</loc><lastmod>2026-03-02</lastmod></url>
                </urlset>""",
            ),
            "https://example.com/blog.xml": (
                200,
                """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                  <url><loc>https://example.com/b</loc><lastmod>2026-03-03</lastmod></url>
                  <url><loc>https://example.com/c</loc><lastmod>2026-03-04</lastmod></url>
                </urlset>""",
            ),
        }

        result = geo_collect._discover_sitemaps(
            FakeSession(routes),
            "https://example.com/",
            {"text": robots, "status": 200, "ok": True},
        )

        self.assertTrue(result["exists"])
        self.assertTrue(result["robots_declares_sitemap"])
        self.assertEqual(result["child_sitemap_count"], 2)
        self.assertEqual(result["url_count"], 3)
        self.assertEqual(result["latest_lastmod"], "2026-03-04")
        self.assertEqual(
            result["page_urls"],
            ["https://example.com/a", "https://example.com/b", "https://example.com/c"],
        )


if __name__ == "__main__":
    unittest.main()
