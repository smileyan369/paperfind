import client from './client';

const LEGACY_STORAGE_KEY = 'paperfind_llm_config';

export interface AppConfig {
  llm_api_key: string;
  llm_base_url: string;
  llm_model: string;
  auto_summary_enabled: boolean;
  ai_available: boolean;
}

export interface ConfigUpdate {
  llm_api_key?: string;
  llm_base_url?: string;
  llm_model?: string;
  auto_summary_enabled?: boolean;
}

export async function fetchConfig(): Promise<AppConfig> {
  const { data } = await client.get('/config');
  return data;
}

export async function updateConfig(updates: ConfigUpdate): Promise<AppConfig> {
  const { data } = await client.put('/config', updates);
  return data;
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

export function clearLegacyLlmConfig() {
  try {
    localStorage.removeItem(LEGACY_STORAGE_KEY);
  } catch {
    // ignore storage errors
  }
}
