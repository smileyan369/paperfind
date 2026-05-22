export interface Paper {
  id: number;
  title: string;
  authors: string;
  abstract: string | null;
  publication_date: string | null;
  source: string;
  doi: string | null;
  arxiv_id: string | null;
  url: string | null;
  pdf_url: string | null;
  journal_name: string | null;
  sci_zone: string | null;
  citation_count: number;
  year: number | null;
  is_starred: boolean;
  has_summary: boolean;
  summary_status: 'completed' | 'processing' | 'none';
  keyword_texts: string[];
  keyword_ids: number[];
  crawled_at: string | null;
  updated_at: string | null;
}

export interface PaperDetail extends Paper {
  summary_cn: string | null;
  key_points_cn: string | null;
  model_used: string | null;
  summary_generated_at: string | null;
  source_type: string | null;
  source_chars: number;
}

export interface PaperListResponse {
  total: number;
  page: number;
  page_size: number;
  papers: Paper[];
}

export interface PaperStats {
  total: number;
  with_summary: number;
  by_zone: Record<string, number>;
  by_source: Record<string, number>;
}

export interface PaperFilterParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
  'sci_zone[]'?: string[];
  'source[]'?: string[];
  'keyword_id[]'?: number[];
  date_from?: string;
  date_to?: string;
  citations_min?: number;
  q?: string;
  has_summary?: boolean;
  starred?: boolean;
}
