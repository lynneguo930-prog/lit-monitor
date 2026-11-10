#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按与 openalex_lit_monitor.py 完全相同的检索式和 7 天窗口，重新查询 OpenAlex，
生成单文件全量文献归档页 papers_archive.html。

零第三方依赖；常量通过 AST 从监控脚本读取，避免两处配置漂移。
用途：邮件因 MAX_EMAIL_ITEMS 截断时，补看未展开的文献。
"""

from __future__ import annotations

import ast
import html
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "openalex_lit_monitor.py"
OUTPUT = ROOT / "papers_archive.html"
PAPERS_CACHE = ROOT / "papers_cache.json"
TRANSLATIONS = ROOT / "translations.json"
API = "https://api.openalex.org/works"
MAILTO = "lynneguo930@gmail.com"
LOOKBACK_DAYS = 7
MAX_PAGES = 5
RETRIES = 3


def load_constants() -> dict:
    wanted = {
        "DEFAULT_QUERIES", "DEFAULT_TOPIC_LABEL", "TOMATO_TERMS",
        "SV_TERMS", "RES_TERMS", "SELECT_FIELDS", "PER_PAGE",
    }
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    result: dict = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in wanted:
                result[target.id] = ast.literal_eval(node.value)
    missing = wanted - result.keys()
    if missing:
        raise RuntimeError("无法从监控脚本读取常量: %s" % sorted(missing))
    return result


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def safe_url(value) -> str:
    url = str(value if value is not None else "").strip()
    return url if url.lower().startswith(("http://", "https://")) else ""


def canonical_id(work: dict) -> str:
    doi = str(work.get("doi") or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
            break
    if doi.strip():
        return "doi:" + doi.strip()
    oa_id = str(work.get("id") or "").strip()
    return "openalex:" + oa_id.rsplit("/", 1)[-1] if oa_id else ""


def abstract_text(work: dict, limit: int = 360) -> str:
    inv = work.get("abstract_inverted_index")
    if not isinstance(inv, dict) or not inv:
        return ""
    pairs = [
        (pos, str(word))
        for word, indexes in inv.items()
        if isinstance(indexes, list)
        for pos in indexes
        if isinstance(pos, int)
    ]
    pairs.sort(key=lambda p: p[0])
    text = " ".join(w for _, w in pairs)
    text = " ".join(text.split())
    return text[:limit].rstrip() + "..." if limit > 0 and len(text) > limit else text


def authors(work: dict) -> str:
    names = [
        str(((item or {}).get("author") or {}).get("display_name") or "").strip()
        for item in (work.get("authorships") or [])
    ]
    names = [n for n in names if n]
    if not names:
        return "未知作者"
    return ", ".join(names[:6]) + (" 等（共 %d 位作者）" % len(names) if len(names) > 6 else "")


def venue(work: dict) -> str:
    loc = work.get("primary_location") or {}
    src = loc.get("source") or {}
    return str(src.get("display_name") or "").strip() or "未标注期刊/会议"


def link(work: dict) -> str:
    doi = str(work.get("doi") or "").strip()
    if doi.lower().startswith(("http://", "https://")):
        return safe_url(doi)
    if doi:
        if doi.lower().startswith("doi:"):
            doi = doi[4:]
        return "https://doi.org/" + doi.lstrip("/")
    loc = work.get("primary_location") or {}
    return safe_url(loc.get("landing_page_url")) or safe_url(work.get("id"))


def relevance(work: dict, c: dict) -> int:
    text = (str(work.get("title") or "") + " " + abstract_text(work, 0)).lower()
    score = 0
    if any(t in text for t in c["TOMATO_TERMS"]):
        score += 4
    if any(t in text for t in c["SV_TERMS"]):
        score += 2
    if any(t in text for t in c["RES_TERMS"]):
        score += 2
    return score


def fetch_query(query: str, start: str, end: str, c: dict) -> list[dict]:
    collected: dict[str, dict] = {}
    cursor = "*"
    for _ in range(MAX_PAGES):
        params = {
            "search": query,
            "filter": "from_publication_date:%s,to_publication_date:%s" % (start, end),
            "per-page": c["PER_PAGE"],
            "cursor": cursor,
            "mailto": MAILTO,
            "select": c["SELECT_FIELDS"],
        }
        request = urllib.request.Request(
            API + "?" + urllib.parse.urlencode(params),
            headers={
                "User-Agent": "openalex-lit-archive/1.0 (mailto:%s)" % MAILTO,
                "Accept": "application/json",
            },
        )
        data = None
        for attempt in range(1, RETRIES + 1):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    data = json.load(response)
                break
            except Exception as exc:
                if attempt == RETRIES:
                    raise RuntimeError("检索式 %r 请求失败: %s" % (query, exc))
                time.sleep(2 ** attempt)
        batch = [w for w in (data.get("results") or []) if isinstance(w, dict)]
        for work in batch:
            cid = canonical_id(work)
            if cid:
                collected.setdefault(cid, work)
        next_cursor = (data.get("meta") or {}).get("next_cursor")
        if not batch or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    print("  %-58s %3d 条" % (query[:58], len(collected)))
    return list(collected.values())


CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:#f8fafc;color:#0f172a;
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
 -webkit-text-size-adjust:100%}
.wrap{max-width:820px;margin:0 auto;padding:20px 14px 48px}
header{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px;margin-bottom:14px}
h1{font-size:20px;margin:0 0 8px;font-weight:600}
.meta{font-size:13px;color:#64748b;line-height:1.8;margin:0}
.note{background:#fffbeb;border:1px solid #fde68a;color:#92400e;border-radius:10px;
 padding:12px 14px;font-size:13px;line-height:1.75;margin-bottom:14px}
.toolbar{position:sticky;top:0;z-index:2;background:#f8fafc;padding:10px 0 12px}
#q{width:100%;padding:12px 14px;font-size:15px;border:1px solid #cbd5e1;border-radius:10px;
 background:#fff;outline:none}
#q:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.12)}
.filter{display:inline-flex;align-items:center;gap:7px;font-size:13px;color:#334155;
 margin:10px 2px 0;cursor:pointer}
.filter input{width:16px;height:16px;accent-color:#2563eb}
.count{font-size:12px;color:#64748b;margin:6px 2px 0}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin-bottom:10px}
.idx{display:inline-block;min-width:26px;color:#94a3b8;font-size:12px;font-weight:600}
.badge{display:inline-block;background:#eff6ff;color:#1d4ed8;border-radius:6px;
 padding:2px 7px;font-size:11px;margin-left:6px;vertical-align:middle}
h2{font-size:15px;line-height:1.55;margin:0 0 8px;font-weight:600}
h2 a{color:#1d4ed8;text-decoration:none}
h2 a:hover{text-decoration:underline}
.line{font-size:12px;color:#64748b;line-height:1.7;margin:0 0 6px}
.cite{color:#b45309;background:#fffbeb;border-radius:6px;padding:2px 7px;font-size:11px}
.abs{font-size:13px;line-height:1.75;color:#475569;margin:8px 0 0}
.abs.empty{color:#94a3b8}
.go{display:inline-block;margin-top:10px;font-size:12px;color:#1d4ed8;text-decoration:none}
.zh-title{font-size:13px;color:#0f172a;font-weight:600;line-height:1.6;margin:0 0 8px}
.zh-title.missing{color:#94a3b8;font-weight:400;font-size:12px}
.zh-tag{display:inline-block;font-size:10px;color:#64748b;background:#f1f5f9;border-radius:4px;
 padding:1px 5px;margin-right:6px;vertical-align:middle;font-weight:400}
.orig{margin:8px 0 0;font-size:12px;color:#94a3b8}
.orig summary{cursor:pointer;display:inline-block}
.orig p{font-size:12px;line-height:1.7;color:#64748b;margin:6px 0 0}
footer{text-align:center;font-size:12px;color:#94a3b8;padding:22px 0 0;line-height:1.8}
code{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px}
@media(max-width:480px){.wrap{padding:14px 10px 36px}header{padding:16px}h1{font-size:18px}}
"""

JS = """
const q = document.getElementById('q');
const rel = document.getElementById('rel');
const cards = Array.from(document.querySelectorAll('.card'));
const shown = document.getElementById('shown');
function apply() {
  const t = q.value.trim().toLowerCase();
  const onlyRel = rel.checked;
  let n = 0;
  cards.forEach(function (c) {
    const hitText = !t || c.dataset.text.indexOf(t) !== -1;
    const hitRel = !onlyRel || Number(c.dataset.rel) >= 6;
    const show = hitText && hitRel;
    c.style.display = show ? '' : 'none';
    if (show) n++;
  });
  shown.textContent = n;
}
q.addEventListener('input', apply);
rel.addEventListener('change', apply);
"""


def render(works: list[dict], c: dict, start: str, end: str,
           translations: dict) -> str:
    cards = []
    for i, work in enumerate(works, 1):
        title = esc(work.get("title") or "（无标题）")
        url = safe_url(link(work))
        date = esc(work.get("publication_date") or "未知日期")
        source = esc(venue(work))
        people = esc(authors(work))
        cites = work.get("cited_by_count")
        cites_text = esc(cites) if isinstance(cites, int) else "0"
        abstract = abstract_text(work)
        tr = translations.get(canonical_id(work)) or {}
        zh_title = str(tr.get("title_zh") or "").strip()
        zh_abstract = str(tr.get("abstract_zh") or "").strip()
        title_zh_block = (
            f'<p class="zh-title"><span class="zh-tag">中文题名</span>{esc(zh_title)}</p>'
            if zh_title else '<p class="zh-title missing">（暂无中文译名）</p>'
        )
        if zh_abstract:
            abs_block = (
                f'<p class="abs"><span class="zh-tag">中文摘要</span>{esc(zh_abstract)}</p>'
                + (f'<details class="orig"><summary>查看英文摘要原文</summary>'
                   f'<p>{esc(abstract)}</p></details>' if abstract else "")
            )
        else:
            abs_block = (
                '<p class="abs">%s</p>' % esc(abstract)
                if abstract else '<p class="abs empty">（OpenAlex 未提供摘要）</p>'
            )
        title_html = (
            '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>' % (esc(url), title)
            if url else title
        )
        link_html = (
            '<a class="go" href="%s" target="_blank" rel="noopener noreferrer">查看原文 / DOI →</a>' % esc(url)
            if url else '<span class="go" style="color:#94a3b8">暂无可用原文链接</span>'
        )
        badge = '<span class="badge">前 50 篇 · 邮件展示范围</span>' if i <= 50 else ""
        searchable = esc(
            " ".join([str(work.get("title") or ""), zh_title, authors(work), venue(work),
                      str(work.get("publication_date") or ""), abstract_text(work, 0),
                      zh_abstract]).lower()
        )
        rel = relevance(work, c)
        cards.append(
            f'<article class="card" data-text="{searchable}" data-rel="{rel}">'
            f'<h2><span class="idx">{i}.</span>{title_html}{badge}</h2>'
            f'{title_zh_block}'
            f'<p class="line">{people}</p>'
            f'<p class="line">{source} &nbsp;|&nbsp; {date} &nbsp;|&nbsp; '
            f'<span class="cite">被引 {cites_text}</span></p>'
            f'{abs_block}{link_html}</article>'
        )

    generated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    queries = "<br>".join("· " + esc(q) for q in c["DEFAULT_QUERIES"])
    return (
        '<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<title>文献全量归档 · %s</title><style>%s</style></head><body><div class="wrap">'
        % (esc(c["DEFAULT_TOPIC_LABEL"]), CSS)
        + '<header><h1>文献全量归档</h1>'
        + f'<p class="meta">监测主题：{esc(c["DEFAULT_TOPIC_LABEL"])}<br>'
        + f'发表窗口：{esc(start)} ~ {esc(end)}（最近 {LOOKBACK_DAYS} 天）<br>'
        + f'检索式：<br>{queries}<br>'
        + f'共 <strong>{len(works)}</strong> 篇 · 生成时间 {esc(generated)}（北京时间）</p></header>'
        + '<div class="note">本页用与邮件脚本<b>完全相同的检索式和日期窗口</b>重新查询 OpenAlex 得到，'
          '包含邮件中已展示和未展开的全部文献。邮件受 <code>MAX_EMAIL_ITEMS=50</code> 限制只渲染前 50 篇，'
          '其余文献仅把 ID 写入 <code>seen_ids.json</code> 去重，并未保存标题与摘要，因此这里是目前唯一能看全的地方。<br>'
          '中文题名与中文摘要由公共翻译接口生成并缓存，机翻仅供参考；点「查看英文摘要原文」可核对原文。<br>'
          '全量召回会混入少量弱相关论文，勾选「只看主题相关」可聚焦研究方向。<br>'
          '注意：OpenAlex 数据持续更新，本页与当时那封邮件可能略有出入；「前 50 篇」标记只是按相同排序规则推算的参考范围。<br>'
          '想让以后每封邮件展示更多：在 GitHub 仓库 Settings → Secrets and variables → Actions → <b>Variables</b> '
          '新增 <code>MAX_EMAIL_ITEMS</code> = <code>200</code>（仅对之后的<b>新</b>文献生效，已推送的不会补发）。</div>'
        + '<div class="toolbar"><input id="q" type="search" placeholder="搜索中文/英文标题、作者、期刊、摘要…" autocomplete="off">'
        + '<label class="filter"><input type="checkbox" id="rel">只看主题相关（番茄 / 结构变异 / 抗病基因）</label>'
        + f'<p class="count">显示 <strong id="shown">{len(works)}</strong> / {len(works)} 篇</p></div>'
        + "".join(cards)
        + '<footer>数据来源 OpenAlex · 由 generate_archive.py 生成<br>'
          '点击标题或「查看原文 / DOI」可跳转出版社页面</footer>'
        + '</div><script>' + JS + '</script></body></html>'
    )


def main() -> int:
    import sys

    c = load_constants()
    today = datetime.now(timezone.utc).date()
    start = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    end = today.isoformat()

    if "--from-cache" in sys.argv[1:] and PAPERS_CACHE.exists():
        payload = json.loads(PAPERS_CACHE.read_text(encoding="utf-8"))
        works, start, end = payload["works"], payload["start"], payload["end"]
        works.sort(key=lambda w: (relevance(w, c), str(w.get("publication_date") or "")), reverse=True)
        print("从缓存载入 %d 篇 | 窗口 %s ~ %s" % (len(works), start, end))
    else:
        print("检索窗口: %s ~ %s | 检索式 %d 条" % (start, end, len(c["DEFAULT_QUERIES"])))
        merged: dict[str, dict] = {}
        for query in c["DEFAULT_QUERIES"]:
            try:
                for work in fetch_query(query, start, end, c):
                    cid = canonical_id(work)
                    if cid:
                        merged.setdefault(cid, work)
            except Exception as exc:
                print("  [WARN] %s" % exc)
        if not merged:
            print("[FAIL] 未取到任何文献")
            return 1
        works = list(merged.values())
        works.sort(key=lambda w: (relevance(w, c), str(w.get("publication_date") or "")), reverse=True)
        PAPERS_CACHE.write_text(
            json.dumps({"start": start, "end": end, "works": works}, ensure_ascii=False),
            encoding="utf-8",
        )

    translations: dict = {}
    if TRANSLATIONS.exists():
        try:
            translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8")).get("items", {})
        except (OSError, ValueError) as exc:
            print("[WARN] 译文缓存读取失败: %s" % exc)
    hit = sum(1 for w in works if (translations.get(canonical_id(w)) or {}).get("title_zh"))
    print("中文译文命中 %d/%d 篇" % (hit, len(works)))

    OUTPUT.write_text(render(works, c, start, end, translations), encoding="utf-8")
    print("去重后共 %d 篇 -> %s (%.1f KB)" % (len(works), OUTPUT, OUTPUT.stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
