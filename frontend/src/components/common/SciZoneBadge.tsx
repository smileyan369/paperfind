const zoneConfig: Record<string, { label: string; className: string }> = {
  Q1: { label: 'SCI Q1', className: 'bg-green-50 text-green-700 border-green-200' },
  Q2: { label: 'SCI Q2', className: 'bg-blue-50 text-blue-700 border-blue-200' },
  Q3: { label: 'SCI Q3', className: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  Q4: { label: 'SCI Q4', className: 'bg-red-50 text-red-700 border-red-200' },
};

interface Props {
  zone: string | null;
  showMissing?: boolean;
}

export default function SciZoneBadge({ zone, showMissing = false }: Props) {
  if (zone) {
    const cfg = zoneConfig[zone] || { label: zone, className: 'bg-gray-50 text-gray-600 border-gray-200' };
    return (
      <span
        className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium border ${cfg.className}`}
        title={`JCR ${zone}`}
      >
        {cfg.label}
      </span>
    );
  }

  if (showMissing) {
    return (
      <span
        className="inline-flex items-center px-1.5 py-0.5 rounded text-xs text-gray-400 bg-gray-50 border border-gray-100"
        title="非SCI期刊或会议论文"
      >
        未收录
      </span>
    );
  }

  return null;
}
