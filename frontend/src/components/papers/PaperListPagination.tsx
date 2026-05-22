interface Props {
  page: number;
  total: number;
  pageSize?: number;
  onChange: (page: number) => void;
}

export default function PaperListPagination({ page, total, pageSize = 24, onChange }: Props) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  if (total === 0) return null;

  const pages: number[] = [];
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, page + 2);
  for (let i = start; i <= end; i++) pages.push(i);

  return (
    <div className="flex items-center justify-between mt-8">
      <span className="text-xs text-gray-400">{from}-{to} / {total} 篇</span>
      <div className="flex items-center gap-1">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="px-3 py-1.5 text-sm rounded-md border disabled:opacity-30 hover:bg-gray-50"
      >
        上一页
      </button>
      {start > 1 && (
        <>
          <button
            onClick={() => onChange(1)}
            className="px-3 py-1.5 text-sm rounded-md border hover:bg-gray-50"
          >1</button>
          {start > 2 && <span className="px-1 text-gray-400">...</span>}
        </>
      )}
      {pages.map(p => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={`px-3 py-1.5 text-sm rounded-md border ${
            p === page ? 'bg-indigo-600 text-white border-indigo-600' : 'hover:bg-gray-50'
          }`}
        >
          {p}
        </button>
      ))}
      {end < totalPages && (
        <>
          {end < totalPages - 1 && <span className="px-1 text-gray-400">...</span>}
          <button
            onClick={() => onChange(totalPages)}
            className="px-3 py-1.5 text-sm rounded-md border hover:bg-gray-50"
          >{totalPages}</button>
        </>
      )}
      <button
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        className="px-3 py-1.5 text-sm rounded-md border disabled:opacity-30 hover:bg-gray-50"
      >
        下一页
      </button>
      </div>
    </div>
  );
}
