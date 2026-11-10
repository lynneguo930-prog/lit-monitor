"use client";

import { useCallback, useEffect, useState } from "react";
import Header from "@/components/Header";
import TabBar from "@/components/TabBar";
import PaperCard from "@/components/PaperCard";
import SkeletonCard from "@/components/SkeletonCard";
import SettingsPanel from "@/components/SettingsPanel";
import { EmptyState, ErrorState } from "@/components/StateViews";
import { DEFAULT_TOPIC, fetchPapers } from "@/lib/openalex";
import {
  loadBaseline,
  loadTab,
  loadTopic,
  saveBaseline,
  saveTab,
  saveTopic,
} from "@/lib/storage";
import type { Paper, Topic, UpdateInfo, View } from "@/lib/types";

type LoadState = "loading" | "ready" | "error";

export default function Home() {
  // 首屏 SSR 与客户端都从 DEFAULT_TOPIC 渲染，挂载后再读 localStorage，避免 hydration 不一致
  const [hydrated, setHydrated] = useState(false);
  const [topic, setTopic] = useState<Topic>(DEFAULT_TOPIC);
  const [view, setView] = useState<View>("latest");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState("");
  const [update, setUpdate] = useState<UpdateInfo | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    setTopic(loadTopic());
    setView(loadTab());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) saveTab(view);
  }, [hydrated, view]);

  const refresh = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    if (!hydrated) return;
    const controller = new AbortController();
    let active = true;

    setState("loading");
    setError("");

    fetchPapers(topic.query, view, controller.signal)
      .then((list) => {
        if (!active) return;

        const baselineKey = `${topic.query}::${view}`;
        const baseline = loadBaseline(baselineKey);
        const known = new Set(baseline?.ids ?? []);
        const fresh = list.filter((paper) => !known.has(paper.id)).length;
        const weekAgo = new Date(Date.now() - 7 * 86_400_000)
          .toISOString()
          .slice(0, 10);
        const recent = list.filter((paper) => paper.date && paper.date >= weekAgo).length;

        setPapers(list);
        setUpdate({
          count: baseline ? fresh : 0,
          first: !baseline,
          recent,
          total: list.length,
          checkedAt: Date.now(),
        });
        saveBaseline(
          baselineKey,
          Array.from(new Set([...(baseline?.ids ?? []), ...list.map((p) => p.id)])).slice(-800),
        );
        setState("ready");
      })
      .catch((cause: unknown) => {
        if (!active || controller.signal.aborted) return;
        setError(cause instanceof Error ? cause.message : "未知错误");
        setState("error");
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [hydrated, topic.query, view, nonce]);

  const handleSaveTopic = (next: Topic) => {
    saveTopic(next);
    setTopic(next);
    setSettingsOpen(false);
  };

  return (
    <main className="pb-safe mx-auto w-full max-w-3xl">
      <div className="pl-safe pr-safe">
        <Header
          topic={topic}
          update={update}
          loading={state === "loading"}
          onSettings={() => setSettingsOpen(true)}
          onRefresh={refresh}
        />

        <TabBar view={view} onChange={setView} disabled={state === "loading" && !papers.length} />

        <section className="px-4 pb-8 pt-2" aria-live="polite" aria-busy={state === "loading"}>
          {state === "loading" && (
            <div className="space-y-3" aria-label="正在加载文献">
              {Array.from({ length: 5 }).map((_, index) => (
                <SkeletonCard key={index} />
              ))}
            </div>
          )}

          {state === "error" && <ErrorState message={error} onRetry={refresh} />}

          {state === "ready" && papers.length === 0 && (
            <EmptyState onSettings={() => setSettingsOpen(true)} />
          )}

          {state === "ready" && papers.length > 0 && (
            <>
              <p className="mb-3 px-1 text-[11px] text-slate-400">
                {view === "latest"
                  ? "按发表日期降序 · 近 1 年"
                  : "综合被引次数、时效与主题匹配度 · 近 6 年"}
                {" · "}共 {papers.length} 篇 · 数据源 OpenAlex
              </p>
              <ol className="space-y-3">
                {papers.map((paper, index) => (
                  <li key={paper.id}>
                    <PaperCard paper={paper} rank={index + 1} />
                  </li>
                ))}
              </ol>
            </>
          )}
        </section>

        <footer className="px-4 pb-6 text-center text-[11px] leading-relaxed text-slate-400">
          数据来自 OpenAlex · 检索词与更新基线保存在本机
          <br />
          添加到主屏幕后以全屏模式运行
        </footer>
      </div>

      {settingsOpen && (
        <SettingsPanel
          initial={topic}
          onSave={handleSaveTopic}
          onClose={() => setSettingsOpen(false)}
        />
      )}
    </main>
  );
}
