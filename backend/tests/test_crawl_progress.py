import unittest

from app.routers.crawl import CrawlEventBus
from app.services.crawler.orchestrator import _keyword_matches, _parse_date, _query_variants


class CrawlProgressTests(unittest.TestCase):
    def test_cancel_marks_running_crawl_for_stop(self):
        bus = CrawlEventBus()
        bus.running = True
        bus.message = "running"

        self.assertTrue(bus.cancel())
        self.assertEqual(bus.message, "检索已取消")

    def test_cancel_returns_false_when_idle(self):
        bus = CrawlEventBus()
        self.assertFalse(bus.cancel())

    def test_keyword_match_handles_underscores_and_hyphens(self):
        self.assertTrue(_keyword_matches(
            "Highly Condensed All-MLP Architecture for Long-Term Human Motion Prediction",
            "Highly_Condensed_All-MLP_Architecture_for_Long-Term_Human_Motion_Prediction",
        ))

    def test_chinese_keyword_adds_english_query_hint(self):
        self.assertIn("cybersecurity", _query_variants("\u7f51\u7edc\u5b89\u5168"))

    def test_short_ar_does_not_match_author_prefix(self):
        self.assertFalse(_keyword_matches("AI protocols by Kamal Ar-Reyouchi", "AR"))
        self.assertTrue(_keyword_matches("An augmented reality interface", "AR"))

    def test_future_publication_date_is_ignored(self):
        self.assertIsNone(_parse_date("2999-01-01"))


if __name__ == "__main__":
    unittest.main()
