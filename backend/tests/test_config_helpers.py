import unittest

from app.routers.config import _is_masked_key, _mask_key, _to_bool


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


if __name__ == "__main__":
    unittest.main()
