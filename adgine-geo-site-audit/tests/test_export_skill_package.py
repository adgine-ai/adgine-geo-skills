import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import export_skill_package  # noqa: E402


class ExportSkillPackageTests(unittest.TestCase):
    def test_export_package_includes_skill_files_and_excludes_caches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "skill.zip"

            code = export_skill_package.main(["--output", str(output_path), "--json"])

            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)

            with zipfile.ZipFile(output_path) as zip_handle:
                names = set(zip_handle.namelist())
                manifest = json.loads(zip_handle.read("adgine-geo-site-audit/PACKAGE_MANIFEST.json"))

            self.assertIn("adgine-geo-site-audit/SKILL.md", names)
            self.assertIn("adgine-geo-site-audit/README.md", names)
            self.assertIn("adgine-geo-site-audit/requirements.txt", names)
            self.assertIn("adgine-geo-site-audit/scripts/geo_collect.py", names)
            self.assertIn("adgine-geo-site-audit/scripts/export_skill_package.py", names)
            self.assertIn("adgine-geo-site-audit/tests/test_export_skill_package.py", names)
            self.assertEqual(manifest["name"], "adgine-geo-site-audit")
            self.assertFalse(any("__pycache__" in name for name in names))
            self.assertFalse(any(name.endswith(".pyc") for name in names))
            self.assertFalse(any(name.startswith("adgine-geo-site-audit/.git/") for name in names))

    def test_export_package_can_exclude_tests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "skill-runtime.zip"

            code = export_skill_package.main(["--output", str(output_path), "--no-tests"])

            self.assertEqual(code, 0)
            with zipfile.ZipFile(output_path) as zip_handle:
                names = set(zip_handle.namelist())

            self.assertIn("adgine-geo-site-audit/SKILL.md", names)
            self.assertFalse(any("/tests/" in name for name in names))


if __name__ == "__main__":
    unittest.main()
