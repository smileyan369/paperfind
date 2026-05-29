interface Props {
  crawling: boolean;
  onClick: () => void;
  onCancel?: () => void;
}

export default function CrawlButton({ crawling, onClick, onCancel }: Props) {
  if (crawling) {
    return (
      <button
        onClick={onCancel}
        className="px-4 py-2 rounded-lg bg-rose-600 text-white text-sm font-medium hover:bg-rose-700 transition-colors"
      >
        <span className="flex items-center gap-2">
          <span className="animate-spin inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
          取消检索
        </span>
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
    >
      立即爬取
    </button>
  );
}
