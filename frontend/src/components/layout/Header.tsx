import { Link, useLocation } from 'react-router-dom';
import { useGlobalCrawl } from '../../contexts/CrawlContext';

export default function Header() {
  const location = useLocation();
  const { crawling, crawlMessage, crawlProgress } = useGlobalCrawl();
  const tabs = [
    { path: '/', label: '论文工作台' },
    { path: '/keywords', label: '关键词管理' },
    { path: '/settings', label: '设置' },
  ];

  return (
    <header className="sticky top-0 z-30 border-b border-white/60 bg-white/72 backdrop-blur-xl select-none">
      <div className="max-w-7xl mx-auto px-5 flex items-center justify-between h-16">
        <Link to="/" className="flex items-center gap-3 min-w-44">
          <img src="/favicon.png" className="w-9 h-9 rounded-xl shadow-sm" alt="" draggable={false} />
          <div>
            <div className="text-base font-bold text-slate-900 leading-tight">论文搜搜</div>
            <div className="text-[10px] uppercase tracking-[0.22em] text-indigo-500">Research Agent</div>
          </div>
        </Link>

        <nav className="flex gap-1 bg-slate-100/70 p-1 rounded-xl border border-white/70">
          {tabs.map(t => (
            <Link
              key={t.path}
              to={t.path}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                location.pathname === t.path
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/70'
              }`}
            >
              {t.label}
            </Link>
          ))}
        </nav>

        <div className="w-64 flex items-center justify-end">
          {crawlMessage && (
            <div className="w-full max-w-64 soft-appear">
              <div className="text-xs text-indigo-700 bg-white/80 border border-indigo-100 px-2.5 py-1.5 rounded-full flex items-center justify-between gap-2 shadow-sm">
                <span className="flex items-center gap-1.5 min-w-0">
                  {crawling && (
                    <span className="inline-block w-3 h-3 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin shrink-0" />
                  )}
                  <span className="truncate">{crawlMessage}</span>
                </span>
                {crawling && <span className="tabular-nums shrink-0">{Math.round(crawlProgress)}%</span>}
              </div>
              {crawling && (
                <div className="mt-1.5 h-1.5 rounded-full bg-white/80 overflow-hidden border border-white/70">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500 transition-all duration-500 progress-glow"
                    style={{ width: `${Math.max(0, Math.min(100, crawlProgress))}%` }}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
