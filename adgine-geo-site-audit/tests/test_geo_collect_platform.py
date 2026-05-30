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


if __name__ == "__main__":
    unittest.main()
