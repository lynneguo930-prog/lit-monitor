export type View = "latest" | "curated";

export interface Topic {
  /** 中文展示名，仅用于 UI */
  label: string;
  /** 传给 OpenAlex search 的英文检索式 */
  query: string;
}

/** OpenAlex /works 中我们 select 的字段（其余字段忽略） */
export interface OpenAlexWork {
  id: string;
  doi: string | null;
  title: string | null;
  publication_year: number | null;
  publication_date: string | null;
  cited_by_count: number | null;
  authorships: Array<{ author?: { display_name?: string } }> | null;
  primary_location: {
    source?: { display_name?: string } | null;
    landing_page_url?: string | null;
  } | null;
  abstract_inverted_index: Record<string, number[]> | null;
}

/** 卡片渲染用的规范化结构 */
export interface Paper {
  id: string;
  title: string;
  authors: string;
  year: string;
  date: string;
  venue: string;
  cites: number;
  summary: string;
  url: string | null;
  doi: string | null;
  /** 命中检索词的数量，用于相关度门槛与综合排序 */
  relevance: number;
}

export interface UpdateInfo {
  /** 自上次查看以来新出现的文献数；首次访问为 0 */
  count: number;
  first: boolean;
  /** 近 7 天发表的篇数 */
  recent: number;
  total: number;
  checkedAt: number;
}
