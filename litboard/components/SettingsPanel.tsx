"use client";

import { useEffect, useState } from "react";
import { DEFAULT_TOPIC } from "@/lib/openalex";
import { resetTopic } from "@/lib/storage";
import type { Topic } from "@/lib/types";

interface Props {
  initial: Topic;
  onSave: (topic: Topic) => void;
  onClose: () => void;
}

const INPUT =
  "mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200 " +
  "dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:focus:border-slate-500 dark:focus:ring-slate-700";

export default function SettingsPanel({ initial, onSave, onClose }: Props) {
  const [label, setLabel] = useState(initial.label);
  const [query, setQuery] = useState(initial.query);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="检索词设置"
        onClick={(event) => event.stopPropagation()}
        className="pb-safe w-full max-w-2xl rounded-t-3xl bg-white p-5 shadow-2xl dark:bg-slate-900"
      >
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-slate-300 dark:bg-slate-700" />
        <h2 className="text-base font-semibold">检索词设置</h2>
        <p className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
          设置仅保存在本机 localStorage，刷新与下次打开依然生效；不会同步到其他设备。
        </p>

        <label className="mt-4 block text-xs font-medium text-slate-700 dark:text-slate-300">
          主题名称
          <input
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            maxLength={80}
            placeholder="例如：植物结构变异附近的抗病基因"
            className={INPUT}
          />
        </label>

        <label className="mt-3 block text-xs font-medium text-slate-700 dark:text-slate-300">
          OpenAlex 检索式（建议英文）
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            maxLength={200}
            placeholder="tomato structural variation disease resistance gene"
            className={`${INPUT} font-mono text-xs`}
          />
        </label>
        <p className="mt-1.5 text-[11px] leading-relaxed text-slate-400">
          多词检索由 OpenAlex 做相关度召回；页面会过滤掉与检索词几乎无关的论文。
        </p>

        <div className="mt-5 flex gap-2">
          <button
            type="button"
            onClick={() => {
              resetTopic();
              setLabel(DEFAULT_TOPIC.label);
              setQuery(DEFAULT_TOPIC.query);
            }}
            className="min-h-[44px] flex-1 rounded-xl border border-slate-200 text-sm font-medium text-slate-600 transition active:scale-95 dark:border-slate-700 dark:text-slate-300"
          >
            恢复默认
          </button>
          <button
            type="button"
            onClick={() =>
              onSave({
                label: label.trim() || DEFAULT_TOPIC.label,
                query: query.trim() || DEFAULT_TOPIC.query,
              })
            }
            className="min-h-[44px] flex-[1.4] rounded-xl bg-slate-900 text-sm font-medium text-white transition active:scale-95 dark:bg-white dark:text-slate-900"
          >
            保存并刷新
          </button>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="mt-2 min-h-[36px] w-full text-xs text-slate-400"
        >
          取消
        </button>
      </div>
    </div>
  );
}
