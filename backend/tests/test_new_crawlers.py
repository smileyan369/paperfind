import json
import unittest

from app.services.crawler.openalex import OpenAlexCrawler
from app.services.crawler.pubmed import PubMedCrawler
from app.services.crawler.europe_pmc import EuropePMCCrawler


class NewCrawlerParseTests(unittest.TestCase):
    def test_openalex_parse_work_restores_abstract_and_metadata(self):
        crawler = OpenAlexCrawler()
        paper = crawler._parse_work({
            "id": "https://openalex.org/W1",
            "display_name": "Useful Research",
            "doi": "https://doi.org/10.1000/test",
            "publication_date": "2024-02-03",
            "publication_year": 2024,
            "cited_by_count": 12,
            "abstract_inverted_index": {"hello": [0], "world": [1]},
            "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
            "primary_location": {"source": {"display_name": "Test Journal"}},
        })

        self.assertEqual(paper["source"], "openalex")
        self.assertEqual(paper["doi"], "10.1000/test")
        self.assertEqual(paper["abstract"], "hello world")
        self.assertEqual(json.loads(paper["authors"]), ["Ada Lovelace"])
        self.assertEqual(paper["journal_name"], "Test Journal")

    def test_pubmed_parse_article_reads_title_authors_abstract_and_doi(self):
        crawler = PubMedCrawler()
        papers = crawler._parse_articles("""
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation>
              <PMID>12345</PMID>
              <Article>
                <Journal>
                  <Title>Medical Journal</Title>
                  <JournalIssue><PubDate><Year>2023</Year><Month>Dec</Month><Day>5</Day></PubDate></JournalIssue>
                </Journal>
                <ArticleTitle>Clinical AI Study</ArticleTitle>
                <Abstract><AbstractText Label="BACKGROUND">Helpful abstract.</AbstractText></Abstract>
                <AuthorList><Author><ForeName>Ada</ForeName><LastName>Lovelace</LastName></Author></AuthorList>
              </Article>
            </MedlineCitation>
            <PubmedData><ArticleIdList><ArticleId IdType="doi">10.1000/pubmed</ArticleId></ArticleIdList></PubmedData>
          </PubmedArticle>
        </PubmedArticleSet>
        """)

        self.assertEqual(len(papers), 1)
        paper = papers[0]
        self.assertEqual(paper["source"], "pubmed")
        self.assertEqual(paper["source_id"], "12345")
        self.assertEqual(paper["title"], "Clinical AI Study")
        self.assertEqual(paper["abstract"], "BACKGROUND: Helpful abstract.")
        self.assertEqual(json.loads(paper["authors"]), ["Ada Lovelace"])
        self.assertEqual(paper["publication_date"], "2023-12-05")
        self.assertEqual(paper["doi"], "10.1000/pubmed")

    def test_europe_pmc_parse_result_reads_open_pdf_metadata(self):
        crawler = EuropePMCCrawler()
        paper = crawler._parse_result({
            "title": "Open access biomedical AI",
            "authorString": "Alice A, Bob B.",
            "abstractText": "A test abstract.",
            "firstPublicationDate": "2025-05-01",
            "source": "MED",
            "pmid": "123",
            "pmcid": "PMC123",
            "doi": "10.1000/pmc",
            "journalTitle": "Test Journal",
            "citedByCount": "9",
            "pubYear": "2025",
        })

        self.assertEqual(paper["source"], "europe_pmc")
        self.assertEqual(paper["source_id"], "PMC123")
        self.assertEqual(paper["pdf_url"], "https://europepmc.org/articles/PMC123?pdf=render")
        self.assertEqual(paper["citation_count"], 9)


if __name__ == "__main__":
    unittest.main()
