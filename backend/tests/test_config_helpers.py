import unittest

from app.routers.config import ConfigUpdateRequest, _is_masked_key, _mask_key, _to_bool
from app.routers.keywords import _fallback_suggestions


class ConfigHelperTests(unittest.TestCase):
    def test_mask_key_never_exposes_full_value(self):
        self.assertEqual(_mask_key(""), "")
        self.assertEqual(_mask_key("abc"), "****")
        self.assertEqual(_mask_key("sk-test-123456"), "****3456")

    def test_masked_key_detection(self):
        self.assertTrue(_is_masked_key("****3456"))
        self.assertTrue(_is_masked_key("****"))
        self.assertFalse(_is_masked_key("sk-real-key"))
        self.assertFalse(_is_masked_key(""))

    def test_to_bool_accepts_expected_truthy_values(self):
        for value in (True, "true", "TRUE", "1", "yes", "on"):
            with self.subTest(value=value):
                self.assertTrue(_to_bool(value))

    def test_to_bool_defaults_to_false(self):
        for value in (False, None, "", "false", "0", "no", "off"):
            with self.subTest(value=value):
                self.assertFalse(_to_bool(value))

    def test_research_profile_is_accepted_by_config_request(self):
        data = ConfigUpdateRequest(research_profile="AI for radiology")
        self.assertEqual(data.research_profile, "AI for radiology")

    def test_fallback_keyword_suggestions_extract_terms(self):
        suggestions = _fallback_suggestions("找医学影像报告生成 radiology report generation 的论文", 5)
        self.assertTrue(suggestions)
        self.assertLessEqual(len(suggestions), 5)


if __name__ == "__main__":
    unittest.main()
