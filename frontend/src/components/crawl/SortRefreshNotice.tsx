import { useState } from 'react';

const STORAGE_KEY = 'paper_search_sort_notice_dismissed';

interface Props {
  visible: boolean;
  onClose: () => void;
}

export function isSortNoticeDismissed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

export default function SortRefreshNotice({ visible, onClose }: Props) {
  const [dontShowAgain, setDontShowAgain] = useState(false);

  const handleClose = () => {
    if (dontShowAgain) {
      try {
        localStorage.setItem(STORAGE_KEY, '1');
      } catch {}
    }
    onClose();
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
      <div className="bg-white rounded-xl shadow-lg p-6 max-w-sm w-full mx-4">
        <p className="text-sm text-gray-700 mb-4">
          爬取完成！如果排序显示有误，请刷新页面重试。
        </p>
        <label className="flex items-center gap-2 text-xs text-gray-500 mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={dontShowAgain}
            onChange={(e) => setDontShowAgain(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          不再提醒
        </label>
        <button
          onClick={handleClose}
          className="w-full py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors"
        >
          知道了
        </button>
      </div>
    </div>
  );
}
