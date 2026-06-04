#!/usr/bin/env python3
"""GEO Audit Signal Collector — collects structured signals for agent judgment.

Usage:
    python scripts/geo_collect.py <url> [--output <path>] [--render auto|always|never]
                                  [--max-subpages 20] [--concurrency 6]

Outputs a JSON object with:
  - meta: fetch metadata (url, domain, render_method, fetched_at, timings)
  - signals: per-check programmatic signals (numbers, booleans, lists)
  - snippets: text excerpts for agent semantic judgment (max ~500 chars each)
  - errors: any collection failures
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote as _url_quote, urljoin, urlparse
from xml.etree import ElementTree

try:
    from curl_cffi import requests
    from bs4 import BeautifulSoup
except ImportError as _exc:
    print(f"ERROR: Missing dependency — {_exc.name}")
    print("  Fix: pip install -r adgine-geo-site-audit/requirements.txt")
    print("  Or:  pip install curl_cffi beautifulsoup4 lxml")
    sys.exit(1)

# Default browser impersonation profile for curl_cffi
_IMPERSONATE = "chrome"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

DEFAULT_TIMEOUT = 15
MAX_SUBPAGES = 20
DEFAULT_CONCURRENCY = 6
MAX_SITEMAP_FETCHES = 25
MAX_SITEMAP_PAGE_URLS = 5000
SNIPPET_MAX_LEN = 500

CRAWLER_UAS: dict[str, str] = {
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.0; +https://openai.com/gptbot",
    "ChatGPT-User": "Mozilla/5.0 (compatible; ChatGPT-User/1.0; +https://openai.com/bot)",
    "ClaudeBot": "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "PerplexityBot": "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    "Googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Bingbot": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Google-Extended": "Mozilla/5.0 (compatible; Google-Extended)",
    "Bytespider": "Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)",
    "CCBot": "CCBot/2.0 (https://commoncrawl.org/faq/)",
}

DEFAULT_UA = "Mozilla/5.0 (compatible; AdgineGeoAudit/1.0)"

TRUST_PATHS_EN = ["contact", "privacy", "terms", "security", "support", "about"]
TRUST_PATHS_ZH = ["联系我们", "隐私政策", "服务条款", "安全", "帮助中心", "关于我们"]

EXPERIENCE_KEYWORDS = [
    "screenshot", "截图", "实测", "case study", "hands-on", "demo",
    "backtest", "教程", "客户反馈", "testimonial", "before and after",
    "roi", "tutorial", "实操", "评测",
]

AUTHORITY_SOURCES = [".gov", ".edu", "reuters.com", "bloomberg.com", "gartner.com",
                     "mckinsey.com", "who.int", "worldbank.org", "statista.com"]

ASSET_KEYWORDS = {
    "guide": ["guide", "指南"],
    "comparison": ["comparison", "对比", " vs ", "versus"],
    "case_study": ["case study", "案例", "customer story"],
    "methodology": ["methodology", "方法论", "framework", "框架"],
    "report": ["report", "报告", "whitepaper", "白皮书"],
    "glossary": ["glossary", "术语", "词汇表"],
    "tutorial": ["tutorial", "教程", "how-to", "quickstart"],
}

SITEMAP_CANDIDATE_PATHS = [
    "/sitemap.xml",
    "/sitemap.xml.gz",
    "/sitemap_index.xml",
    "/sitemap_index.xml.gz",
    "/sitemap-index.xml",
    "/sitemap-index.xml.gz",
    "/sitemap/sitemap.xml",
    "/sitemap/sitemap_index.xml",
    "/sitemap/sitemap-index.xml",
    "/sitemaps.xml",
    "/sitemaps/sitemap.xml",
    "/wp-sitemap.xml",
    "/page-sitemap.xml",
    "/post-sitemap.xml",
]

SITEMAP_PRODUCT_SEGMENTS = {
    "products", "product", "payments", "billing", "checkout", "connect",
    "tax", "radar", "terminal", "issuing", "treasury", "atlas", "identity",
    "invoicing", "subscriptions", "sigma", "climate", "capital",
    "financial-connections", "payment-links",
}

SITEMAP_CONVERSION_SEGMENTS = SITEMAP_PRODUCT_SEGMENTS | {
    "service", "services", "course", "courses", "solution", "solutions",
    "feature", "features", "pricing", "prices", "fees", "plans",
    "app-download", "download", "downloads", "app", "apps", "signup",
    "sign-up", "register", "join", "start", "trial", "demo", "book-demo",
    "campaign", "campaigns", "activity", "activities", "event", "events",
    "promo", "promotions", "offer", "offers",
}

SITEMAP_TRUST_SEGMENTS = {
    "about", "contact", "company", "team", "support", "privacy", "terms",
    "legal", "risk", "risks", "security", "trust", "regulatory",
    "regulation", "compliance", "reviews", "review", "licenses", "license",
    "responsible", "safety",
}

SITEMAP_CITATION_SEGMENTS = {
    "guides", "guide", "docs", "documentation", "developers", "developer",
    "help", "faq", "faqs", "questions", "compare", "comparison",
    "alternatives", "vs", "blog", "blogs", "glossary", "resources",
    "resource", "learn", "tutorial", "tutorials", "article", "articles",
    "news", "reports", "report", "research", "whitepapers", "whitepaper",
    "ebooks", "ebook", "academy", "case-studies", "case-study", "stories",
    "customers", "customer-stories",
}

SITEMAP_TECHNICAL_SEGMENTS = {
    "robots.txt", "sitemap.xml", "sitemap_index.xml", "sitemap-index.xml",
    "sitemaps.xml", "wp-sitemap.xml", "page-sitemap.xml", "post-sitemap.xml",
    "llms.txt", "llms-full.txt",
}

SITEMAP_RISK_SEGMENTS = {
    "404", "not-found", "notfound", "error", "errors", "fallback",
    "component", "components", "search", "login", "signin", "sign-in",
    "dashboard", "auth", "account", "wp-json", "xmlrpc.php", "synthetic",
    "synthetic-404", "blocked", "bot-blocked", "bot", "challenge",
}

SITEMAP_CATEGORY_SCORES = {
    "conversion": 170,
    "trust": 150,
    "citation": 135,
    "template": 90,
    "technical_entry": 20,
    "risk_validation": -60,
    "default": 40,
    "asset": -120,
    "homepage": -200,
}

SITEMAP_SAMPLE_CATEGORY_ORDER = [
    "conversion",
    "trust",
    "citation",
    "template",
    "technical_entry",
    "default",
]

HOMEPAGE_LINK_SKIP_EXTENSIONS = {
    ".7z", ".avi", ".css", ".csv", ".doc", ".docx", ".eot", ".gif", ".ico",
    ".jpeg", ".jpg", ".js", ".json", ".m4a", ".mov", ".mp3", ".mp4", ".otf",
    ".pdf", ".png", ".rar", ".rss", ".svg", ".ttf", ".txt", ".wav", ".webm",
    ".webmanifest", ".webp", ".woff", ".woff2", ".xls", ".xlsx", ".xml",
    ".zip",
}

# ============================================================================
# HTTP Layer
# ============================================================================

_CHROME_PATHS: list[str] = [
    "headless_shell",
    "headless_shell.exe",
    "chromium",
    "chromium.exe",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "chrome",
    "chrome.exe",
    "msedge",
    "msedge.exe",
    "/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def _chrome_candidate_paths() -> list[str]:
    candidates: list[str] = []
    env_path = os.environ.get("GEO_AUDIT_CHROME_PATH")
    if env_path:
        candidates.append(env_path)

    home = os.path.expanduser("~")
    local_app_data = os.environ.get("LOCALAPPDATA")
    program_files = [os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)")]

    patterns = [
        os.path.join(home, "Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-*/headless_shell"),
        os.path.join(home, "Library/Caches/ms-playwright/chromium-*/chrome-*/headless_shell"),
        os.path.join(home, "Library/Caches/ms-playwright/chromium-*/chrome-*/Chromium.app/Contents/MacOS/Chromium"),
        os.path.join(home, "Library/Caches/ms-playwright/chromium-*/chrome-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"),
        os.path.join(home, ".cache/ms-playwright/chromium_headless_shell-*/chrome-*/headless_shell"),
        os.path.join(home, ".cache/ms-playwright/chromium-*/chrome-*/headless_shell"),
    ]
    if local_app_data:
        patterns.extend([
            os.path.join(local_app_data, "ms-playwright", "chromium_headless_shell-*", "chrome-win", "headless_shell.exe"),
            os.path.join(local_app_data, "ms-playwright", "chromium-*", "chrome-win", "headless_shell.exe"),
            os.path.join(local_app_data, "ms-playwright", "chromium-*", "chrome-win", "chrome.exe"),
            os.path.join(local_app_data, "ms-playwright", "chromium-*", "chrome-win", "Chromium.exe"),
        ])
    for base in program_files:
        if not base:
            continue
        candidates.extend([
            os.path.join(base, "Google", "Chrome for Testing", "Application", "chrome.exe"),
            os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(base, "Chromium", "Application", "chrome.exe"),
        ])
    for pattern in patterns:
        candidates.extend(sorted(glob.glob(pattern), reverse=True))
    candidates.extend(_CHROME_PATHS)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def _get(session: requests.Session, url: str, *, ua: str = DEFAULT_UA,
         timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch a URL and return a dict with status, headers, text, final_url, error."""
    try:
        # When using a custom (bot) UA, skip impersonate to avoid TLS/UA mismatch.
        # When using the default audit UA, rely on impersonate for full browser mimicry.
        use_impersonate = (ua == DEFAULT_UA)
        kwargs: dict[str, Any] = {
            "timeout": timeout,
            "allow_redirects": True,
        }
        if use_impersonate:
            kwargs["impersonate"] = _IMPERSONATE
        else:
            kwargs["headers"] = {"User-Agent": ua, "Accept": "*/*"}
        r = session.get(url, **kwargs)
        text = ""
        try:
            content_type = r.headers.get("Content-Type", "").lower()
            is_gzip_sitemap = (
                urlparse(r.url).path.endswith(".gz")
                or "application/x-gzip" in content_type
            )
            if is_gzip_sitemap:
                text = gzip.decompress(r.content).decode(
                    r.encoding or "utf-8", errors="replace"
                )
            else:
                text = r.text
        except Exception:
            try:
                text = r.text
            except Exception:
                pass
        return {
            "url": url, "status": r.status_code, "ok": r.ok,
            "headers": dict(r.headers), "text": text,
            "final_url": r.url, "error": "",
        }
    except (requests.RequestsError, OSError) as e:
        return {"url": url, "status": 0, "ok": False, "headers": {},
                "text": "", "final_url": "", "error": str(e)}


def _get_with_new_session(url: str, *, ua: str = DEFAULT_UA,
                          timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch a URL in a worker thread with an isolated curl_cffi session."""
    with requests.Session() as session:
        return _get(session, url, ua=ua, timeout=timeout)


def _bounded_workers(concurrency: int) -> int:
    return max(1, min(int(concurrency or 1), 12))


def _timed_call(func, *args, **kwargs) -> tuple[Any, float]:
    started = time.perf_counter()
    result = func(*args, **kwargs)
    return result, round(time.perf_counter() - started, 3)


def _parallel_fetch(
    jobs: list[tuple[str, str, str]],
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, dict]:
    """Fetch jobs concurrently and return results by caller-provided key."""
    if not jobs:
        return {}
    workers = min(_bounded_workers(concurrency), len(jobs))
    job_by_key = {key: (url, ua) for key, url, ua in jobs}
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_key = {
            executor.submit(_get_with_new_session, url, ua=ua, timeout=timeout): key
            for key, url, ua in jobs
        }
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                url, _ua = job_by_key[key]
                results[key] = {
                    "url": url,
                    "status": 0,
                    "ok": False,
                    "headers": {},
                    "text": "",
                    "final_url": url,
                    "error": str(exc),
                }
    return results


def _detect_access_blocker(*results: dict) -> dict:
    """Detect edge/security challenges that hide the real page from crawlers."""
    evidence: list[str] = []
    affected_urls: list[dict[str, Any]] = []
    providers: set[str] = set()

    for result in results:
        if not result:
            continue

        status = result.get("status", 0)
        headers = {k.lower(): str(v) for k, v in result.get("headers", {}).items()}
        text = (result.get("text") or "")[:50000].lower()
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", text, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""

        result_evidence: list[str] = []
        if status in {401, 403, 429}:
            result_evidence.append(f"HTTP {status}")
        if headers.get("x-vercel-mitigated") == "challenge":
            providers.add("Vercel")
            result_evidence.append("X-Vercel-Mitigated: challenge")
        if "x-vercel-challenge-token" in headers:
            providers.add("Vercel")
            result_evidence.append("X-Vercel-Challenge-Token present")
        if headers.get("server", "").lower() == "vercel":
            providers.add("Vercel")
        if "cf-mitigated" in headers or "cf-chl" in text:
            providers.add("Cloudflare")
            result_evidence.append("Cloudflare challenge signal")
        if "vercel security checkpoint" in text or "vercel security checkpoint" in title:
            providers.add("Vercel")
            result_evidence.append("Vercel Security Checkpoint page")
        if "we're verifying your browser" in text or "enable javascript to continue" in text:
            result_evidence.append("browser verification copy")
        if "just a moment" in title and "cloudflare" in text:
            providers.add("Cloudflare")
            result_evidence.append("Cloudflare Just a moment page")

        if result_evidence:
            affected_urls.append({
                "url": result.get("url", ""),
                "status": status,
                "final_url": result.get("final_url", ""),
                "evidence": result_evidence,
            })
            evidence.extend(result_evidence)

    return {
        "detected": bool(affected_urls),
        "provider": ", ".join(sorted(providers)) if providers else "",
        "evidence": _dedupe_preserve_order(evidence),
        "affected_urls": affected_urls[:10],
    }


def _find_chrome() -> Optional[str]:
    for path in _chrome_candidate_paths():
        if shutil.which(path):
            return path
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _render_chrome(url: str, timeout: int = 20) -> Optional[str]:
    chrome = _find_chrome()
    if not chrome:
        return None
    try:
        result = subprocess.run(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--disable-breakpad",
                "--disable-crash-reporter",
                "--noerrdialogs",
                "--no-sandbox",
                "--dump-dom",
                url,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None


_SPA_MARKERS = ("__NEXT_DATA__", "window.__NUXT__", "window.__APP__",
                'id="app"', 'id="root"', 'id="__next"', "ng-app", "data-reactroot")


def _is_spa_shell(html: str) -> bool:
    if not html:
        return True
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    words = text.split()
    if len(words) < 50:
        return True
    if len(words) < 150:
        lower = html.lower()
        if any(m.lower() in lower for m in _SPA_MARKERS):
            return True
    return False


# ============================================================================
# HTML Parsing
# ============================================================================

def _parse_html(html: str, base_url: str = "") -> dict:
    """Parse HTML into structured page info dict."""
    info: dict[str, Any] = {
        "title": "", "description": "", "canonical": "", "meta_robots": "",
        "h1": [], "h2": [], "h3": [], "h4": [], "h5": [], "h6": [],
        "schema_types": [], "schema_blocks": [],
        "internal_links": [], "external_links": [], "word_count": 0,
        "paragraphs": [], "ol_count": 0, "ul_count": 0, "li_count": 0,
        "time_elements": [], "visible_dates": [], "body_text": "",
        "has_faq_visible": False, "hreflang_count": 0,
        "html_lang": "",
        "og_tags": {}, "twitter_tags": {}, "image_count": 0,
        "images_missing_alt": 0, "images_weak_alt": 0, "table_count": 0,
    }
    if not html:
        return info

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Language
    html_el = soup.find("html")
    if html_el and html_el.get("lang"):
        info["html_lang"] = html_el["lang"].strip()

    # Title
    if soup.title and soup.title.string:
        info["title"] = soup.title.string.strip()

    # Meta
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        info["description"] = desc["content"].strip()

    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        info["canonical"] = canonical["href"].strip()

    meta_robots = soup.find("meta", attrs={"name": "robots"})
    if meta_robots and meta_robots.get("content"):
        info["meta_robots"] = meta_robots["content"].strip()

    info["hreflang_count"] = len(soup.find_all("link", attrs={"rel": "alternate", "hreflang": True}))

    # Headings
    info["h1"] = [t.get_text(strip=True) for t in soup.find_all("h1")]
    info["h2"] = [t.get_text(strip=True) for t in soup.find_all("h2")]
    info["h3"] = [t.get_text(strip=True) for t in soup.find_all("h3")]
    info["h4"] = [t.get_text(strip=True) for t in soup.find_all("h4")]
    info["h5"] = [t.get_text(strip=True) for t in soup.find_all("h5")]
    info["h6"] = [t.get_text(strip=True) for t in soup.find_all("h6")]

    # Lists
    info["ol_count"] = len(soup.find_all("ol"))
    info["ul_count"] = len(soup.find_all("ul"))
    info["li_count"] = len(soup.find_all("li"))
    info["table_count"] = len(soup.find_all("table"))

    # Images and social metadata
    images = soup.find_all("img")
    info["image_count"] = len(images)
    weak_alt_values = {"image", "photo", "picture", "logo", "icon", "banner", "图片", "照片", "图像"}
    for image in images:
        alt = (image.get("alt") or "").strip()
        if not alt:
            info["images_missing_alt"] += 1
        elif alt.lower() in weak_alt_values or len(alt) <= 3:
            info["images_weak_alt"] += 1

    for meta in soup.find_all("meta"):
        prop = meta.get("property") or meta.get("name") or ""
        content = meta.get("content") or ""
        if not prop or not content:
            continue
        prop_lower = prop.lower()
        if prop_lower.startswith("og:"):
            info["og_tags"][prop_lower] = content.strip()
        elif prop_lower.startswith("twitter:"):
            info["twitter_tags"][prop_lower] = content.strip()

    # Paragraphs
    info["paragraphs"] = [
        p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)
    ]

    # Time elements
    for t in soup.find_all("time"):
        dt = t.get("datetime", "")
        if dt:
            info["time_elements"].append(dt)

    # Visible dates
    body_text_raw = soup.get_text(" ", strip=True)
    info["visible_dates"] = re.findall(
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", body_text_raw
    )

    # Schema.org JSON-LD (must be extracted BEFORE scripts are decomposed)
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string)
            # Handle @graph wrapper (common in Yoast SEO / RankMath / Next.js)
            if isinstance(data, dict) and "@graph" in data and isinstance(data["@graph"], list):
                blocks = data["@graph"]
            else:
                blocks = data if isinstance(data, list) else [data]
            for block in blocks:
                if isinstance(block, dict):
                    info["schema_blocks"].append(block)
                    # Recurse into nested @graph if present (rare but valid)
                    nested_graph = block.get("@graph", [])
                    if isinstance(nested_graph, list):
                        for sub in nested_graph:
                            if isinstance(sub, dict):
                                info["schema_blocks"].append(sub)
                                t = sub.get("@type", "")
                                if isinstance(t, list):
                                    info["schema_types"].extend(t)
                                elif t:
                                    info["schema_types"].append(t)
                    t = block.get("@type", "")
                    if isinstance(t, list):
                        info["schema_types"].extend(t)
                    elif t:
                        info["schema_types"].append(t)
        except (json.JSONDecodeError, TypeError):
            pass

    # Links (extracted before decompose to preserve <a> in <noscript> if any)
    if base_url:
        parsed_base = urlparse(base_url)
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "sms:")):
                continue
            absolute = urljoin(base_url, href)
            link_parsed = urlparse(absolute)
            if link_parsed.scheme not in ("http", "https"):
                continue
            if link_parsed.netloc.lower() == parsed_base.netloc.lower():
                info["internal_links"].append(absolute)
            else:
                info["external_links"].append(absolute)

    # Body text (stripped of scripts/styles)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    info["body_text"] = soup.get_text(" ", strip=True)
    info["word_count"] = len(info["body_text"].split())

    # FAQ detection
    faq_kws = ["faq", "常见问题", "frequently asked", "q&a"]
    text_lower = info["body_text"].lower()
    headings_lower = " ".join(info["h2"] + info["h3"]).lower()
    if any(kw in text_lower or kw in headings_lower for kw in faq_kws):
        info["has_faq_visible"] = True
    if "FAQPage" in info["schema_types"]:
        info["has_faq_visible"] = True

    return info


# ============================================================================
# Sitemap / Robots Parsing
# ============================================================================

def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _xml_tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _parse_sitemap_xml(sitemap_text: str, sitemap_url: str) -> dict:
    """Parse a sitemap or sitemap index and return URLs, lastmods, and metadata."""
    parsed: dict[str, Any] = {
        "page_urls": [],
        "child_sitemaps": [],
        "lastmods": [],
        "has_hreflang": False,
        "root_tag": "",
    }
    if not sitemap_text:
        return parsed

    parsed["has_hreflang"] = "xhtml:link" in sitemap_text or "hreflang" in sitemap_text

    try:
        root = ElementTree.fromstring(sitemap_text.encode("utf-8"))
        root_tag = _xml_tag_name(root.tag)
        parsed["root_tag"] = root_tag
        parsed["lastmods"] = [
            (node.text or "").strip()
            for node in root.iter()
            if _xml_tag_name(node.tag) == "lastmod" and (node.text or "").strip()
        ]
        if root_tag == "sitemapindex":
            locs = [
                (node.text or "").strip()
                for sitemap in root
                for node in sitemap
                if _xml_tag_name(sitemap.tag) == "sitemap"
                and _xml_tag_name(node.tag) == "loc"
                and (node.text or "").strip()
            ]
            parsed["child_sitemaps"] = [urljoin(sitemap_url, loc) for loc in locs]
        else:
            locs = [
                (node.text or "").strip()
                for url_node in root
                for node in url_node
                if _xml_tag_name(url_node.tag) == "url"
                and _xml_tag_name(node.tag) == "loc"
                and (node.text or "").strip()
            ]
            parsed["page_urls"] = locs
        return parsed
    except ElementTree.ParseError:
        pass

    # Fallback for malformed XML that still contains useful sitemap tags.
    locs = [u.strip() for u in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sitemap_text)]
    parsed["lastmods"] = [
        u.strip() for u in re.findall(r"<lastmod>\s*([^<]+?)\s*</lastmod>", sitemap_text)
    ]
    is_index = "<sitemapindex" in sitemap_text.lower()
    if is_index:
        parsed["root_tag"] = "sitemapindex"
        parsed["child_sitemaps"] = [urljoin(sitemap_url, loc) for loc in locs]
    else:
        parsed["root_tag"] = "urlset"
        parsed["page_urls"] = locs
    return parsed


def _sitemap_candidate_urls(base_url: str, robots_sitemap_urls: list[str]) -> list[str]:
    candidates = [urljoin(base_url, value) for value in robots_sitemap_urls]
    candidates.extend(urljoin(base_url, path) for path in SITEMAP_CANDIDATE_PATHS)
    return _dedupe_preserve_order(candidates)


def _sitemap_path_segments(page_url: str) -> list[str]:
    path = urlparse(page_url).path.lower().strip("/")
    segments = [segment for segment in path.split("/") if segment]
    while segments and (
        segments[0] in {"en", "zh", "ja", "jp", "ko", "fr", "de", "es", "pt"}
        or re.fullmatch(r"[a-z]{2}[-_][a-z]{2}", segments[0])
    ):
        segments.pop(0)
    return segments


def _classify_sitemap_page_url(page_url: str) -> str:
    segments = _sitemap_path_segments(page_url)
    if not segments:
        return "homepage"

    first = segments[0]
    path = "/" + "/".join(segments)
    joined = " ".join(segments)

    if re.search(r"\.(pdf|png|jpg|jpeg|webp|gif|svg|zip)$", path):
        return "asset"
    if first in SITEMAP_TECHNICAL_SEGMENTS or any(segment in SITEMAP_TECHNICAL_SEGMENTS for segment in segments):
        return "technical_entry"
    if (
        first in SITEMAP_RISK_SEGMENTS
        or any(segment in SITEMAP_RISK_SEGMENTS for segment in segments)
        or urlparse(page_url).query
    ):
        return "risk_validation"
    if (
        first in SITEMAP_CONVERSION_SEGMENTS
        or any(segment in SITEMAP_CONVERSION_SEGMENTS for segment in segments[:2])
    ):
        return "conversion"
    if first in SITEMAP_TRUST_SEGMENTS or any(segment in SITEMAP_TRUST_SEGMENTS for segment in segments[:2]):
        return "trust"
    if (
        first in SITEMAP_CITATION_SEGMENTS
        or any(segment in SITEMAP_CITATION_SEGMENTS for segment in segments[:2])
        or any(token in joined for token in ("alternatives", "comparison", "compare", " vs ", "versus"))
    ):
        return "citation"
    return "template"


def _score_sitemap_page_url(page_url: str) -> tuple[int, str]:
    category = _classify_sitemap_page_url(page_url)
    segments = _sitemap_path_segments(page_url)
    score = SITEMAP_CATEGORY_SCORES.get(category, SITEMAP_CATEGORY_SCORES["default"])

    if category == "conversion" and len(segments) == 1:
        score += 30
    elif category in {"trust", "citation"} and len(segments) <= 2:
        score += 15
    elif category == "template" and len(segments) <= 2:
        score += 8

    if len(segments) > 4:
        score -= (len(segments) - 4) * 4
    if urlparse(page_url).query:
        score -= 25

    return score, category


def _sitemap_template_key(page_url: str, category: str) -> str:
    segments = _sitemap_path_segments(page_url)
    if category != "template":
        return category
    if not segments:
        return "homepage"
    return segments[0]


def _canonical_sitemap_sample_key(page_url: str) -> str:
    parsed = urlparse(page_url)
    segments = _sitemap_path_segments(page_url)
    path = "/" + "/".join(segments)
    return f"{parsed.netloc.lower()}{path.rstrip('/')}"


def _normalize_homepage_link_url(href: str, base_url: str) -> Optional[str]:
    if not href:
        return None
    href = href.strip()
    if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "sms:")):
        return None

    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    parsed_base = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc.lower() != parsed_base.netloc.lower():
        return None

    extension = os.path.splitext(parsed.path.lower())[1]
    if extension in HOMEPAGE_LINK_SKIP_EXTENSIONS:
        return None

    normalized = parsed._replace(fragment="", query="")
    return normalized.geturl().rstrip("/") or normalized.geturl()


def _extract_homepage_candidate_urls(homepage_html: str, base_url: str) -> list[str]:
    """Extract same-origin page candidates from the homepage when sitemap URLs are unavailable."""
    if not homepage_html or not base_url:
        return []
    try:
        soup = BeautifulSoup(homepage_html, "lxml")
    except Exception:
        soup = BeautifulSoup(homepage_html, "html.parser")

    urls: list[str] = []
    for anchor in soup.find_all("a", href=True):
        normalized = _normalize_homepage_link_url(anchor.get("href", ""), base_url)
        if normalized:
            urls.append(normalized)
    return _dedupe_preserve_order(urls)[:MAX_SITEMAP_PAGE_URLS]


def _select_subpage_sample_entries(
    sitemap_info: dict[str, Any],
    homepage_html: str,
    base_url: str,
    limit: int = MAX_SUBPAGES,
) -> tuple[list[dict[str, Any]], str, list[str]]:
    sitemap_page_urls = sitemap_info.get("page_urls", []) or []
    if sitemap_page_urls:
        return _prioritize_sitemap_page_urls(sitemap_page_urls, limit), "sitemap", []

    homepage_candidate_urls = _extract_homepage_candidate_urls(homepage_html, base_url)
    if not homepage_candidate_urls:
        return [], "none", []
    return (
        _prioritize_sitemap_page_urls(homepage_candidate_urls, limit),
        "homepage_links",
        homepage_candidate_urls,
    )


def _prioritize_sitemap_page_urls(page_urls: list[str], limit: int = MAX_SUBPAGES) -> list[dict[str, Any]]:
    """Pick representative pages using GEO sampling priority, not sitemap order.

    The homepage is collected separately by the caller, so homepage URLs inside a
    sitemap are not duplicated here. Within the remaining URLs, priority is:
    conversion pages, trust pages, citation pages, one page per important
    template, technical entry pages, and risk-validation URLs last.
    """
    entries: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for index, page_url in enumerate(_dedupe_preserve_order(page_urls)):
        key = _canonical_sitemap_sample_key(page_url)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        score, category = _score_sitemap_page_url(page_url)
        if category == "homepage":
            continue
        entries.append({
            "url": page_url,
            "category": category,
            "score": score,
            "index": index,
            "template_key": _sitemap_template_key(page_url, category),
        })

    entries.sort(key=lambda item: (-item["score"], item["index"]))

    selected: list[dict[str, Any]] = []
    selected_urls: set[str] = set()

    def select_entry(entry: dict[str, Any]) -> None:
        selected.append(entry)
        selected_urls.add(entry["url"])

    for category in SITEMAP_SAMPLE_CATEGORY_ORDER:
        if len(selected) >= limit:
            break
        if category == "template":
            seen_templates: set[str] = set()
            for entry in entries:
                if len(selected) >= limit:
                    break
                template_key = entry["template_key"]
                if (
                    entry["category"] == category
                    and entry["url"] not in selected_urls
                    and template_key not in seen_templates
                ):
                    select_entry(entry)
                    seen_templates.add(template_key)
            continue
        for entry in entries:
            if entry["category"] == category and entry["url"] not in selected_urls:
                select_entry(entry)
                break

    for entry in entries:
        if len(selected) >= limit:
            break
        if entry["url"] not in selected_urls:
            select_entry(entry)

    return [
        {
            "url": item["url"],
            "category": item["category"],
            "score": item["score"],
            "template_key": item["template_key"],
        }
        for item in selected[:limit]
    ]


def _discover_sitemaps(
    session: requests.Session,
    base_url: str,
    robots_result: dict,
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict:
    """Find sitemap URLs from robots.txt and common paths, then follow sitemap indexes."""
    robots_rules = _parse_robots_rules(robots_result.get("text", ""))
    declared_candidates = _dedupe_preserve_order(
        [urljoin(base_url, value) for value in robots_rules["sitemap_urls"]]
    )
    fallback_candidates = _dedupe_preserve_order(
        [urljoin(base_url, path) for path in SITEMAP_CANDIDATE_PATHS]
    )
    queue = list(declared_candidates or fallback_candidates)
    queued = set(queue)
    fallback_pending = [url for url in fallback_candidates if url not in queued]
    fetched: list[dict[str, Any]] = []
    page_urls: list[str] = []
    lastmods: list[str] = []
    has_hreflang = False
    first_status = 0
    first_ok_status = 0
    use_provided_session = not isinstance(session, requests.Session)
    has_successful_sitemap = False

    while queue and len(fetched) < MAX_SITEMAP_FETCHES:
        remaining = MAX_SITEMAP_FETCHES - len(fetched)
        batch_size = min(_bounded_workers(concurrency), remaining, len(queue))
        batch_urls = [queue.pop(0) for _ in range(batch_size)]
        if use_provided_session:
            batch_results = {
                sitemap_url: _get(session, sitemap_url)
                for sitemap_url in batch_urls
            }
        else:
            batch_results = _parallel_fetch(
                [(sitemap_url, sitemap_url, DEFAULT_UA) for sitemap_url in batch_urls],
                concurrency=concurrency,
            )

        for sitemap_url in batch_urls:
            result = batch_results.get(sitemap_url, {})
            if not first_status:
                first_status = result.get("status", 0)

            entry: dict[str, Any] = {
                "url": sitemap_url,
                "status": result.get("status", 0),
                "ok": result.get("ok", False),
                "root_tag": "",
                "page_url_count": 0,
                "child_sitemap_count": 0,
            }

            if result.get("ok"):
                parsed = _parse_sitemap_xml(result.get("text", ""), sitemap_url)
                if parsed["page_urls"] or parsed["child_sitemaps"]:
                    has_successful_sitemap = True
                    if not first_ok_status:
                        first_ok_status = result.get("status", 0)
                    entry["root_tag"] = parsed["root_tag"]
                    entry["page_url_count"] = len(parsed["page_urls"])
                    entry["child_sitemap_count"] = len(parsed["child_sitemaps"])
                    page_urls.extend(parsed["page_urls"])
                    lastmods.extend(parsed["lastmods"])
                    has_hreflang = has_hreflang or parsed["has_hreflang"]

                    for child_url in parsed["child_sitemaps"]:
                        if child_url not in queued:
                            queued.add(child_url)
                            queue.append(child_url)

            fetched.append(entry)

        if not queue and fallback_pending and not has_successful_sitemap:
            queue = list(fallback_pending)
            queued.update(queue)
            fallback_pending = []

    page_urls = _dedupe_preserve_order(page_urls)[:MAX_SITEMAP_PAGE_URLS]
    successful = [
        item for item in fetched
        if item["ok"] and (item["page_url_count"] or item["child_sitemap_count"])
    ]

    return {
        "exists": bool(successful),
        "status_code": first_ok_status or first_status,
        "url_count": len(page_urls),
        "latest_lastmod": max(lastmods) if lastmods else "",
        "has_hreflang": has_hreflang,
        "robots_declares_sitemap": len(robots_rules["sitemap_urls"]) > 0,
        "sitemap_urls": [item["url"] for item in successful],
        "candidate_urls": fetched,
        "child_sitemap_count": sum(item["child_sitemap_count"] for item in fetched),
        "page_urls": page_urls,
    }


def _extract_sitemap_urls(sitemap_text: str, limit: int = MAX_SUBPAGES) -> list[str]:
    if not sitemap_text:
        return []
    return _parse_sitemap_xml(sitemap_text, "")["page_urls"][:limit]


def _parse_robots_rules(robots_text: str) -> dict:
    """Parse robots.txt into structured rules."""
    rules: dict[str, list[str]] = {}  # ua -> disallow paths
    sitemap_urls: list[str] = []
    current_ua = "*"

    for line in robots_text.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            current_ua = value
            if current_ua not in rules:
                rules[current_ua] = []
        elif key == "disallow" and value:
            rules.setdefault(current_ua, []).append(value)
        elif key == "sitemap":
            sitemap_urls.append(value)

    return {"rules": rules, "sitemap_urls": sitemap_urls}


def _robots_rule_blocks_root(rule: str) -> bool:
    """Return true only when a Disallow rule blocks the homepage/root URL."""
    rule = (rule or "").split("#", 1)[0].strip()
    if not rule:
        return False
    return rule in {"/", "/*", "/$", "/*$"}


def _robots_effective_disallows(robots_rules: dict, user_agent: str) -> list[str]:
    """Return UA-specific disallows, falling back to wildcard rules."""
    rules = robots_rules.get("rules", {})
    return rules.get(user_agent) or rules.get(user_agent.lower()) or rules.get("*", [])


# ============================================================================
# Signal Collection — D1: Technical Accessibility
# ============================================================================

def _collect_d1(session: requests.Session, url: str, homepage_result: dict,
                homepage_info: dict, robots_result: dict, sitemap_info: dict,
                llms_result: dict, llms_full_result: dict,
                notfound_result: dict, ua_probes: dict, sub_pages: list[dict],
                render_method: str) -> tuple[dict, dict]:
    """Collect D1 Technical Accessibility signals and snippets."""
    signals: dict[str, Any] = {}
    snippets: dict[str, str] = {}

    signals["d1_access_blocker"] = _detect_access_blocker(
        homepage_result,
        robots_result,
        llms_result,
        notfound_result,
        *ua_probes.values(),
    )

    parsed_requested = urlparse(url)
    parsed_final = urlparse(homepage_result.get("final_url") or url)
    homepage_status = homepage_result.get("status", 0)
    homepage_text = homepage_result.get("text", "")
    homepage_headers = {k.lower(): str(v) for k, v in homepage_result.get("headers", {}).items()}
    internal_links = homepage_info.get("internal_links", [])
    sitemap_page_urls = sitemap_info.get("page_urls", [])

    signals["d1_entry_normalization"] = {
        "requested_url": url,
        "final_url": homepage_result.get("final_url", ""),
        "requested_scheme": parsed_requested.scheme,
        "final_scheme": parsed_final.scheme,
        "requested_host": parsed_requested.netloc,
        "final_host": parsed_final.netloc,
        "uses_https": parsed_final.scheme == "https",
        "host_changed": parsed_requested.netloc.lower() != parsed_final.netloc.lower(),
        "canonical": homepage_info.get("canonical", ""),
    }

    signals["d1_homepage_access"] = {
        "status_code": homepage_status,
        "ok": homepage_result.get("ok", False),
        "word_count": homepage_info.get("word_count", 0),
        "content_type": homepage_headers.get("content-type", ""),
        "final_url": homepage_result.get("final_url", ""),
        "access_blocker_detected": signals["d1_access_blocker"].get("detected", False),
        "access_blocker_evidence": signals["d1_access_blocker"].get("evidence", []),
    }

    # D1.1 robots.txt
    robots_rules = _parse_robots_rules(robots_result.get("text", ""))
    wildcard_disallows = robots_rules["rules"].get("*", [])
    signals["d1_robots"] = {
        "status_code": robots_result.get("status", 0),
        "disallow_paths": wildcard_disallows[:20],
        "blocks_root": any(_robots_rule_blocks_root(rule) for rule in wildcard_disallows),
        "total_rules": sum(len(v) for v in robots_rules["rules"].values()),
    }

    # D1.2 AI Crawler Access
    crawler_results = {}
    blocker_provider = signals["d1_access_blocker"].get("provider", "")
    waf_is_blocking_bots = signals["d1_access_blocker"].get("detected", False) and bool(blocker_provider)
    # Also check robots.txt for per-UA blocks
    for name in CRAWLER_UAS:
        status = ua_probes.get(name, {}).get("status", 0)
        # Check if robots.txt explicitly blocks this UA
        ua_rules = _robots_effective_disallows(robots_rules, name)
        robots_blocked = any(_robots_rule_blocks_root(rule) for rule in ua_rules)
        # 区分 WAF 安全挑战拦截与 robots.txt 策略拦截
        waf_blocked = (
            not robots_blocked
            and status not in range(200, 400)
            and waf_is_blocking_bots
        )
        crawler_results[name] = {
            "status": status,
            "robots_blocked": robots_blocked,
            "waf_blocked": waf_blocked,
            "accessible": status in range(200, 400) and not robots_blocked,
        }

    accessible_count = sum(1 for v in crawler_results.values() if v["accessible"])
    blocked_count = sum(1 for v in crawler_results.values() if not v["accessible"])
    waf_blocked_count = sum(1 for v in crawler_results.values() if v["waf_blocked"])
    # 当所有探测结果均被 WAF 拦截时，AI 爬虫可达性实质上不可检测
    all_waf_blocked = waf_blocked_count > 0 and accessible_count == 0

    signals["d1_ai_crawlers"] = {
        "results": crawler_results,
        "accessible_count": accessible_count,
        "blocked_count": blocked_count,
        "waf_blocked_count": waf_blocked_count,
        "waf_provider": blocker_provider if waf_blocked_count > 0 else "",
        "all_waf_blocked": all_waf_blocked,
        "note": (
            f"该项无法检测：站点启用了 {blocker_provider} 安全防护，"
            f"Bot UA 探测请求被拦截，无法判断 AI 爬虫的真实可达性。"
        ) if all_waf_blocked else "",
    }

    # D1.3 Sitemap
    signals["d1_sitemap"] = {
        "exists": sitemap_info.get("exists", False),
        "status_code": sitemap_info.get("status_code", 0),
        "url_count": sitemap_info.get("url_count", 0),
        "latest_lastmod": sitemap_info.get("latest_lastmod", ""),
        "has_hreflang": sitemap_info.get("has_hreflang", False),
        "robots_declares_sitemap": sitemap_info.get("robots_declares_sitemap", False),
        "sitemap_urls": sitemap_info.get("sitemap_urls", [])[:10],
        "child_sitemap_count": sitemap_info.get("child_sitemap_count", 0),
        "sample_source": sitemap_info.get("sample_source", "none"),
        "homepage_candidate_url_count": sitemap_info.get("homepage_candidate_url_count", 0),
        "sampled_page_urls": sitemap_info.get("sampled_page_urls", []),
        "sampled_page_categories": sitemap_info.get("sampled_page_categories", []),
    }

    # D1.4 Status Codes & Error Handling
    sub_statuses = [p.get("status", 0) for p in sub_pages]
    notfound_status = notfound_result.get("status", 0)
    notfound_text = notfound_result.get("text", "")
    notfound_has_noindex = "noindex" in notfound_text.lower() if notfound_text else False

    # Check for soft-404 (404 probe returning 200)
    soft_404 = notfound_status == 200

    signals["d1_status_codes"] = {
        "homepage_status": homepage_result.get("status", 0),
        "homepage_final_url": homepage_result.get("final_url", ""),
        "sub_page_statuses": sub_statuses,
        "sub_page_errors": sum(1 for s in sub_statuses if s >= 400 or s == 0),
        "notfound_status": notfound_status,
        "notfound_has_noindex": notfound_has_noindex,
        "soft_404": soft_404,
    }

    # D1.5 Rendering Readability
    signals["d1_rendering"] = {
        "word_count": homepage_info.get("word_count", 0),
        "render_method": render_method,
        "is_spa_shell": render_method != "static",
    }

    # D1.6 llms.txt
    llms_text = llms_result.get("text", "") if llms_result.get("ok") else ""
    llms_full_text = llms_full_result.get("text", "") if llms_full_result.get("ok") else ""
    llms_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", llms_text)
    llms_has_title = llms_text.startswith("#") or "\n#" in llms_text
    llms_has_intro = ">" in llms_text[:500]
    llms_sections = len(re.findall(r"^##\s", llms_text, re.MULTILINE))

    signals["d1_llms_txt"] = {
        "exists": llms_result.get("ok", False),
        "full_exists": llms_full_result.get("ok", False),
        "status_code": llms_result.get("status", 0),
        "has_title": llms_has_title,
        "has_intro": llms_has_intro,
        "link_count": len(llms_links),
        "section_count": llms_sections,
        "char_count": len(llms_text),
    }
    if llms_text:
        snippets["d1_llms_txt_content"] = llms_text[:SNIPPET_MAX_LEN]

    # D1.7 Analytics & CDN
    html_lower = homepage_result.get("text", "").lower()
    has_ga4 = bool(re.search(r"g-[a-z0-9]{6,}", html_lower))
    has_gtm = "gtm-" in html_lower or "googletagmanager" in html_lower
    has_gtag = "gtag(" in html_lower or "gtag.js" in html_lower

    cdn_signals = {}
    for key in ["server", "cf-ray", "x-served-by", "via", "x-cdn"]:
        if key in homepage_headers:
            cdn_signals[key] = homepage_headers[key]
    is_cloudflare = "cloudflare" in homepage_headers.get("server", "").lower() or "cf-ray" in homepage_headers

    signals["d1_analytics"] = {
        "has_ga4": has_ga4,
        "has_gtm": has_gtm,
        "has_gtag": has_gtag,
        "cdn_signals": cdn_signals,
        "is_cloudflare": is_cloudflare,
    }

    coverage_targets = {
        "pricing": ("pricing", "price", "plans", "费用", "价格"),
        "product_service": ("product", "service", "feature", "solution", "course", "产品", "服务", "课程"),
        "blog_resources": ("blog", "resource", "learn", "guide", "academy", "博客", "资源", "指南"),
        "docs_help": ("docs", "documentation", "help", "support", "faq", "帮助", "文档"),
        "about_contact": ("about", "contact", "company", "team", "关于", "联系"),
        "legal": ("privacy", "terms", "legal", "policy", "compliance", "隐私", "条款", "合规"),
    }
    searchable_links = " ".join(internal_links + sitemap_page_urls).lower()
    coverage = {
        name: any(token in searchable_links for token in tokens)
        for name, tokens in coverage_targets.items()
    }
    high_value_categories = {
        entry.get("category")
        for entry in sitemap_info.get("sampled_page_categories", [])
        if entry.get("category")
    }

    signals["d1_core_entry_coverage"] = {
        "coverage": coverage,
        "covered_count": sum(1 for value in coverage.values() if value),
        "total_targets": len(coverage),
        "internal_link_count": len(internal_links),
        "sitemap_page_count": len(sitemap_page_urls),
    }
    signals["d1_crawl_set_coverage"] = {
        "sampled_page_count": len(sub_pages),
        "sampled_categories": sorted(high_value_categories),
        "has_homepage": True,
        "has_high_value_page": any(
            category in high_value_categories
            for category in ("conversion", "trust", "citation", "template")
        ),
    }
    signals["d1_waf_cdn_blocking"] = {
        "detected": signals["d1_access_blocker"].get("detected", False),
        "evidence": signals["d1_access_blocker"].get("evidence", []),
        "cdn_signals": cdn_signals,
        "status_code": homepage_status,
    }
    meta_robots = homepage_info.get("meta_robots", "")
    x_robots_tag = homepage_headers.get("x-robots-tag", "")
    canonical = homepage_info.get("canonical", "")
    canonical_host = urlparse(urljoin(url, canonical)).netloc if canonical else ""
    signals["d1_indexability"] = {
        "meta_robots": meta_robots,
        "x_robots_tag": x_robots_tag,
        "has_noindex": "noindex" in f"{meta_robots} {x_robots_tag}".lower(),
        "has_nofollow": "nofollow" in f"{meta_robots} {x_robots_tag}".lower(),
        "canonical": canonical,
        "canonical_host": canonical_host,
        "canonical_conflict": bool(canonical_host and canonical_host != parsed_final.netloc),
    }
    lower_notfound = notfound_text.lower()
    signals["d1_soft_404"] = {
        "probe_status": notfound_status,
        "soft_404": soft_404,
        "looks_like_error_page": any(token in lower_notfound for token in ("not found", "404", "page not found", "不存在")),
        "has_noindex": notfound_has_noindex,
    }
    homepage_signature = (
        homepage_info.get("title", ""),
        "|".join(homepage_info.get("h1", [])),
        homepage_info.get("canonical", ""),
    )
    fallback_examples = []
    for page in sub_pages:
        if page.get("status") == 200:
            info = _parse_html(page.get("text", ""), page.get("final_url", ""))
            signature = (
                info.get("title", ""),
                "|".join(info.get("h1", [])),
                info.get("canonical", ""),
            )
            if signature == homepage_signature:
                fallback_examples.append(page.get("final_url") or page.get("url"))
    signals["d1_homepage_fallback"] = {
        "fallback_count": len(fallback_examples),
        "fallback_examples": fallback_examples[:5],
    }
    signals["d1_404_index_conflict"] = {
        "notfound_status": notfound_status,
        "notfound_has_noindex": notfound_has_noindex,
        "conflict": notfound_status in (404, 410) and not notfound_has_noindex,
    }
    signals["d1_sitemap_pollution"] = {
        "sampled_errors": sum(1 for status in sub_statuses if status >= 400 or status == 0),
        "sampled_total": len(sub_statuses),
        "sitemap_url_count": sitemap_info.get("url_count", 0),
    }
    signals["d1_internal_discovery"] = {
        "internal_link_count": len(internal_links),
        "footer_nav_coverage_proxy": coverage,
        "covered_target_count": sum(1 for value in coverage.values() if value),
    }

    return signals, snippets


# ============================================================================
# Signal Collection — D2: Content Quality
# ============================================================================

def _collect_d2(homepage_info: dict, sub_page_infos: list[dict],
                homepage_result: dict) -> tuple[dict, dict]:
    """Collect D2 Content Quality signals and snippets."""
    signals: dict[str, Any] = {}
    snippets: dict[str, str] = {}

    all_infos = [homepage_info] + sub_page_infos
    word_counts = [p.get("word_count", 0) for p in all_infos]

    # D2.1 Professional Depth
    # Deep pages: >=800 words (English) or large CJK content
    deep_threshold = 800
    deep_pages = sum(1 for wc in word_counts if wc >= deep_threshold)
    deep_ratio = deep_pages / max(len(word_counts), 1)

    signals["d2_depth"] = {
        "pages_sampled": len(all_infos),
        "word_counts": word_counts,
        "deep_pages": deep_pages,
        "deep_ratio": round(deep_ratio, 2),
    }
    # Snippet: first 500 chars of the deepest page body for agent to judge quality
    deepest_idx = word_counts.index(max(word_counts)) if word_counts else 0
    if all_infos:
        snippets["d2_depth_sample"] = all_infos[deepest_idx].get("body_text", "")[:SNIPPET_MAX_LEN]

    # D2.2 Content Freshness
    all_dates = []
    for info in all_infos:
        all_dates.extend(info.get("time_elements", []))
        all_dates.extend(info.get("visible_dates", []))
    # Also check schema datePublished/dateModified
    for info in all_infos:
        for block in info.get("schema_blocks", []):
            for key in ("datePublished", "dateModified"):
                if key in block:
                    all_dates.append(str(block[key])[:10])

    # Parse and find most recent
    parsed_dates = []
    for d in all_dates:
        try:
            # Try ISO format
            parsed_dates.append(datetime.fromisoformat(d[:10]).date())
        except (ValueError, TypeError):
            pass

    latest_date = max(parsed_dates) if parsed_dates else None
    days_since_latest = (datetime.now(timezone.utc).date() - latest_date).days if latest_date else None
    pages_with_dates = sum(1 for info in all_infos
                           if info.get("time_elements") or info.get("visible_dates"))

    signals["d2_freshness"] = {
        "total_dates_found": len(all_dates),
        "pages_with_dates": pages_with_dates,
        "pages_sampled": len(all_infos),
        "latest_date": str(latest_date) if latest_date else None,
        "days_since_latest": days_since_latest,
    }

    # D2.3 Author/Team Attribution
    author_signals = []
    has_author_schema = False
    has_about_link = False

    for info in all_infos:
        for block in info.get("schema_blocks", []):
            if "author" in block:
                has_author_schema = True
                author_val = block["author"]
                if isinstance(author_val, dict):
                    author_signals.append(author_val.get("name", ""))
                elif isinstance(author_val, str):
                    author_signals.append(author_val)

    # Check for author/about page links
    all_links = []
    for info in all_infos:
        all_links.extend(info.get("internal_links", []))
    about_patterns = ["/about", "/team", "/author", "/我们", "/关于"]
    has_about_link = any(any(p in link.lower() for p in about_patterns) for link in all_links)

    # Text patterns for bylines
    body_combined = " ".join(info.get("body_text", "")[:200] for info in all_infos)
    byline_patterns = re.findall(
        r"(?:by|作者|编辑|reviewed by|written by)\s*[:：]?\s*([A-Z\u4e00-\u9fff][\w\s\u4e00-\u9fff]{1,30})",
        body_combined, re.IGNORECASE
    )

    signals["d2_author"] = {
        "has_author_schema": has_author_schema,
        "schema_authors": list(set(author_signals))[:5],
        "has_about_link": has_about_link,
        "byline_matches": byline_patterns[:5],
    }
    if author_signals or byline_patterns:
        snippets["d2_author_context"] = "; ".join(
            (author_signals + byline_patterns)[:5]
        )[:SNIPPET_MAX_LEN]

    # D2.4 Sources & Citations
    all_external = []
    for info in all_infos:
        all_external.extend(info.get("external_links", []))
    ext_domains = list(set(urlparse(u).netloc for u in all_external if urlparse(u).netloc))
    authority_hits = [d for d in ext_domains
                     if any(a in d for a in AUTHORITY_SOURCES)]

    signals["d2_citations"] = {
        "total_external_links": len(all_external),
        "unique_domains": len(ext_domains),
        "authority_domains": authority_hits[:10],
        "avg_per_page": round(len(all_external) / max(len(all_infos), 1), 1),
    }

    # D2.5 Real Experience Signals
    exp_hits: dict[str, int] = {}
    exp_context_snippets: list[str] = []
    combined_text = " ".join(info.get("body_text", "") for info in all_infos).lower()

    for kw in EXPERIENCE_KEYWORDS:
        count = combined_text.count(kw.lower())
        if count > 0:
            exp_hits[kw] = count
            # Grab context around first occurrence
            idx = combined_text.find(kw.lower())
            start = max(0, idx - 50)
            end = min(len(combined_text), idx + len(kw) + 100)
            exp_context_snippets.append(combined_text[start:end])

    # Video embeds
    has_video = any("youtube" in info.get("body_text", "").lower() or
                    "vimeo" in info.get("body_text", "").lower() or
                    "bilibili" in info.get("body_text", "").lower()
                    for info in all_infos)

    signals["d2_experience"] = {
        "keyword_hits": exp_hits,
        "hit_types": len(exp_hits),
        "has_video_embed": has_video,
    }
    if exp_context_snippets:
        snippets["d2_experience_context"] = "\n---\n".join(
            exp_context_snippets[:3]
        )[:SNIPPET_MAX_LEN]

    # D2.6 Facts & Data
    # Count numeric tokens, percentages, currency
    num_tokens = len(re.findall(r"\b\d+[.,]?\d*%?\b", combined_text))
    year_refs = len(re.findall(r"\b20[12]\d\b", combined_text))

    signals["d2_data"] = {
        "numeric_tokens": min(num_tokens, 999),
        "year_references": year_refs,
        "authority_source_mentions": len(authority_hits),
    }
    if num_tokens > 0:
        # Sample a snippet with data context
        data_match = re.search(r"[^.]*\d+[.,]?\d*%[^.]*\.", combined_text)
        if data_match:
            snippets["d2_data_sample"] = data_match.group(0)[:SNIPPET_MAX_LEN]

    # D2.7 Content Completeness
    short_threshold = 200
    short_pages = sum(1 for wc in word_counts if wc < short_threshold)
    short_ratio = short_pages / max(len(word_counts), 1)

    signals["d2_completeness"] = {
        "pages_sampled": len(word_counts),
        "short_pages": short_pages,
        "short_ratio": round(short_ratio, 2),
        "word_counts": word_counts,
    }

    # D2.8 Summaries & Key Takeaways
    summary_kws = ["tl;dr", "key takeaways", "summary", "摘要", "要点",
                   "核心结论", "highlights", "in brief", "总结"]
    summary_hits = 0
    summary_context = []
    for info in all_infos:
        page_text = info.get("body_text", "").lower()
        headings = " ".join(info.get("h2", []) + info.get("h3", [])).lower()
        if any(kw in page_text or kw in headings for kw in summary_kws):
            summary_hits += 1
            # Find the actual summary section
            for kw in summary_kws:
                idx = page_text.find(kw)
                if idx >= 0:
                    summary_context.append(page_text[idx:idx + 200])
                    break

    signals["d2_summaries"] = {
        "pages_with_summary": summary_hits,
        "pages_sampled": len(all_infos),
        "coverage_ratio": round(summary_hits / max(len(all_infos), 1), 2),
    }
    if summary_context:
        snippets["d2_summary_sample"] = "\n---\n".join(summary_context[:3])[:SNIPPET_MAX_LEN]

    # New 5-dimension score-table support signals.
    all_h1 = [h for info in all_infos for h in info.get("h1", [])]
    all_h2_h6 = [
        h
        for info in all_infos
        for key in ("h2", "h3", "h4", "h5", "h6")
        for h in info.get(key, [])
    ]
    schema_types_all = [schema_type for info in all_infos for schema_type in info.get("schema_types", [])]
    og_complete = sum(1 for info in all_infos if {"og:title", "og:description"}.issubset(set(info.get("og_tags", {}).keys())))
    twitter_complete = sum(1 for info in all_infos if info.get("twitter_tags"))
    image_count = sum(info.get("image_count", 0) for info in all_infos)
    images_missing_alt = sum(info.get("images_missing_alt", 0) for info in all_infos)
    images_weak_alt = sum(info.get("images_weak_alt", 0) for info in all_infos)
    combined_links = " ".join(link.lower() for info in all_infos for link in info.get("internal_links", []))
    information_architecture_targets = {
        "product": ("product", "feature", "solution", "course", "service", "产品", "服务", "课程"),
        "pricing": ("pricing", "price", "plans", "费用", "价格"),
        "blog_resources": ("blog", "resource", "learn", "guide", "academy", "博客", "资源", "指南"),
        "docs_help": ("docs", "documentation", "help", "support", "faq", "帮助", "文档"),
        "about_contact": ("about", "contact", "company", "team", "关于", "联系"),
        "legal": ("privacy", "terms", "legal", "policy", "隐私", "条款"),
    }
    architecture_coverage = {
        key: any(token in combined_links for token in tokens)
        for key, tokens in information_architecture_targets.items()
    }

    signals["d2_heading_structure"] = {
        "h1_count_total": len(all_h1),
        "pages_with_one_h1": sum(1 for info in all_infos if len(info.get("h1", [])) == 1),
        "h2_h6_count_total": len(all_h2_h6),
        "heading_samples": all_h2_h6[:20],
    }
    signals["d2_information_architecture"] = {
        "coverage": architecture_coverage,
        "covered_count": sum(1 for value in architecture_coverage.values() if value),
        "total_targets": len(architecture_coverage),
    }
    signals["d2_schema_coverage"] = {
        "schema_types": sorted(set(schema_types_all)),
        "schema_type_count": len(set(schema_types_all)),
        "has_organization": "Organization" in schema_types_all,
        "has_website": "WebSite" in schema_types_all,
        "has_breadcrumb": "BreadcrumbList" in schema_types_all,
        "has_article_like": any(t in schema_types_all for t in ("Article", "BlogPosting", "NewsArticle", "TechArticle")),
        "has_faq": "FAQPage" in schema_types_all,
    }
    signals["d2_social_metadata"] = {
        "pages_with_og_title_description": og_complete,
        "pages_with_twitter_tags": twitter_complete,
        "pages_sampled": len(all_infos),
        "image_count": image_count,
        "images_missing_alt": images_missing_alt,
        "images_weak_alt": images_weak_alt,
    }
    signals["d2_lang"] = {
        "html_lang": homepage_info.get("html_lang", ""),
        "hreflang_count": homepage_info.get("hreflang_count", 0),
    }

    return signals, snippets


# ============================================================================
# Signal Collection — D3: Brand Entity
# ============================================================================

def _collect_d3(homepage_info: dict, homepage_result: dict,
                llms_result: dict, sub_page_infos: list[dict],
                wikipedia_result: dict, wikidata_result: dict,
                domain: str) -> tuple[dict, dict]:
    """Collect D3 Brand Entity signals and snippets."""
    signals: dict[str, Any] = {}
    snippets: dict[str, str] = {}

    schema_blocks = homepage_info.get("schema_blocks", [])
    schema_types = homepage_info.get("schema_types", [])

    # D3.1 Brand Name Consistency
    # Sources: Organization schema name, <title> brand segment, llms.txt title
    org_name = ""
    for block in schema_blocks:
        if block.get("@type") in ("Organization", "Corporation", "LocalBusiness"):
            org_name = block.get("name", "")
            break

    title = homepage_info.get("title", "")
    title_brand = title.split("|")[0].split(" - ")[0].split(" — ")[0].strip() if title else ""

    llms_text = llms_result.get("text", "") if llms_result.get("ok") else ""
    llms_title = ""
    if llms_text:
        first_line = llms_text.strip().split("\n")[0]
        if first_line.startswith("#"):
            llms_title = first_line.lstrip("#").strip()

    signals["d3_brand_name"] = {
        "schema_org_name": org_name,
        "title_brand": title_brand,
        "llms_title": llms_title,
        "domain_root": domain.replace("www.", "").split(".")[0],
    }
    snippets["d3_brand_name_sources"] = (
        f"Schema Organization name: {org_name}\n"
        f"Title brand segment: {title_brand}\n"
        f"llms.txt title: {llms_title}\n"
        f"Domain: {domain}"
    )

    # D3.2 Brand Description
    description = homepage_info.get("description", "")
    h1_text = " | ".join(homepage_info.get("h1", []))
    llms_intro = ""
    if llms_text:
        # Extract blockquote (>) intro
        intro_lines = [l[1:].strip() for l in llms_text.split("\n") if l.startswith(">")]
        llms_intro = " ".join(intro_lines)

    signals["d3_brand_description"] = {
        "meta_description_length": len(description),
        "has_h1": bool(h1_text),
        "llms_intro_length": len(llms_intro),
    }
    snippets["d3_brand_description_content"] = (
        f"Meta description: {description}\n"
        f"H1: {h1_text}\n"
        f"llms.txt intro: {llms_intro[:200]}"
    )[:SNIPPET_MAX_LEN]

    # D3.3 Trust Entry Points
    all_links = homepage_info.get("internal_links", [])
    links_lower = [l.lower() for l in all_links]
    body_lower = homepage_info.get("body_text", "").lower()

    trust_found = []
    for path in TRUST_PATHS_EN:
        if any(path in l for l in links_lower):
            trust_found.append(path)
    for path in TRUST_PATHS_ZH:
        if path in body_lower:
            trust_found.append(path)
    trust_found = list(set(trust_found))

    signals["d3_trust_entries"] = {
        "found": trust_found,
        "count": len(trust_found),
        "missing": [p for p in TRUST_PATHS_EN if p not in trust_found],
    }

    # D3.4 Third-Party Platforms
    platform_patterns = {
        "App Store": ["apps.apple.com", "itunes.apple.com"],
        "Google Play": ["play.google.com"],
        "LinkedIn": ["linkedin.com"],
        "YouTube": ["youtube.com", "youtu.be"],
        "Twitter/X": ["twitter.com", "x.com"],
        "Facebook": ["facebook.com"],
        "Instagram": ["instagram.com"],
        "Reddit": ["reddit.com"],
        "GitHub": ["github.com"],
        "Trustpilot": ["trustpilot.com"],
        "G2": ["g2.com"],
    }
    ext_links = homepage_info.get("external_links", [])
    found_platforms = []
    for name, patterns in platform_patterns.items():
        if any(any(p in link for p in patterns) for link in ext_links):
            found_platforms.append(name)

    # Also check schema sameAs
    same_as_links = []
    for block in schema_blocks:
        sa = block.get("sameAs", [])
        if isinstance(sa, str):
            sa = [sa]
        same_as_links.extend(sa)

    signals["d3_third_party"] = {
        "platforms_found": found_platforms,
        "platform_count": len(found_platforms),
        "same_as_count": len(same_as_links),
        "same_as_links": same_as_links[:10],
    }

    # D3.5 Knowledge Graph Presence
    wiki_data = {}
    if wikipedia_result.get("ok") and wikipedia_result.get("text"):
        try:
            wiki_json = json.loads(wikipedia_result["text"])
            search_results = wiki_json.get("query", {}).get("search", [])
            wiki_data = {
                "total_hits": wiki_json.get("query", {}).get("searchinfo", {}).get("totalhits", 0),
                "results": [{"title": r.get("title", ""), "snippet": r.get("snippet", "")}
                            for r in search_results[:3]],
            }
        except (json.JSONDecodeError, KeyError):
            pass

    wikidata_data = {}
    if wikidata_result.get("ok") and wikidata_result.get("text"):
        try:
            wd_json = json.loads(wikidata_result["text"])
            entities = wd_json.get("search", [])
            wikidata_data = {
                "entity_count": len(entities),
                "entities": [{"id": e.get("id", ""), "label": e.get("label", ""),
                              "description": e.get("description", "")}
                             for e in entities[:3]],
            }
        except (json.JSONDecodeError, KeyError):
            pass

    # Check if sameAs includes wikipedia/wikidata
    has_wiki_sameas = any("wikipedia" in l or "wikidata" in l for l in same_as_links)

    signals["d3_knowledge_graph"] = {
        "wikipedia": wiki_data,
        "wikidata": wikidata_data,
        "has_wiki_sameas": has_wiki_sameas,
    }
    if wiki_data.get("results"):
        snippets["d3_knowledge_graph_results"] = json.dumps(
            wiki_data["results"][:2], ensure_ascii=False
        )[:SNIPPET_MAX_LEN]

    # D3.6 Technical Trust Assets
    tech_patterns = ["github.com", "developer.", "api docs", "openapi", "swagger",
                     "sdk", "npm", "pypi", "/developers", "/api", "/docs"]
    tech_found = []
    all_page_links = ext_links + homepage_info.get("internal_links", [])
    for pattern in tech_patterns:
        if any(pattern in l.lower() for l in all_page_links):
            tech_found.append(pattern)
    # Also check body text
    body = homepage_info.get("body_text", "").lower()
    for pattern in tech_patterns:
        if pattern in body and pattern not in tech_found:
            tech_found.append(pattern)

    signals["d3_tech_assets"] = {
        "found": list(set(tech_found)),
        "count": len(set(tech_found)),
    }

    # D3.7 Organization + WebSite Schema
    has_org = any(t in ("Organization", "Corporation", "LocalBusiness") for t in schema_types)
    has_website = "WebSite" in schema_types

    org_fields = {}
    for block in schema_blocks:
        if block.get("@type") in ("Organization", "Corporation", "LocalBusiness"):
            for f in ("url", "name", "logo", "sameAs", "description", "contactPoint"):
                if f in block:
                    org_fields[f] = True
            break

    signals["d3_schema_org"] = {
        "has_organization": has_org,
        "has_website": has_website,
        "org_fields": list(org_fields.keys()),
        "org_field_count": len(org_fields),
    }

    # D3.8 Brand Search Presence
    signals["d3_brand_search"] = {
        "wikipedia_hits": wiki_data.get("total_hits", 0),
        "wikidata_entities": wikidata_data.get("entity_count", 0),
        "same_as_count": len(same_as_links),
        "same_as_domains": list(set(urlparse(l).netloc for l in same_as_links if urlparse(l).netloc))[:10],
    }
    if same_as_links:
        snippets["d3_brand_search_sameas"] = "\n".join(same_as_links[:10])[:SNIPPET_MAX_LEN]

    return signals, snippets


# ============================================================================
# Signal Collection — D4: AI Citability
# ============================================================================

def _collect_d4(homepage_info: dict, sub_page_infos: list[dict],
                llms_result: dict, homepage_result: dict) -> tuple[dict, dict]:
    """Collect D4 AI Citability signals and snippets."""
    signals: dict[str, Any] = {}
    snippets: dict[str, str] = {}

    all_infos = [homepage_info] + sub_page_infos
    schema_types_all = []
    for info in all_infos:
        schema_types_all.extend(info.get("schema_types", []))

    # D4.1 Definition Content
    description = homepage_info.get("description", "")
    h1 = " | ".join(homepage_info.get("h1", []))
    llms_text = llms_result.get("text", "") if llms_result.get("ok") else ""
    llms_intro = ""
    if llms_text:
        intro_lines = [l[1:].strip() for l in llms_text.split("\n") if l.startswith(">")]
        llms_intro = " ".join(intro_lines)

    # Count definition patterns
    body_combined = " ".join(info.get("body_text", "") for info in all_infos)
    def_patterns = re.findall(
        r"(?:is a|是|refers to|即|指的是|定义为|means|represents)",
        body_combined, re.IGNORECASE
    )

    signals["d4_definition"] = {
        "description_length": len(description),
        "has_h1": bool(h1),
        "has_llms_intro": bool(llms_intro),
        "definition_pattern_count": len(def_patterns),
    }
    snippets["d4_definition_content"] = (
        f"Description: {description}\n"
        f"H1: {h1}\n"
        f"llms.txt intro: {llms_intro[:200]}"
    )[:SNIPPET_MAX_LEN]

    # D4.2 Direct Answer Paragraphs
    ideal_paragraphs = []
    for info in all_infos:
        for p in info.get("paragraphs", []):
            word_count = len(p.split())
            # Ideal range: 80-200 words for EN, or 160-400 chars for CJK-heavy
            if 60 <= word_count <= 250:
                ideal_paragraphs.append(p)

    signals["d4_direct_answers"] = {
        "ideal_paragraph_count": len(ideal_paragraphs),
        "total_paragraphs": sum(len(info.get("paragraphs", [])) for info in all_infos),
    }
    if ideal_paragraphs:
        # Sample up to 3 ideal paragraphs for agent to judge
        snippets["d4_answer_paragraphs"] = "\n---\n".join(
            ideal_paragraphs[:3]
        )[:SNIPPET_MAX_LEN]

    # D4.3 FAQ Coverage
    faq_pages = sum(1 for info in all_infos if info.get("has_faq_visible"))
    has_faq_schema = "FAQPage" in schema_types_all

    # Count question patterns
    question_patterns = re.findall(
        r"(?:什么是|如何|怎么|为什么|why|how to|what is|how do|can i|does)",
        body_combined.lower()
    )
    # Count actual Q&A pairs in FAQ sections
    faq_questions = re.findall(
        r"(?:<h[2-4][^>]*>|^\s*[-•*]\s*|^\s*\d+\.\s*)(.*?\?)",
        body_combined, re.MULTILINE
    )

    signals["d4_faq"] = {
        "has_visible_faq": faq_pages > 0,
        "has_faq_schema": has_faq_schema,
        "question_pattern_count": len(question_patterns),
        "faq_question_count": len(faq_questions),
    }
    # Snippet: FAQ content for agent to judge quality
    for info in all_infos:
        if info.get("has_faq_visible"):
            body = info.get("body_text", "")
            # Find FAQ section
            faq_idx = -1
            for kw in ["faq", "常见问题", "frequently asked"]:
                idx = body.lower().find(kw)
                if idx >= 0:
                    faq_idx = idx
                    break
            if faq_idx >= 0:
                snippets["d4_faq_content"] = body[faq_idx:faq_idx + SNIPPET_MAX_LEN]
                break

    # D4.4 How-It-Works / Process
    process_kws = ["how it works", "工作原理", "如何使用", "step 1", "step 2",
                   "快速开始", "操作步骤", "getting started", "how to use"]
    process_hits = []
    headings_combined = " ".join(
        " ".join(info.get("h2", []) + info.get("h3", [])) for info in all_infos
    ).lower()

    for kw in process_kws:
        if kw in body_combined.lower() or kw in headings_combined:
            process_hits.append(kw)

    # Check for ordered lists as process indicators
    total_ol = sum(info.get("ol_count", 0) for info in all_infos)

    signals["d4_process"] = {
        "keyword_hits": process_hits,
        "has_ordered_lists": total_ol > 0,
        "ol_count": total_ol,
    }
    if process_hits:
        # Find context around first process keyword
        for kw in process_hits:
            idx = body_combined.lower().find(kw)
            if idx >= 0:
                snippets["d4_process_content"] = body_combined[idx:idx + SNIPPET_MAX_LEN]
                break

    # D4.5 Comparison Content
    compare_kws = [" vs ", "对比", "compare", "alternatives", "区别",
                   "difference", "better than", "选择", "versus"]
    compare_hits = []
    for kw in compare_kws:
        if kw in body_combined.lower():
            compare_hits.append(kw)

    # Check for comparison tables
    # (approximation: check headings for comparison keywords)
    compare_in_headings = any(
        any(kw in h.lower() for kw in compare_kws)
        for info in all_infos
        for h in info.get("h2", []) + info.get("h3", [])
    )

    signals["d4_comparison"] = {
        "keyword_hits": compare_hits,
        "in_headings": compare_in_headings,
    }
    if compare_hits:
        for kw in compare_hits:
            idx = body_combined.lower().find(kw)
            if idx >= 0:
                start = max(0, idx - 50)
                snippets["d4_comparison_content"] = body_combined[start:start + SNIPPET_MAX_LEN]
                break

    # D4.6 Lists & Step-by-Step Guides
    total_ol = sum(info.get("ol_count", 0) for info in all_infos)
    total_ul = sum(info.get("ul_count", 0) for info in all_infos)
    total_li = sum(info.get("li_count", 0) for info in all_infos)
    avg_li = total_li / max(len(all_infos), 1)

    signals["d4_lists"] = {
        "ol_count": total_ol,
        "ul_count": total_ul,
        "li_count": total_li,
        "avg_li_per_page": round(avg_li, 1),
    }

    # D4.7 AI Answer Page Assets
    all_links_text = " ".join(
        " ".join(info.get("internal_links", [])) for info in all_infos
    ).lower()
    all_headings_text = " ".join(
        " ".join(info.get("h1", []) + info.get("h2", []) + info.get("h3", []))
        for info in all_infos
    ).lower()
    search_text = all_links_text + " " + all_headings_text + " " + llms_text.lower()

    found_assets = []
    for asset_type, keywords in ASSET_KEYWORDS.items():
        if any(kw in search_text for kw in keywords):
            found_assets.append(asset_type)

    signals["d4_page_assets"] = {
        "found": found_assets,
        "count": len(found_assets),
        "total_types": len(ASSET_KEYWORDS),
    }

    # D4.8 Article Structured Data
    article_types = ["Article", "BlogPosting", "TechArticle", "NewsArticle"]
    has_article = any(t in schema_types_all for t in article_types)
    has_breadcrumb = "BreadcrumbList" in schema_types_all

    article_fields = []
    for info in all_infos:
        for block in info.get("schema_blocks", []):
            if block.get("@type") in article_types:
                for f in ("author", "datePublished", "headline", "image"):
                    if f in block:
                        article_fields.append(f)
                break

    signals["d4_article_schema"] = {
        "has_article_schema": has_article,
        "has_breadcrumb": has_breadcrumb,
        "article_fields": list(set(article_fields)),
    }

    return signals, snippets


# ============================================================================
# Signal Collection — D5: Recommendation
# ============================================================================

# Common URL path patterns for content asset detection
_BLOG_PATH_PATTERNS = ("/blog", "/articles", "/news", "/posts", "/insights", "/stories")
_RESOURCE_PATH_PATTERNS = ("/resources", "/guides", "/docs", "/help", "/learn", "/library", "/hub")
_PRICING_PATH_PATTERNS = ("/pricing", "/plans", "/subscribe", "/prices", "/buy")
_PRODUCT_PATH_PATTERNS = ("/product", "/features", "/solutions", "/services")
_CONVERSION_PATH_PATTERNS = ("/signup", "/register", "/demo", "/trial", "/download", "/booking", "/appointment", "/contact")
_EXTERNAL_PLATFORM_DOMAINS = {
    "youtube.com": "YouTube", "youtu.be": "YouTube",
    "linkedin.com": "LinkedIn",
    "github.com": "GitHub",
    "reddit.com": "Reddit",
    "twitter.com": "Twitter", "x.com": "Twitter",
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "producthunt.com": "ProductHunt",
    "trustpilot.com": "Trustpilot",
}


def _collect_d5(
    homepage_info: dict, sub_page_infos: list[dict],
    homepage_result: dict, sub_page_results: list[dict],
) -> tuple[dict, dict]:
    """Collect D5 Recommendation signals."""
    signals: dict[str, Any] = {}
    snippets: dict[str, str] = {}
    all_infos = [homepage_info] + sub_page_infos

    # Gather all URLs (from internal links + page URLs)
    all_urls: list[str] = []
    for info in all_infos:
        all_urls.extend(info.get("internal_links", []))
    for result in sub_page_results:
        if result.get("ok"):
            all_urls.append(result.get("final_url", result.get("url", "")))
    all_urls.append(homepage_result.get("final_url", ""))

    url_text = " ".join(all_urls).lower()

    # Content assets detection
    blog_detected = any(p in url_text for p in _BLOG_PATH_PATTERNS)
    resource_hub_detected = any(p in url_text for p in _RESOURCE_PATH_PATTERNS)
    pricing_detected = any(p in url_text for p in _PRICING_PATH_PATTERNS)
    product_detected = any(p in url_text for p in _PRODUCT_PATH_PATTERNS)

    # Conversion pages
    conversion_found: list[str] = []
    for pattern in _CONVERSION_PATH_PATTERNS:
        if pattern.lstrip("/") in url_text:
            conversion_found.append(pattern.lstrip("/"))

    # External platform links
    external_platforms: dict[str, bool] = {}
    for info in all_infos:
        for link in info.get("external_links", []):
            for domain, name in _EXTERNAL_PLATFORM_DOMAINS.items():
                if domain in link.lower():
                    external_platforms[name] = True

    signals["d5_content_assets"] = {
        "blog_detected": blog_detected,
        "resource_hub_detected": resource_hub_detected,
        "pricing_detected": pricing_detected,
        "product_detected": product_detected,
        "conversion_pages": sorted(set(conversion_found)),
        "conversion_count": len(set(conversion_found)),
        "external_platforms": sorted(external_platforms.keys()),
        "external_platform_count": len(external_platforms),
    }

    # Homepage CTA detection
    homepage_text = homepage_info.get("body_text", "").lower()
    cta_keywords = ["sign up", "get started", "try free", "free trial", "book a demo",
                    "contact us", "subscribe", "download", "start free"]
    cta_found = [kw for kw in cta_keywords if kw in homepage_text]
    signals["d5_cta"] = {
        "homepage_cta_keywords": cta_found,
        "has_clear_cta": len(cta_found) > 0,
    }

    # Snippet: list conversion URLs and external platforms
    if conversion_found:
        snippets["d5_conversion_pages"] = ", ".join(sorted(set(conversion_found)))
    if external_platforms:
        snippets["d5_external_platforms"] = ", ".join(sorted(external_platforms.keys()))

    return signals, snippets


# ============================================================================
# Main Orchestrator
# ============================================================================

def collect_signals(
    url: str,
    *,
    render: str = "auto",
    max_subpages: int = MAX_SUBPAGES,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict:
    """Main entry point: fetch all data and collect signals for all dimensions."""
    started = time.perf_counter()
    timings: dict[str, float] = {}

    def record_timing(name: str, stage_started: float) -> None:
        timings[name] = round(time.perf_counter() - stage_started, 3)

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    domain = parsed.netloc
    errors: list[str] = []
    render_method = "static"
    concurrency = _bounded_workers(concurrency)
    max_subpages = max(0, int(max_subpages))

    session = requests.Session()

    # --- Fetch Phase ---
    logger.info("Fetching homepage: %s", url)
    stage_started = time.perf_counter()
    homepage_result = _get(session, url)
    record_timing("homepage_fetch_seconds", stage_started)
    if not homepage_result["ok"]:
        errors.append(f"Homepage fetch failed: {homepage_result['error']}")

    # SPA detection & rendering
    stage_started = time.perf_counter()
    if homepage_result["ok"] and render != "never":
        if _is_spa_shell(homepage_result["text"]) or render == "always":
            rendered = _render_chrome(url)
            if rendered:
                homepage_result["text"] = rendered
                render_method = "chrome"
                logger.info("SPA detected, rendered with Chrome")
            else:
                render_method = "spa_unrendered"
                logger.warning("SPA detected but Chrome unavailable")
    record_timing("homepage_render_seconds", stage_started)

    logger.info("Fetching robots.txt, llms.txt, sitemaps...")
    stage_started = time.perf_counter()
    robots_result = _get(session, urljoin(url, "/robots.txt"))
    record_timing("robots_fetch_seconds", stage_started)

    stage_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(concurrency, 4)) as executor:
        future_llms = executor.submit(_timed_call, _get_with_new_session, urljoin(url, "/llms.txt"))
        future_llms_full = executor.submit(_timed_call, _get_with_new_session, urljoin(url, "/llms-full.txt"))
        future_notfound = executor.submit(
            _timed_call,
            _get_with_new_session,
            urljoin(url, "/__geo_audit_nonexistent_path_probe__"),
        )
        future_sitemap = executor.submit(
            _timed_call,
            _discover_sitemaps,
            session,
            url,
            robots_result,
            concurrency=concurrency,
        )
        llms_result, timings["llms_fetch_seconds"] = future_llms.result()
        llms_full_result, timings["llms_full_fetch_seconds"] = future_llms_full.result()
        notfound_result, timings["notfound_probe_seconds"] = future_notfound.result()
        sitemap_info, timings["sitemap_discovery_seconds"] = future_sitemap.result()
    record_timing("resource_discovery_seconds", stage_started)

    # Multi-UA probes
    logger.info("Probing AI crawler access...")
    stage_started = time.perf_counter()
    ua_probes = _parallel_fetch(
        [(name, url, ua) for name, ua in CRAWLER_UAS.items()],
        concurrency=concurrency,
    )
    record_timing("crawler_probe_seconds", stage_started)

    # Sub-pages from sitemap
    logger.info("Fetching sampled sub-pages...")
    stage_started = time.perf_counter()
    sub_page_results: list[dict] = []
    selection_started = time.perf_counter()
    sampling_base_url = homepage_result.get("final_url") or url
    sampled_page_entries, sample_source, homepage_candidate_urls = _select_subpage_sample_entries(
        sitemap_info,
        homepage_result.get("text", ""),
        sampling_base_url,
        max_subpages,
    )
    record_timing("subpage_selection_seconds", selection_started)
    sitemap_info["sample_source"] = sample_source
    sitemap_info["homepage_candidate_url_count"] = len(homepage_candidate_urls)
    sitemap_info["homepage_candidate_urls"] = homepage_candidate_urls[:100]
    sitemap_info["sampled_page_urls"] = [entry["url"] for entry in sampled_page_entries]
    sitemap_info["sampled_page_categories"] = [
        {
            "url": entry["url"],
            "category": entry["category"],
            "template_key": entry.get("template_key", entry["category"]),
        }
        for entry in sampled_page_entries
    ]
    static_fetch_started = time.perf_counter()
    subpage_results_by_url = _parallel_fetch(
        [(entry["url"], entry["url"], DEFAULT_UA) for entry in sampled_page_entries],
        concurrency=concurrency,
    )
    record_timing("subpage_static_fetch_seconds", static_fetch_started)
    render_started = time.perf_counter()
    for sub_url in sitemap_info["sampled_page_urls"]:
        sub = subpage_results_by_url.get(sub_url, {
            "url": sub_url,
            "status": 0,
            "ok": False,
            "headers": {},
            "text": "",
            "final_url": sub_url,
            "error": "missing parallel fetch result",
        })
        if sub["ok"] and render != "never" and _is_spa_shell(sub["text"]):
            rendered = _render_chrome(sub_url)
            if rendered:
                sub["text"] = rendered
        sub_page_results.append(sub)
    record_timing("subpage_render_seconds", render_started)
    record_timing("subpage_fetch_seconds", stage_started)

    # Knowledge graph probes
    logger.info("Probing Wikipedia/Wikidata...")
    stage_started = time.perf_counter()
    brand_query = _derive_brand_query(homepage_result["text"], domain)
    knowledge_results = _parallel_fetch(
        [
            (
                "wikipedia",
                f"https://en.wikipedia.org/w/api.php?action=query&list=search"
                f"&srsearch={_url_quote(brand_query)}&format=json&srlimit=3",
                DEFAULT_UA,
            ),
            (
                "wikidata",
                f"https://www.wikidata.org/w/api.php?action=wbsearchentities"
                f"&search={_url_quote(brand_query)}&language=en&format=json&limit=3",
                DEFAULT_UA,
            ),
        ],
        concurrency=min(concurrency, 2),
        timeout=10,
    )
    wikipedia_result = knowledge_results["wikipedia"]
    wikidata_result = knowledge_results["wikidata"]
    record_timing("knowledge_graph_seconds", stage_started)

    # --- Parse Phase ---
    logger.info("Parsing HTML...")
    stage_started = time.perf_counter()
    homepage_info = _parse_html(homepage_result["text"], url)
    sub_page_infos = [_parse_html(p["text"], p.get("url", "")) for p in sub_page_results if p["ok"]]
    record_timing("html_parse_seconds", stage_started)

    # --- Signal Collection Phase ---
    logger.info("Collecting D1 signals...")
    stage_started = time.perf_counter()
    d1_signals, d1_snippets = _collect_d1(
        session, url, homepage_result, homepage_info,
        robots_result, sitemap_info,
        llms_result, llms_full_result, notfound_result,
        ua_probes, sub_page_results, render_method,
    )
    record_timing("d1_signal_collection_seconds", stage_started)

    logger.info("Collecting D2 signals...")
    stage_started = time.perf_counter()
    d2_signals, d2_snippets = _collect_d2(homepage_info, sub_page_infos, homepage_result)
    record_timing("d2_signal_collection_seconds", stage_started)

    logger.info("Collecting D3 signals...")
    stage_started = time.perf_counter()
    d3_signals, d3_snippets = _collect_d3(
        homepage_info, homepage_result, llms_result,
        sub_page_infos, wikipedia_result, wikidata_result, domain,
    )
    record_timing("d3_signal_collection_seconds", stage_started)

    logger.info("Collecting D4 signals...")
    stage_started = time.perf_counter()
    d4_signals, d4_snippets = _collect_d4(homepage_info, sub_page_infos, llms_result, homepage_result)
    record_timing("d4_signal_collection_seconds", stage_started)

    logger.info("Collecting D5 signals...")
    stage_started = time.perf_counter()
    d5_signals, d5_snippets = _collect_d5(
        homepage_info, sub_page_infos, homepage_result, sub_page_results,
    )
    record_timing("d5_signal_collection_seconds", stage_started)
    timings["total_collection_seconds"] = round(time.perf_counter() - started, 3)

    # --- Assemble Output ---
    output = {
        "meta": {
            "url": url,
            "domain": domain,
            "brand_query": brand_query,
            "render_method": render_method,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "sub_pages_fetched": len(sub_page_infos),
            "sub_pages_requested": max_subpages,
            "concurrency": concurrency,
            "report_generation_elapsed_seconds": timings["total_collection_seconds"],
            "timings": timings,
            "version": "1.6.0",
        },
        "signals": {**d1_signals, **d2_signals, **d3_signals, **d4_signals, **d5_signals},
        "snippets": {**d1_snippets, **d2_snippets, **d3_snippets, **d4_snippets, **d5_snippets},
        "errors": errors,
    }

    return output


def _derive_brand_query(html: str, domain: str) -> str:
    """Extract best-effort brand name from <title> or domain."""
    if html:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            for sep in ["|", " - ", " \u2013 ", "\u2014", " :: "]:
                if sep in title:
                    title = title.split(sep)[0].strip()
            if 2 <= len(title) <= 60:
                return title
    root = domain.split(":")[0]
    root = root[4:] if root.startswith("www.") else root
    return root.split(".")[0]


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="GEO Audit Signal Collector")
    parser.add_argument("url", help="Target URL to audit")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--render", choices=["auto", "always", "never"],
                        default="auto", help="SPA rendering mode")
    parser.add_argument("--max-subpages", type=int, default=MAX_SUBPAGES,
                        help=f"Maximum sitemap sub-pages to sample (default: {MAX_SUBPAGES})")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                        help=f"Concurrent fetch workers, capped at 12 (default: {DEFAULT_CONCURRENCY})")
    args = parser.parse_args()

    result = collect_signals(
        args.url,
        render=args.render,
        max_subpages=args.max_subpages,
        concurrency=args.concurrency,
    )

    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        logger.info("Output written to %s", args.output)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
