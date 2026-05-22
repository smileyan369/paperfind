  export type SciZone = 'Q1' | 'Q2' | 'Q3' | 'Q4';
export type PaperSource = 'arxiv' | 'semantic_scholar' | 'dblp' | 'google_scholar' | 'jnu_library' | 'ieee' | 'acm';
export type SortField = 'sci_zone' | 'publication_date' | 'citation_count' | 'title' | 'updated_at' | 'crawled_at';
export type SortOrder = 'asc' | 'desc';

export interface FilterState {
  sciZones: SciZone[];
  sources: PaperSource[];
  keywordIds: number[];
  dateFrom: string | null;
  dateTo: string | null;
  citationsMin: number | null;
  searchQuery: string;
  hasSummary: boolean | null;
  starred: boolean | null;
  sortBy: SortField;
  sortOrder: SortOrder;
}
