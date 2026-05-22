import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

interface Props {
  icon?: string;
  title?: string;
  description?: string;
  action?: ReactNode;
}

export default function EmptyState({
  icon = '📄',
  title = '暂无数据',
  description = '还没有内容，请先添加关键词并触发爬取',
  action,
}: Props) {
  const navigate = useNavigate();
  return (
    <div className="flex items-center justify-center py-16">
      <div className="text-center">
        <div className="text-4xl mb-3">{icon}</div>
        <h3 className="text-lg font-medium text-gray-700 mb-1">{title}</h3>
        <p className="text-gray-400 mb-4">{description}</p>
        {action !== undefined ? action : (
          <button
            onClick={() => navigate('/keywords')}
            className="text-sm px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            去添加关键词
          </button>
        )}
      </div>
    </div>
  );
}
