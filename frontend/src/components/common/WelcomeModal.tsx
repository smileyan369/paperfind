import { useEffect, useState } from 'react';

const STORAGE_KEY = 'paperfind_welcome_dismissed';

export default function WelcomeModal() {
  const [visible, setVisible] = useState(false);
  const [dontShow, setDontShow] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY) !== '1') setVisible(true);
  }, []);

  const handleClose = () => {
    if (dontShow) localStorage.setItem(STORAGE_KEY, '1');
    setVisible(false);
  };

  if (!visible) return null;

  const tips = [
    '本软件提供自动总结，但考虑到可能会消耗 token，因此烦请在设置中自行开启。',
    '建议先填写研究方向档案，AI 导读会结合你的方向判断论文是否值得优先阅读。',
    '可以用自然语言生成检索词，再一键加入关键词追踪。',
    '部分论文来源在国内可能需要代理或网络环境支持，系统会跳过不可达来源。',
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm">
      <div className="glass-panel rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden soft-appear">
        <div className="px-6 py-5 bg-gradient-to-r from-indigo-600 to-cyan-500 text-white flex items-center gap-4">
          <img src="/favicon.png" className="w-14 h-14 rounded-2xl bg-white/20" alt="" />
          <div>
            <h2 className="text-xl font-bold">欢迎使用论文搜搜</h2>
            <p className="text-sm text-white/80 mt-1">本地科研论文 Agent，帮你检索、导读和沉淀论文。</p>
          </div>
        </div>

        <div className="px-6 py-5 space-y-3">
          {tips.map((tip, i) => (
            <div key={tip} className="flex items-start gap-3">
              <span className="mt-0.5 w-6 h-6 rounded-full bg-indigo-50 text-indigo-700 text-xs flex items-center justify-center shrink-0 font-bold">
                {i + 1}
              </span>
              <span className="text-sm text-slate-600 leading-relaxed">{tip}</span>
            </div>
          ))}
        </div>

        <div className="border-t border-slate-100 px-6 py-3 flex items-center justify-between bg-white/70">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={dontShow}
              onChange={e => setDontShow(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm text-slate-500">不再提示</span>
          </label>
          <button onClick={handleClose} className="premium-button px-5 py-2 text-white text-sm rounded-xl font-medium">
            开始使用
          </button>
        </div>
      </div>
    </div>
  );
}
