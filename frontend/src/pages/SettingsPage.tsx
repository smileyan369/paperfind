import { useEffect, useState } from 'react';
import CrawlButton from '../components/crawl/CrawlButton';
import CrawlStatusBadge from '../components/crawl/CrawlStatusBadge';
import { useCrawl } from '../hooks/useCrawl';
import { useGlobalCrawl } from '../contexts/CrawlContext';
import { useAppConfig } from '../contexts/ConfigContext';
import { fetchPaperStats } from '../api/papers';
import { sourceLabel } from '../utils/labels';
import type { PaperStats } from '../types/paper';

export default function SettingsPage() {
  const { logs, logsTotal, schedule, changeSchedule } = useCrawl();
  const { crawling, startCrawl } = useGlobalCrawl();
  const { config, loading: configLoading, error: configError, saveConfig } = useAppConfig();
  const [stats, setStats] = useState<PaperStats | null>(null);
  const [hour, setHour] = useState(8);
  const [minute, setMinute] = useState(0);
  const [scheduleSaved, setScheduleSaved] = useState(false);
  const [editingApi, setEditingApi] = useState(false);
  const [apiKey, setApiKeyLocal] = useState('');
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [apiModel, setApiModel] = useState('');
  const [savingConfig, setSavingConfig] = useState(false);

  useEffect(() => {
    fetchPaperStats().then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    if (schedule?.daily_crawl.next_run) {
      const d = new Date(schedule.daily_crawl.next_run);
      setHour(d.getHours());
      setMinute(d.getMinutes());
    }
  }, [schedule?.daily_crawl.next_run]);

  useEffect(() => {
    if (!config) return;
    setApiBaseUrl(config.llm_base_url || '');
    setApiModel(config.llm_model || '');
  }, [config?.llm_base_url, config?.llm_model]);

  const handleSaveSchedule = async () => {
    await changeSchedule(hour, minute);
    setScheduleSaved(true);
    setTimeout(() => setScheduleSaved(false), 2000);
  };

  const handleSaveApiConfig = async () => {
    setSavingConfig(true);
    try {
      const updates: {
        llm_api_key?: string;
        llm_base_url: string;
        llm_model: string;
      } = {
        llm_base_url: apiBaseUrl.trim(),
        llm_model: apiModel.trim(),
      };
      const key = apiKey.trim();
      if (key) updates.llm_api_key = key;
      await saveConfig(updates);
      setApiKeyLocal('');
      setEditingApi(false);
    } finally {
      setSavingConfig(false);
    }
  };

  const maskedKey = (key: string) => {
    if (!key) return '未设置';
    if (key.length <= 4 || key.startsWith('****')) return key.startsWith('****') ? key : '****';
    return '****' + key.slice(-4);
  };

  const aiAvailable = !!config?.ai_available;

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h2 className="text-lg font-bold text-gray-800">设置</h2>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800 flex items-start gap-2">
        <span className="text-lg shrink-0">!</span>
        <div>
          <p className="font-medium">网络提醒</p>
          <p className="text-amber-700 text-xs mt-0.5">
            部分论文数据源在国内可能需要代理或 VPN 才能访问。爬取时如果某个来源无法连接，系统会跳过并记录原因。
          </p>
        </div>
      </div>

      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-semibold text-sm text-gray-700 mb-3">API 配置</h3>
        {configError && <p className="text-xs text-red-500 mb-2">{configError}</p>}

        {!editingApi ? (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between gap-3">
              <span className="text-gray-500">API Key</span>
              <span className="text-gray-700 font-mono text-xs">{configLoading ? '...' : maskedKey(config?.llm_api_key || '')}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-gray-500">Base URL</span>
              <span className="text-gray-700 font-mono text-xs truncate max-w-[250px]">{config?.llm_base_url || '未设置'}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-gray-500">模型</span>
              <span className="text-gray-700 font-mono text-xs">{config?.llm_model || '未设置'}</span>
            </div>
            <div className="flex justify-between items-center pt-1">
              <span className="text-gray-500">
                AI 摘要
                {aiAvailable
                  ? <span className="text-emerald-600 ml-1">可用</span>
                  : <span className="text-amber-600 ml-1">未启用（未配置 API Key）</span>
                }
              </span>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setEditingApi(true)}
                disabled={configLoading}
                className="text-xs px-3 py-1.5 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                修改
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">
                LLM API Key <span className="text-gray-400">（留空则保留当前 Key）</span>
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={e => setApiKeyLocal(e.target.value)}
                placeholder={config?.ai_available ? '输入新 Key 覆盖当前值' : '请输入 API Key'}
                className="w-full px-3 py-1.5 text-sm border rounded-md"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">API Base URL</label>
              <input
                type="text"
                value={apiBaseUrl}
                onChange={e => setApiBaseUrl(e.target.value)}
                placeholder="例如 https://api.openai.com/v1"
                className="w-full px-3 py-1.5 text-sm border rounded-md"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">模型</label>
              <input
                type="text"
                value={apiModel}
                onChange={e => setApiModel(e.target.value)}
                placeholder="例如 gpt-4o-mini"
                className="w-full px-3 py-1.5 text-sm border rounded-md"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleSaveApiConfig}
                disabled={savingConfig}
                className="text-xs px-3 py-1.5 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {savingConfig ? '保存中...' : '保存'}
              </button>
              <button
                onClick={() => setEditingApi(false)}
                disabled={savingConfig}
                className="text-xs px-3 py-1.5 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50"
              >
                取消
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-semibold text-sm text-gray-700 mb-3">AI 自动摘要</h3>
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={!!config?.auto_summary_enabled}
            disabled={configLoading || savingConfig || !aiAvailable}
            onChange={async e => {
              setSavingConfig(true);
              try {
                await saveConfig({ auto_summary_enabled: e.target.checked });
              } finally {
                setSavingConfig(false);
              }
            }}
            className="mt-1 w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span>
            <span className="block text-sm text-gray-700">自动生成 AI 摘要</span>
            <span className="block text-xs text-gray-500 mt-1">
              开启后，系统会在后台调用 AI 为待处理论文生成摘要，可能产生 API 费用。新用户默认关闭。
            </span>
            {!aiAvailable && (
              <span className="block text-xs text-amber-600 mt-1">请先配置 API Key 后再开启自动摘要。</span>
            )}
          </span>
        </label>
      </div>

      {stats && (
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold text-sm text-gray-700 mb-3">论文统计</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-gray-500">总计</p>
              <p className="text-xl font-bold text-gray-800">{stats.total}</p>
            </div>
            <div className="bg-indigo-50 rounded-lg p-3">
              <p className="text-gray-500">已总结</p>
              <p className="text-xl font-bold text-indigo-700">{stats.with_summary}</p>
            </div>
            {stats.by_zone && Object.entries(stats.by_zone).map(([zone, count]) => (
              <div key={zone} className="bg-gray-50 rounded-lg p-3">
                <p className="text-gray-500">SCI {zone}</p>
                <p className="text-xl font-bold text-gray-800">{count}</p>
              </div>
            ))}
            {stats.by_source && Object.entries(stats.by_source).map(([source, count]) => (
              <div key={source} className="bg-gray-50 rounded-lg p-3">
                <p className="text-gray-500">{sourceLabel(source)}</p>
                <p className="text-xl font-bold text-gray-800">{count}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-semibold text-sm text-gray-700 mb-3">手动爬取</h3>
        <p className="text-xs text-gray-500 mb-3">
          立即触发一次爬取任务，从所有来源检索并入库论文。已存在的论文会跳过或补全信息。
        </p>
        <CrawlButton crawling={crawling} onClick={() => startCrawl()} />
      </div>

      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-semibold text-sm text-gray-700 mb-3">定时爬取</h3>
        <p className="text-xs text-gray-500 mb-3">
          设置每日自动爬取时间。是否自动生成摘要由上方“AI 自动摘要”开关控制。
        </p>
        <div className="flex items-center gap-2 mb-3">
          <input
            type="number"
            min={0}
            max={23}
            value={hour}
            onChange={e => setHour(Number(e.target.value))}
            className="w-16 px-2 py-1.5 text-sm border rounded-md"
          />
          <span className="text-gray-500">:</span>
          <input
            type="number"
            min={0}
            max={59}
            value={minute}
            onChange={e => setMinute(Number(e.target.value))}
            className="w-16 px-2 py-1.5 text-sm border rounded-md"
          />
          <button
            onClick={handleSaveSchedule}
            className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 transition-colors"
          >
            {scheduleSaved ? '已保存' : '保存'}
          </button>
        </div>
        {schedule?.daily_crawl.next_run && (
          <p className="text-xs text-gray-500">
            下次执行: {new Date(schedule.daily_crawl.next_run).toLocaleString('zh-CN')}
          </p>
        )}
      </div>

      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-semibold text-sm text-gray-700 mb-3">爬取日志</h3>
        {logs.length === 0 ? (
          <p className="text-sm text-gray-400">暂无日志</p>
        ) : (
          <div className="space-y-2">
            {logs.slice(0, 10).map(log => (
              <div key={log.id} className="flex items-center gap-3 text-sm py-2 border-b border-gray-50 last:border-0">
                <CrawlStatusBadge status={log.status} />
                <span className="text-gray-600">{log.source}</span>
                <span className="text-xs text-gray-400">
                  {log.papers_new > 0 && `新增 ${log.papers_new}`}
                  {log.papers_updated > 0 && ` 更新 ${log.papers_updated}`}
                </span>
                <span className="text-xs text-gray-400 ml-auto">
                  {new Date(log.started_at).toLocaleString('zh-CN')}
                </span>
              </div>
            ))}
            {logsTotal > 10 && (
              <p className="text-xs text-gray-400 text-center pt-2">共 {logsTotal} 条日志</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
