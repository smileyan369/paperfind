const SOURCE_LABELS: Record<string, string> = {
  arxiv: 'arXiv',
  crossref: 'Crossref',
  openalex: 'OpenAlex',
  pubmed: 'PubMed',
  europe_pmc: 'Europe PMC',
  semantic_scholar: 'Semantic Scholar',
  dblp: 'DBLP',
  google_scholar: 'Google Scholar',
  jnu_library: '暨大图书馆',
};

export function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] || source;
}

const ZONE_LABELS: Record<string, string> = {
  Q1: 'SCI Q1',
  Q2: 'SCI Q2',
  Q3: 'SCI Q3',
  Q4: 'SCI Q4',
};

export function zoneLabel(zone: string | null): string {
  if (!zone) return '未收录';
  return ZONE_LABELS[zone] || zone;
}
