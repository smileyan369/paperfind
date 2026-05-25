import { Link, useLocation } from 'react-router-dom';
import { useGlobalCrawl } from '../../contexts/CrawlContext';

export default function Header() {
  const location = useLocation();
  const { crawling, crawlMessage, crawlProgress } = useGlobalCrawl();
  const tabs = [
    { path: '/', label: '论文浏览' },
    { path: '/keywords', label: '关键词管理' },
    { path: '/settings', label: '设置' },
  ];

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-14">
        <Link to="/" className="text-lg font-bold text-indigo-600 whitespace-nowrap">
          论文搜搜
        </Link>
        <nav className="flex gap-1">
          {tabs.map(t => (
            <Link
              key={t.path}
              to={t.path}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                location.pathname === t.path
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {t.label}
            </Link>
          ))}
        </nav>
        <div className="w-56 flex items-center justify-end">
          {crawlMessage && (
            <div className="w-full max-w-56">
              <div className="text-xs text-indigo-600 bg-indigo-50 px-2 py-1 rounded-full flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5 min-w-0">
                  {crawling && (
                    <span className="inline-block w-3 h-3 border-2 border-indigo-300 border-t-indigo-600 rounded-full animate-spin shrink-0" />
                  )}
                  <span className="truncate">{crawlMessage}</span>
                </span>
                {crawling && (
                  <span className="tabular-nums shrink-0">{Math.round(crawlProgress)}%</span>
                )}
              </div>
              {crawling && (
                <div className="mt-1 h-1 rounded-full bg-indigo-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-indigo-600 transition-all duration-500"
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
