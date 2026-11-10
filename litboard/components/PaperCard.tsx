"use client";

import type { Paper } from "@/lib/types";

interface Props {
  paper: Paper;
  rank: number;
}

export default function PaperCard({ paper, rank }: Props) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition active:scale-[0.995] dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md bg-slate-100 text-[11px] font-semibold tabular-nums text-slate-500 dark:bg-slate-800 dark:text-slate-400">
          {rank}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-[15px] font-semibold leading-snug tracking-tight text-slate-900 dark:text-slate-50">
            {paper.url ? (
              <a
                href={paper.url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline-offset-2 hover:underline"
              >
                {paper.title}
              </a>
            ) : (
              paper.title
            )}
          </h2>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
            {paper.authors}
          </p>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-500">
            <span className="font-semibold tabular-nums text-slate-700 dark:text-slate-300">
              {paper.year}
            </span>
            <span className="text-slate-300 dark:text-slate-600">·</span>
            <span className="truncate">{paper.venue}</span>
          </p>
        </div>
      </div>

      {paper.summary && (
        <p className="mt-3 line-clamp-2 rounded-lg bg-slate-50 px-3 py-2 text-[13px] leading-relaxed text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
          {paper.summary}
        </p>
      )}

      <div className="mt-3 flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-medium tabular-nums text-amber-700 dark:bg-amber-400/10 dark:text-amber-300">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3" aria-hidden="true">
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
          </svg>
          被引 {paper.cites.toLocaleString("zh-CN")}
        </span>

        {paper.url && (
          <a
            href={paper.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-[36px] items-center gap-1 rounded-lg px-2 text-xs font-medium text-blue-600 active:bg-blue-50 dark:text-blue-400 dark:active:bg-blue-500/10"
          >
            {paper.doi ? "DOI 原文" : "查看原文"}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5" aria-hidden="true">
              <path d="M15 3h6v6" />
              <path d="M10 14 21 3" />
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            </svg>
          </a>
        )}
      </div>
    </article>
  );
}
