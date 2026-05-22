const STATUS_MAP: Record<string, string> = {
  running: 'bg-blue-100 text-blue-700',
  success: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  partial: 'bg-yellow-100 text-yellow-700',
};

interface Props {
  status: string;
}

export default function CrawlStatusBadge({ status }: Props) {
  const color = STATUS_MAP[status] || 'bg-gray-100 text-gray-600';
  const label: Record<string, string> = {
    running: '运行中',
    success: '成功',
    failed: '失败',
    partial: '部分成功',
  };

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>
      {label[status] || status}
    </span>
  );
}
