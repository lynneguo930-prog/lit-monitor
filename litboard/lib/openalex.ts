import type { OpenAlexWork, Paper, Topic, View } from "./types";

const API = "https://api.openalex.org/works";
const SELECT_FIELDS = [
  "id",
  "doi",
  "title",
  "publication_year",
  "publication_date",
  "cited_by_count",
  "authorships",
  "primary_location",
  "abstract_inverted_index",
].join(",");

/** 泛词不计入相关度，否则任意基因组学论文都能蒙混过关 */
const STOP_WORDS = new Set([
  "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
  "into", "using", "based", "gene", "genes", "genome", "genomic", "genomics",
  "plant", "plants", "study", "studies", "analysis", "review", "novel",
  "its", "their", "via", "near", "associated",
]);

export const DEFAULT_TOPIC: Topic = {
  label:
    (process.env.NEXT_PUBLIC_DEFAULT_TOPIC_LABEL || "植物结构变异附近的抗病基因（番茄为主）").trim(),
  query:
    (process.env.NEXT_PUBLIC_DEFAULT_TOPIC_QUERY ||
      "tomato structural variation disease resistance gene").trim(),
};

function isoDaysAgo(days: number): string {
  return new Date(Date.now() - days * 86_400_000).toISOString().slice(0, 10);
}

/** 构造 OpenAlex 请求 URL。浏览器直连，已确认 API 返回 Access-Control-Allow-Origin: * */
export function buildOpenAlexUrl(query: string, view: View): string {
  const params = new URLSearchParams({
    search: query,
    "per-page": "100",
    select: SELECT_FIELDS,
  });

  const mailto = (process.env.NEXT_PUBLIC_OPENALEX_MAILTO || "").trim();
  if (mailto) params.set("mailto", mailto);

  if (view === "latest") {
    // 近 1 年，用 OpenAlex 默认相关度召回，再在本地按 publication_date 降序。
    // 实测：服务端 sort=publication_date:desc 会把大量无关论文排到最前面。
    params.set(
      "filter",
      `from_publication_date:${isoDaysAgo(365)},to_publication_date:${isoDaysAgo(0)}`,
    );
  } else {
    // 被引 > 10 + 近 6 年 + 相关度召回，保证无新文献时主页依然有内容
    params.set(
      "filter",
      `cited_by_count:>10,from_publication_date:${isoDaysAgo(365 * 6)},to_publication_date:${isoDaysAgo(0)}`,
    );
  }
  return `${API}?${params.toString()}`;
}

export function topicTokens(query: string): string[] {
  return Array.from(
    new Set(
      query
        .toLowerCase()
        .split(/[^a-z0-9-]+/)
        .filter((w) => w.length >= 3 && !STOP_WORDS.has(w)),
    ),
  );
}

/** OpenAlex 摘要以倒排索引返回，需按词位置还原 */
export function reconstructAbstract(
  inv: Record<string, number[]> | null | undefined,
): string {
  if (!inv || typeof inv !== "object") return "";
  const positions: Array<[number, string]> = [];
  for (const [word, indexes] of Object.entries(inv)) {
    if (!Array.isArray(indexes)) continue;
    for (const pos of indexes) {
      if (Number.isInteger(pos)) positions.push([pos, word]);
    }
  }
  positions.sort((a, b) => a[0] - b[0]);
  return positions.map(([, word]) => word).join(" ").replace(/\s+/g, " ").trim();
}

function oneLineSummary(text: string, max = 140): string {
  if (!text) return "";
  const firstSentence = text.split(". ")[0] || text;
  const base = firstSentence.length >= 20 ? firstSentence : text;
  return base.length > max ? `${base.slice(0, max).trimEnd()}…` : base;
}

function safeUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  const url = value.trim();
  return /^https?:\/\//i.test(url) ? url : null;
}

function buildLink(work: OpenAlexWork): string | null {
  const doi = (work.doi || "").trim();
  if (/^https?:\/\//i.test(doi)) return doi;
  if (doi) return `https://doi.org/${doi.replace(/^doi:/i, "").replace(/^\/+/, "")}`;
  return safeUrl(work.primary_location?.landing_page_url) ?? safeUrl(work.id);
}

function countHits(tokens: string[], text: string): number {
  if (!tokens.length) return 1;
  return tokens.reduce((n, token) => n + (text.includes(token) ? 1 : 0), 0);
}

function normalize(work: OpenAlexWork, tokens: string[]): Paper {
  const abstract = reconstructAbstract(work.abstract_inverted_index);
  const names = (work.authorships ?? [])
    .map((item) => item?.author?.display_name?.trim())
    .filter((name): name is string => Boolean(name));
  const authors = names.length
    ? names.length > 4
      ? `${names.slice(0, 4).join(", ")} 等 ${names.length} 人`
      : names.join(", ")
    : "作者未标注";

  return {
    id: work.id,
    title: work.title?.trim() || "（无标题）",
    authors,
    year: work.publication_year
      ? String(work.publication_year)
      : (work.publication_date || "").slice(0, 4) || "—",
    date: work.publication_date || "",
    venue: work.primary_location?.source?.display_name?.trim() || "来源未标注",
    cites: work.cited_by_count ?? 0,
    summary: oneLineSummary(abstract),
    url: buildLink(work),
    doi: work.doi ?? null,
    relevance: countHits(tokens, `${work.title ?? ""} ${abstract}`.toLowerCase()),
  };
}

export async function fetchPapers(
  query: string,
  view: View,
  signal?: AbortSignal,
): Promise<Paper[]> {
  const q = query.trim();
  if (!q) throw new Error("检索词为空，请在设置中填写关键词");

  const response = await fetch(buildOpenAlexUrl(q, view), {
    signal,
    headers: { Accept: "application/json" },
  });

  if (response.status === 429) {
    throw new Error("OpenAlex 请求过于频繁（429），请稍后重试，或配置礼貌池邮箱");
  }
  if (!response.ok) throw new Error(`OpenAlex 请求失败（HTTP ${response.status}）`);

  let data: { results?: OpenAlexWork[] };
  try {
    data = (await response.json()) as { results?: OpenAlexWork[] };
  } catch {
    throw new Error("OpenAlex 返回内容无法解析");
  }
  if (!Array.isArray(data.results)) throw new Error("OpenAlex 返回结构异常");

  const tokens = topicTokens(q);
  const threshold = tokens.length >= 3 ? 2 : 1;
  const list = data.results
    .filter((work) => work && typeof work === "object" && typeof work.id === "string")
    .map((work) => normalize(work, tokens))
    .filter((paper) => paper.relevance >= threshold && paper.url);

  if (view === "latest") {
    list.sort(
      (a, b) => (b.date || "").localeCompare(a.date || "") || b.cites - a.cites,
    );
  } else {
    const now = Date.now();
    const score = (p: Paper) => {
      const ageDays = p.date
        ? Math.max(0, (now - new Date(p.date).getTime()) / 86_400_000)
        : 3650;
      const recency = Math.max(0, 12 - ageDays / 180);
      const tomato = /tomato|lycopersic/i.test(`${p.title} ${p.summary}`) ? 6 : 0;
      return Math.log10(p.cites + 1) * 8 + recency + p.relevance * 3 + tomato;
    };
    list.sort((a, b) => score(b) - score(a));
  }

  return list.slice(0, 24);
}
