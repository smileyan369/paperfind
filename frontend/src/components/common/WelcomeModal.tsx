import { useState, useEffect } from 'react';

const STORAGE_KEY = 'paperfind_welcome_dismissed';

export default function WelcomeModal() {
  const [visible, setVisible] = useState(false);
  const [dontShow, setDontShow] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY) !== '1') {
      setVisible(true);
    }
  }, []);

  const handleClose = () => {
    if (dontShow) {
      localStorage.setItem(STORAGE_KEY, '1');
    }
    setVisible(false);
  };

  if (!visible) return null;

  const tips = [
    '本软件提供自动总结，但考虑到可能会消耗 token，因此烦请在设置中自行开启。',
    '可以在设置界面自行配置AI，便于在检索时使用你的AI进行总结',
    '可以在关键词检索界面输入关键词进行检索',
    '如果关键词有多个，可以以空格进行区分',
    '如果录入多组关键词，系统会默认返回至少含有其中一组关键词的论文',
    '注：关键词检索区分中英文，推荐用英文作为关键词',
    '可以在左边进行论文筛选，便于查找更适合你要求的论文',
    <>
      如需免费AI，可以尝试在网站{' '}
      <a href="https://groq.com/" target="_blank" rel="noopener noreferrer"
         className="text-indigo-600 underline hover:text-indigo-800">
        groq.com
      </a>{' '}
      获取
      <div className="text-gray-400 mt-0.5">
        URL：https://api.groq.com/openai/v1
        <br />
        Model：llama-3.1-8b-instant
      </div>
    </>,
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-indigo-600 rounded-t-xl px-6 py-5 text-center">
          <span className="text-3xl">✨</span>
          <h2 className="text-xl font-bold text-white mt-1">欢迎使用论文搜搜</h2>
        </div>

        {/* Tips */}
        <div className="px-6 py-5 space-y-3">
          {tips.map((tip, i) => (
            <div key={i} className="flex items-start gap-3">
              <span className="mt-0.5 w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 text-xs flex items-center justify-center shrink-0 font-bold">
                {i + 1}
              </span>
              <span className="text-sm text-gray-600 leading-relaxed">{tip}</span>
            </div>
          ))}
        </div>

        {/* Author */}
        <p className="text-center text-xs text-gray-400 pb-3">by：星海无言</p>

        {/* Footer */}
        <div className="border-t px-6 py-3 flex items-center justify-between">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={dontShow}
              onChange={e => setDontShow(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm text-gray-500">不再提示</span>
          </label>
          <button
            onClick={handleClose}
            className="px-5 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors font-medium"
          >
            开始使用
          </button>
        </div>
      </div>
    </div>
  );
}
