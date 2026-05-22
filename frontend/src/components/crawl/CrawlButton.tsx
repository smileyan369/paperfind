interface Props {
  crawling: boolean;
  onClick: () => void;
}

export default function CrawlButton({ crawling, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      disabled={crawling}
      className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
    >
      {crawling ? (
        <span className="flex items-center gap-2">
          <span className="animate-spin inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
          爬取中...
        </span>
      ) : (
        '立即爬取'
      )}
    </button>
  );
}
