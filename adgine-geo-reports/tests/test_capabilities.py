import json
import os
import sys
import tempfile
import unittest

os.environ.setdefault("GEO_SKIP_VERSION_CHECK", "1")
SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from _capabilities import _cache_path, discover_capabilities, supports  # noqa: E402
from _client import ApiError  # noqa: E402


class CapabilityClient:
    def __init__(self, responses):
        self.base = "https://api.example.test"
        self.project_id = "project-visible-id"
        self.responses = list(responses)
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        os.environ["GEO_REPORT_CACHE_DIR"] = self.directory.name

    def tearDown(self):
        os.environ.pop("GEO_REPORT_CACHE_DIR", None)
        os.environ.pop("GEO_REPORT_CAPABILITY_CACHE_TTL_SECONDS", None)
        self.directory.cleanup()

    def test_two_hour_disk_cache_avoids_second_probe(self):
        client = CapabilityClient([{
            "schema_version": "1.0",
            "features": {"prompt_performance": True},
        }])
        first, warning = discover_capabilities(client, now=1000)
        second, second_warning = discover_capabilities(client, now=8000)
        self.assertIsNone(warning)
        self.assertIsNone(second_warning)
        self.assertTrue(supports(first, "prompt_performance"))
        self.assertEqual(second, first)
        self.assertEqual(len(client.calls), 1)
        cached = _cache_path(client.base, client.project_id).read_text(encoding="utf-8")
        self.assertNotIn("api_key", cached.lower())
        self.assertNotIn("token", cached.lower())

    def test_route_absence_selects_legacy_mode(self):
        client = CapabilityClient([ApiError("missing", status_code=404)])
        data, warning = discover_capabilities(client)
        self.assertTrue(data["legacy"])
        self.assertIn("legacy", warning.lower())

    def test_stale_cache_is_used_for_discovery_5xx(self):
        client = CapabilityClient([{
            "schema_version": "1.0",
            "features": {"pages": True},
        }])
        discover_capabilities(client, now=1000)
        client.responses.append(ApiError("down", status_code=503))
        data, warning = discover_capabilities(client, now=8201)
        self.assertTrue(supports(data, "pages"))
        self.assertIn("stale", warning.lower())

    def test_cache_ttl_can_be_shortened_for_rollout(self):
        os.environ["GEO_REPORT_CAPABILITY_CACHE_TTL_SECONDS"] = "60"
        client = CapabilityClient([{
            "schema_version": "1.0",
            "features": {"pages": True},
        }, {
            "schema_version": "1.0",
            "features": {"pages": False},
        }])
        first, _ = discover_capabilities(client, now=1000)
        second, warning = discover_capabilities(client, now=1061)
        self.assertTrue(supports(first, "pages"))
        self.assertFalse(supports(second, "pages"))
        self.assertIsNone(warning)
        self.assertEqual(len(client.calls), 2)

    def test_auth_failure_never_falls_back(self):
        client = CapabilityClient([ApiError("forbidden", status_code=403)])
        with self.assertRaises(ApiError):
            discover_capabilities(client)

    def test_cache_is_valid_json(self):
        client = CapabilityClient([{"schema_version": "1.0", "features": {}}])
        discover_capabilities(client)
        payload = json.loads(_cache_path(client.base, client.project_id).read_text())
        self.assertEqual(payload["data"]["schema_version"], "1.0")


if __name__ == "__main__":
    unittest.main()
