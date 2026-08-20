import importlib.util
import os
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load(relative, module_name):
    path = os.path.join(ROOT, relative)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ParameterValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.languages = load(
            "adgine-geo-brand/scripts/_language.py", "brand_language_contract"
        )
        cls.platforms = load(
            "adgine-geo-topics/scripts/_platforms.py", "topic_platform_contract"
        )
        cls.traffic = load(
            "adgine-geo-aiagent/scripts/_traffic_types.py", "traffic_type_contract"
        )
        cls.report_platforms = load(
            "adgine-geo-reports/scripts/_platforms.py", "report_platform_contract"
        )

    def test_localized_languages_use_backend_canonical_values(self):
        self.assertEqual(
            self.languages.normalize_language("中文"), "Chinese (Simplified)"
        )
        self.assertEqual(
            self.languages.normalize_language("繁體中文"), "Chinese (Traditional)"
        )
        self.assertEqual(self.languages.normalize_language("英文"), "English")
        with self.assertRaisesRegex(ValueError, "unsupported language"):
            self.languages.normalize_language("Klingon")

    def test_platform_display_names_use_backend_ids(self):
        self.assertEqual(
            self.platforms.normalize_platforms(
                "ChatGPT, Perplexity, Google AI Overviews, 腾讯元宝"
            ),
            ["openai", "perplexity", "google_aio", "yuanbao"],
        )
        self.assertEqual(
            self.platforms.normalize_platforms(["openai,qwen", "豆包", "文心一言"]),
            ["openai", "qwen", "doubao", "baidu"],
        )
        with self.assertRaisesRegex(ValueError, "gemini"):
            self.platforms.normalize_platform("gemini")
        self.assertEqual(
            self.report_platforms.normalize_platforms(
                ["ChatGPT,Google AI Overviews", "豆包"]
            ),
            ["openai", "google_aio", "doubao"],
        )

    def test_platform_helpers_remain_identical_across_standalone_skills(self):
        paths = (
            "adgine-geo-topics/scripts/_platforms.py",
            "adgine-geo-visibility/scripts/_platforms.py",
        )
        contents = []
        for relative in paths:
            with open(os.path.join(ROOT, relative), encoding="utf-8") as handle:
                contents.append(handle.read())
        self.assertEqual(contents[0], contents[1])

    def test_traffic_type_groups_expand_to_supported_backend_values(self):
        self.assertEqual(
            self.traffic.normalize_traffic_types("bot"),
            "ai_search,ai_training,ai_assistant,ai_agent",
        )
        self.assertEqual(
            self.traffic.normalize_traffic_types("human"),
            "ai_human_referral,utm_ai",
        )
        self.assertEqual(
            self.traffic.normalize_traffic_types("ai_assistant,ai_training"),
            "ai_assistant,ai_training",
        )
        self.assertIsNone(self.traffic.normalize_traffic_types("all"))
        with self.assertRaisesRegex(ValueError, "unsupported traffic type"):
            self.traffic.normalize_traffic_types("crawler")


if __name__ == "__main__":
    unittest.main()
