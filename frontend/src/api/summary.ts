import client from './client';

interface SummaryData {
  id: number;
  paper_id: number;
  summary_cn: string | null;
  key_points_cn: string | null;
  model_used: string;
  tokens_used: number;
  generated_at: string;
  error_message: string | null;
}

export async function summarizePaper(paperId: number): Promise<SummaryData> {
  const { data } = await client.post(`/summary/${paperId}`);
  return data;
}

export async function batchSummarize(limit = 10): Promise<{ success: number; failed: number; errors: { paper_id: number; error: string }[] }> {
  const { data } = await client.post('/summary/batch', { limit });
  return data;
}
