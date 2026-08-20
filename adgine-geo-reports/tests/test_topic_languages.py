import os
import sys
import unittest


TOPIC_SCRIPTS = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "adgine-geo-topics", "scripts",
))
if TOPIC_SCRIPTS not in sys.path:
    sys.path.append(TOPIC_SCRIPTS)

from _language import normalize_language  # noqa: E402


class TopicLanguageNormalizationTests(unittest.TestCase):
    def test_simplified_chinese_conversation_labels_are_canonicalized(self):
        for value in ("中文", "简体中文", "簡體中文", "zh", "zh-CN", "zh_Hans"):
            with self.subTest(value=value):
                self.assertEqual(normalize_language(value), "Chinese (Simplified)")

    def test_traditional_chinese_and_english_aliases_are_canonicalized(self):
        self.assertEqual(normalize_language("繁體中文"), "Chinese (Traditional)")
        self.assertEqual(normalize_language("zh-TW"), "Chinese (Traditional)")
        self.assertEqual(normalize_language("英文"), "English")
        self.assertEqual(normalize_language("English (en-US)"), "English")

    def test_omitted_language_keeps_topic_inheritance(self):
        self.assertIsNone(normalize_language(None))
        self.assertIsNone(normalize_language("  "))

    def test_unsupported_language_fails_locally_with_clear_error(self):
        with self.assertRaisesRegex(ValueError, "unsupported language"):
            normalize_language("不存在的语言")


if __name__ == "__main__":
    unittest.main()
