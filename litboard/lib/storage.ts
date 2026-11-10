import { DEFAULT_TOPIC } from "./openalex";
import type { Topic, View } from "./types";

const TOPIC_KEY = "litboard:topic:v1";
const TAB_KEY = "litboard:tab:v1";
const BASELINE_PREFIX = "litboard:baseline:v1:";

export interface Baseline {
  ids: string[];
  checkedAt: number;
}

function read<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Safari 无痕模式 / 存储配额不足时静默降级，不影响主流程
  }
}

export function loadTopic(): Topic {
  const stored = read<Partial<Topic>>(TOPIC_KEY);
  return {
    label:
      typeof stored?.label === "string" && stored.label.trim()
        ? stored.label.trim().slice(0, 80)
        : DEFAULT_TOPIC.label,
    query:
      typeof stored?.query === "string" && stored.query.trim()
        ? stored.query.trim().slice(0, 200)
        : DEFAULT_TOPIC.query,
  };
}

export function saveTopic(topic: Topic): void {
  write(TOPIC_KEY, topic);
}

export function resetTopic(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(TOPIC_KEY);
  } catch {
    /* noop */
  }
}

export function loadTab(): View {
  return read<{ view?: string }>(TAB_KEY)?.view === "curated" ? "curated" : "latest";
}

export function saveTab(view: View): void {
  write(TAB_KEY, { view });
}

export function loadBaseline(key: string): Baseline | null {
  const baseline = read<Baseline>(BASELINE_PREFIX + key);
  return baseline && Array.isArray(baseline.ids) ? baseline : null;
}

export function saveBaseline(key: string, ids: string[]): void {
  write(BASELINE_PREFIX + key, { ids, checkedAt: Date.now() } satisfies Baseline);
}
