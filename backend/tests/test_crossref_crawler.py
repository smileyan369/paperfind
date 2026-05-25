import json
import unittest

from app.services.crawler.crossref import CrossrefCrawler


class CrossrefCrawlerTests(unittest.TestCase):
    def test_parse_paper_normalizes_crossref_metadata(self):
        crawler = CrossrefCrawler()

        paper = crawler._parse_paper({
            "title": ["Example Medical Paper"],
            "author": [
                {"given": "Ada", "family": "Lovelace"},
                {"given": "Grace", "family": "Hopper"},
            ],
            "abstract": "<jats:p>This is an abstract.</jats:p>",
            "published-online": {"date-parts": [[2024, 5]]},
            "container-title": ["Journal of Useful Tests"],
            "DOI": "10.1000/example",
            "URL": "https://doi.org/10.1000/example",
            "is-referenced-by-count": 7,
        })

        self.assertEqual(paper["source"], "crossref")
        self.assertEqual(paper["title"], "Example Medical Paper")
        self.assertEqual(json.loads(paper["authors"]), ["Ada Lovelace", "Grace Hopper"])
        self.assertEqual(paper["abstract"], "This is an abstract.")
        self.assertEqual(paper["publication_date"], "2024-05-01")
        self.assertEqual(paper["journal_name"], "Journal of Useful Tests")
        self.assertEqual(paper["doi"], "10.1000/example")
        self.assertEqual(paper["citation_count"], 7)


if __name__ == "__main__":
    unittest.main()
