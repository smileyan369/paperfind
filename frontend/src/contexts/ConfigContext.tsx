import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import {
  clearLegacyLlmConfig,
  fetchConfig,
  readLegacyLlmConfig,
  updateConfig,
  type AppConfig,
  type ConfigUpdate,
} from '../api/config';

interface ConfigState {
  config: AppConfig | null;
  loading: boolean;
  error: string | null;
  refreshConfig: () => Promise<void>;
  saveConfig: (updates: ConfigUpdate) => Promise<AppConfig>;
}

const ConfigContext = createContext<ConfigState | null>(null);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshConfig = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let next = await fetchConfig();

      if (!next.ai_available) {
        const legacy = readLegacyLlmConfig();
        if (legacy?.llm_api_key) {
          next = await updateConfig(legacy);
          clearLegacyLlmConfig();
        }
      }

      setConfig(next);
    } catch (err: any) {
      setError(err?.message || 'Failed to load config');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshConfig();
  }, [refreshConfig]);

  const saveConfig = useCallback(async (updates: ConfigUpdate) => {
    const next = await updateConfig(updates);
    setConfig(next);
    clearLegacyLlmConfig();
    return next;
  }, []);

  return (
    <ConfigContext.Provider value={{ config, loading, error, refreshConfig, saveConfig }}>
      {children}
    </ConfigContext.Provider>
  );
}

export function useAppConfig() {
  const ctx = useContext(ConfigContext);
  if (!ctx) throw new Error('useAppConfig must be used within ConfigProvider');
  return ctx;
}
