"use client";

import type { Topic, UpdateInfo } from "@/lib/types";

interface Props {
  topic: Topic;
  update: UpdateInfo | null;
  loading: boolean;
  onSettings: () => void;
  onRefresh: () => void;
}

const ICON_BTN =
  "grid h-9 w-9 place-items-center rounded-xl border border-slate-200 bg-white/80 text-slate-500 transition active:scale-95 hover:text-slate-900 " +
  "dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-400 dark:hover:text-white";

export default function Header({ topic, update, loading, onSettings, onRefresh }: Props) {
  const newCount = update?.count ?? 0;
  const statusText = !update
    ? "正在同步文献…"
    : newCount > 0
      ? `更新了 ${newCount} 篇文献`
      : "今日已是最新";
  const isNew = newCount > 0;

  return (
    <header className="pt-safe sticky top-0 z-20 border-b border-slate-200/80 bg-slate-50/85 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/85">
      <div className="px-4 pb-3 pt-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-slate-900 text-xs font-bold text-white dark:bg-white dark:text-slate-900">
                文
              </span>
              <h1 className="truncate text-base font-semibold tracking-tight">文献看板</h1>
            </div>

            <p className="mt-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
              当前监控主题
            </p>
            <p className="mt-0.5 text-sm font-medium leading-snug text-slate-800 dark:text-slate-100">
              {topic.label}
            </p>
            <p
              className="mt-1 truncate font-mono text-[11px] text-slate-500 dark:text-slate-400"
              title={topic.query}
            >
              {topic.query}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
              className={`${ICON_BTN} disabled:opacity-40`}
              aria-label="重新同步"
              title="重新同步"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
                <path d="M21 12a9 9 0 1 1-2.64-6.36" />
                <path d="M21 3v6h-6" />
              </svg>
            </button>
            <button type="button" onClick={onSettings} className={ICON_BTN} aria-label="检索词设置" title="检索词设置">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" className="h-4 w-4" aria-hidden="true">
                <path d="M4 7h16M4 12h16M4 17h16" />
                <circle cx="9" cy="7" r="2" fill="currentColor" stroke="none" />
                <circle cx="15" cy="12" r="2" fill="currentColor" stroke="none" />
                <circle cx="8" cy="17" r="2" fill="currentColor" stroke="none" />
              </svg>
            </button>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
              isNew
                ? "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300"
                : "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
            }`}
            role="status"
            aria-live="polite"
          >
            <span className={`h-1.5 w-1.5 rounded-full ${isNew ? "bg-rose-500" : "bg-emerald-500"}`} />
            {statusText}
          </span>
          {update && (
            <span className="text-[11px] text-slate-400">
              近 7 天 {update.recent} 篇 · 本次 {update.total} 篇
            </span>
          )}
        </div>

        {update && (
          <p className="mt-1.5 text-[11px] text-slate-400">
            {update.first ? "已建立本地基线" : "相对上次查看"} · 最近同步{" "}
            {new Date(update.checkedAt).toLocaleTimeString("zh-CN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        )}
      </div>
    </header>
  );
}
