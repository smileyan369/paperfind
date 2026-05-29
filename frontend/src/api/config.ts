import client from './client';

const LEGACY_STORAGE_KEY = 'paperfind_llm_config';

export interface AppConfig {
  llm_api_key: string;
  llm_base_url: string;
  llm_model: string;
  auto_summary_enabled: boolean;
  research_profile: string;
  ai_available: boolean;
}

export interface ConfigUpdate {
  llm_api_key?: string;
  llm_base_url?: string;
  llm_model?: string;
  auto_summary_enabled?: boolean;
  research_profile?: string;
}

export interface KeywordHistoryEntry {
  text: string;
  added_at: string;
}

export async function fetchConfig(): Promise<AppConfig> {
  const { data } = await client.get('/config');
  return data;
}

export async function updateConfig(updates: ConfigUpdate): Promise<AppConfig> {
  const { data } = await client.put('/config', updates);
  writeLegacyLlmConfig(updates);
  return data;
}

export async function fetchKeywordHistory(): Promise<KeywordHistoryEntry[]> {
  const { data } = await client.get('/config/keyword-history');
  return data.entries || [];
}

export async function saveKeywordHistory(entries: KeywordHistoryEntry[]): Promise<KeywordHistoryEntry[]> {
  const { data } = await client.put('/config/keyword-history', { entries });
  return data.entries || [];
}

function isMaskedKey(key: string): boolean {
  return key.startsWith('****');
}

export function readLegacyLlmConfig(): ConfigUpdate | null {
  try {
    const stored = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!stored) return null;
    const cfg = JSON.parse(stored);
    const key = String(cfg.llm_api_key || '').trim();
    const baseUrl = String(cfg.llm_base_url || '').trim();
    const model = String(cfg.llm_model || '').trim();
    const result: ConfigUpdate = {};
    if (key && !isMaskedKey(key)) result.llm_api_key = key;
    if (baseUrl) result.llm_base_url = baseUrl;
    if (model) result.llm_model = model;
    return Object.keys(result).length > 0 ? result : null;
  } catch {
    return null;
  }
}

export function writeLegacyLlmConfig(updates: ConfigUpdate) {
  try {
    const existing = readLegacyLlmConfig() || {};
    const next: ConfigUpdate = { ...existing };
    const key = String(updates.llm_api_key || '').trim();
    const baseUrl = String(updates.llm_base_url || '').trim();
    const model = String(updates.llm_model || '').trim();
    if (key && !isMaskedKey(key)) next.llm_api_key = key;
    if (baseUrl) next.llm_base_url = baseUrl;
    if (model) next.llm_model = model;
    if (Object.keys(next).length > 0) {
      localStorage.setItem(LEGACY_STORAGE_KEY, JSON.stringify(next));
    }
  } catch {
    // ignore storage errors
  }
}

export function clearLegacyLlmConfig() {
  try {
    // Keep this browser-side copy as a last-resort recovery path when users
    // replace the packaged exe or accidentally point it at a fresh database.
  } catch {
    // ignore storage errors
  }
}
