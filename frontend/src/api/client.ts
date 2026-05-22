import axios from 'axios';

export function getApiUrl(): string {
  // In dev mode, use relative path (goes through Vite proxy).
  // In production, frontend is served from the same backend, so relative path works.
  return '/api';
}

export function getApiKey(): string {
  try {
    const stored = localStorage.getItem('paperfind_llm_config');
    if (stored) {
      const cfg = JSON.parse(stored);
      return cfg.llm_api_key || '';
    }
  } catch {}
  return '';
}

export function setApiKey(key: string, baseUrl: string, model: string) {
  localStorage.setItem('paperfind_llm_config', JSON.stringify({
    llm_api_key: key,
    llm_base_url: baseUrl,
    llm_model: model,
  }));
}

export function getLlmConfig(): { apiKey: string; baseUrl: string; model: string } {
  try {
    const stored = localStorage.getItem('paperfind_llm_config');
    if (stored) {
      const cfg = JSON.parse(stored);
      return {
        apiKey: cfg.llm_api_key || '',
        baseUrl: cfg.llm_base_url || '',
        model: cfg.llm_model || '',
      };
    }
  } catch {}
  return { apiKey: '', baseUrl: '', model: '' };
}

const client = axios.create({ timeout: 60000 });

client.interceptors.request.use((config) => {
  config.baseURL = '/api';
  return config;
});

export function apiUrl(path: string): string {
  return '/api' + path;
}

export function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  return fetch('/api' + path, options);
}

export default client;
