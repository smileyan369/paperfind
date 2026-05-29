import { useEffect, useState } from 'react';
import { apiUrl } from '../../api/client';
import { useAppConfig } from '../../contexts/ConfigContext';

interface ProcessingPaper {
  id: number;
  title: string;
}

interface ProgressData {
  total_papers: number;
  total_summarized: number;
  remaining: number;
  currently_processing: ProcessingPaper[];
  running: boolean;
}

export default function SummaryProgressBar() {
  const { config } = useAppConfig();
  const [data, setData] = useState<ProgressData | null>(null);

  useEffect(() => {
    let active = true;
    const fetchProgress = async () => {
      try {
        const res = await fetch(apiUrl('/summary/progress'));
        if (!res.ok) return;
        const json = await res.json();
        if (active) setData(json);
      } catch { /* ignore */ }
    };
    if (!config?.ai_available || !config?.auto_summary_enabled) {
      setData(null);
      return;
    }
    fetchProgress();
    const interval = setInterval(fetchProgress, 5000);
    return () => { active = false; clearInterval(interval); };
  }, [config?.ai_available, config?.auto_summary_enabled]);

  if (!config?.ai_available || !config?.auto_summary_enabled || !data || !data.running) return null;

  const total = data.total_papers || 1;
  const done = data.total_summarized;
  const pct = Math.round((done / total) * 100);
  const hasProcessing = data.currently_processing.length > 0;

  return (
    <div className="glass-panel rounded-2xl px-4 py-3 mb-4 soft-appear">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          已总结 <span className="text-indigo-600 font-semibold">{done}</span> / {total} 篇
          {data.remaining > 0 && (
            <span className="text-gray-400 ml-1">({pct}%)</span>
          )}
        </span>
        {hasProcessing && (
          <span className="flex items-center gap-1.5 text-xs text-amber-600">
            <span className="inline-block w-2.5 h-2.5 border-2 border-amber-400 border-t-amber-600 rounded-full animate-spin" />
            正在总结...
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-white/80 rounded-full overflow-hidden border border-white/70">
        <div
          className="h-full bg-gradient-to-r from-indigo-500 to-cyan-500 rounded-full transition-all duration-700 ease-out progress-glow"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Currently processing titles */}
      {hasProcessing && (
        <div className="mt-2 space-y-1">
          {data.currently_processing.slice(0, 3).map(p => (
            <p key={p.id} className="text-xs text-gray-500 truncate flex items-center gap-1.5">
              <span className="inline-block w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse shrink-0" />
              {p.title}
            </p>
          ))}
          {data.currently_processing.length > 3 && (
            <p className="text-xs text-gray-400">
              ...及其他 {data.currently_processing.length - 3} 篇
            </p>
          )}
        </div>
      )}
    </div>
  );
}
