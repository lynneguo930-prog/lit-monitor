"use client";

import type { View } from "@/lib/types";

interface Props {
  view: View;
  onChange: (view: View) => void;
  disabled?: boolean;
}

const TABS: Array<{ key: View; label: string; hint: string }> = [
  { key: "latest", label: "最新发表", hint: "按日期" },
  { key: "curated", label: "精选推荐", hint: "被引 · 综合" },
];

export default function TabBar({ view, onChange, disabled = false }: Props) {
  return (
    <div className="px-4 pb-1 pt-3">
      <div
        role="tablist"
        aria-label="文献排序方式"
        className="flex rounded-xl bg-slate-200/70 p-1 dark:bg-slate-800/70"
      >
        {TABS.map((tab) => {
          const active = view === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={active}
              disabled={disabled}
              onClick={() => onChange(tab.key)}
              className={`flex-1 rounded-lg px-2 py-2 text-sm font-medium transition disabled:opacity-60 ${
                active
                  ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white"
                  : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              {tab.label}
              <span className="ml-1.5 align-middle text-[10px] font-normal opacity-60">
                {tab.hint}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
