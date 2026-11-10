"use client";

const PRIMARY_BTN =
  "inline-flex min-h-[40px] items-center justify-center rounded-xl bg-slate-900 px-4 text-sm font-medium text-white transition active:scale-95 dark:bg-white dark:text-slate-900";

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-2xl border border-rose-200 bg-rose-50/60 px-5 py-10 text-center dark:border-rose-500/20 dark:bg-rose-500/5">
      <div className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-rose-100 text-rose-600 dark:bg-rose-500/15 dark:text-rose-300">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" className="h-5 w-5" aria-hidden="true">
          <path d="M12 8v5M12 17h.01" />
          <circle cx="12" cy="12" r="9" />
        </svg>
      </div>
      <h2 className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-100">文献加载失败</h2>
      <p className="mx-auto mt-1.5 max-w-xs break-words text-xs leading-relaxed text-slate-600 dark:text-slate-400">
        {message}
      </p>
      <button type="button" onClick={onRetry} className={`${PRIMARY_BTN} mt-4`}>
        重新加载
      </button>
    </div>
  );
}

export function EmptyState({ onSettings }: { onSettings: () => void }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-5 py-12 text-center dark:border-slate-700 dark:bg-slate-900/50">
      <div className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5" aria-hidden="true">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" />
        </svg>
      </div>
      <h2 className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-100">
        当前检索词下暂无匹配文献
      </h2>
      <p className="mx-auto mt-1.5 max-w-xs text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        可以换一个更宽泛的英文检索式，或切到「精选推荐」查看该主题的经典高被引论文。
      </p>
      <button type="button" onClick={onSettings} className={`${PRIMARY_BTN} mt-4`}>
        修改检索词
      </button>
    </div>
  );
}
