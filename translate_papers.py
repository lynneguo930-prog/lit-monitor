#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 papers_cache.json 中的文献批量生成中文题名与中文摘要。

翻译通道：MyMemory 公共接口 (en -> zh-CN)。标题与摘要用 ||| 合并成一次请求，
缩写术语用占位符保护。结果缓存到 translations.json，支持断点续跑。

用法:
    python translate_papers.py              # 翻译所有未缓存条目
    python translate_papers.py --limit 10   # 只翻 10 条（试跑）
    python translate_papers.py --reset      # 清空缓存重新翻译
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import generate_archive as ga

ROOT = Path(__file__).resolve().parent
PAPERS = ROOT / "papers_cache.json"
OUTPUT = ROOT / "translations.json"
ENDPOINT = "https://api.mymemory.translated.net/get"
MAILTO = "lynneguo930@gmail.com"  # 仅作 MyMemory 配额标识，与 OpenAlex 礼貌池同一邮箱
SEP = "|||"
MAX_TITLE = 200
MAX_ABSTRACT = 240
SAVE_EVERY = 10
PAUSE = 0.15

# 纯缩写/术语：译成占位符，译后原样还原，避免机翻破坏学术缩写
PROTECT = (
    "NBS-LRR", "RNA-seq", "CRISPR", "GWAS", "NLR", "QTL", "PAV", "CNV",
    "SNP", "GWAS", "R gene", "SV",
)


def abstract_snippet(work: dict) -> str:
    text = ga.abstract_text(work, 0)
    if not text:
        return ""
    text = re.sub(r"^(abstract|summary)\s*[:.\-]?\s*", "", text, flags=re.I).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    short = " ".join(sentences[:2]).strip()
    return short[:MAX_ABSTRACT].rstrip()


def protect(text: str) -> tuple[str, dict]:
    slots: dict[str, str] = {}
    for i, term in enumerate(dict.fromkeys(PROTECT)):
        token = "ZQ%dZQ" % i
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.I)
        if pattern.search(text):
            text = pattern.sub(token, text)
            slots[token] = term
    # 拉丁学名归一为 tomato，避免机翻成「茄属番茄」或保留拉丁文
    text = re.sub(r"Solanum\s+lycopersicum", "tomato", text, flags=re.I)
    text = re.sub(r"S\.\s*lycopersicum", "tomato", text, flags=re.I)
    return text, slots


def restore(text: str, slots: dict) -> str:
    for token, term in slots.items():
        number = token[2:-2]
        text = re.sub(r"ZQ\s*%s\s*ZQ" % number, term, text, flags=re.I)
    text = re.sub(r"\s*\|\|\|\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^抽象\s*", "", text)
    return re.sub(r"^(摘要|概要)\s*[:：]?\s*", "", text)


def translate(pair: list[str]) -> tuple[str, str, bool]:
    query = SEP.join(pair)
    params = {"q": query, "langpair": "en|zh-CN", "de": MAILTO}
    request = urllib.request.Request(
        ENDPOINT + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": "lit-archive-translator/1.0"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        data = json.load(response)
    if data.get("quotaFinished") or str(data.get("responseStatus")) != "200":
        raise RuntimeError(
            "配额/状态异常: status=%s details=%s"
            % (data.get("responseStatus"), data.get("responseDetails"))
        )
    translated = (data.get("responseData") or {}).get("translatedText") or ""
    pieces = re.split(r"\s*\|{2,}\s*", translated)
    title_zh = pieces[0].strip() if pieces else ""
    abstract_zh = " ".join(p.strip() for p in pieces[1:] if p.strip())
    return title_zh, abstract_zh, len(pieces) >= 2


def load_cache(reset: bool) -> dict:
    if reset or not OUTPUT.exists():
        return {"updated_at": "", "items": {}}
    try:
        data = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if isinstance(data.get("items"), dict):
            return data
    except (OSError, ValueError) as exc:
        print("[WARN] 缓存读取失败，重新开始: %s" % exc)
    return {"updated_at": "", "items": {}}


def save_cache(cache: dict) -> None:
    cache["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    OUTPUT.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def repair(works: list[dict], cache: dict) -> int:
    """补翻：合并请求中分隔符丢失、但原文确有摘要的条目，改为单段请求。"""
    by_id = {ga.canonical_id(w): w for w in works}
    todo = [
        cid for cid, item in cache["items"].items()
        if not item.get("abstract_zh") and ga.abstract_text(by_id.get(cid, {}), 0)
    ]
    print("补翻摘要 %d 篇" % len(todo))
    ok = 0
    for cid in todo:
        protected, slots = protect(abstract_snippet(by_id[cid]))
        try:
            zh, _, _ = translate([protected])
            zh = restore(zh, slots)
            if zh:
                cache["items"][cid]["abstract_zh"] = zh
                ok += 1
        except Exception as exc:
            print("  [FAIL] %s -> %s" % (cid[:38], str(exc)[:90]))
        time.sleep(PAUSE)
    save_cache(cache)
    print("补翻完成 %d/%d" % (ok, len(todo)))
    return 0


def main() -> int:
    if not PAPERS.exists():
        print("[FAIL] 缺少 papers_cache.json，请先运行: python generate_archive.py")
        return 1
    works = json.loads(PAPERS.read_text(encoding="utf-8"))["works"]
    cache = load_cache("--reset" in sys.argv[1:])
    if "--repair" in sys.argv[1:]:
        return repair(works, cache)
    limit = None
    if "--limit" in sys.argv[1:]:
        try:
            limit = int(sys.argv[sys.argv.index("--limit") + 1])
        except (ValueError, IndexError):
            print("[FAIL] --limit 需要整数")
            return 1

    todo = [w for w in works if ga.canonical_id(w) not in cache["items"]]
    if limit:
        todo = todo[:limit]
    print("文献 %d 篇 | 已缓存 %d 篇 | 本次待翻 %d 篇" %
          (len(works), len(cache["items"]), len(todo)))

    ok = failed = 0
    for i, work in enumerate(todo, 1):
        cid = ga.canonical_id(work)
        en_title = str(work.get("title") or "").strip()[:MAX_TITLE]
        en_abstract = abstract_snippet(work)
        if not en_title:
            continue
        p_title, s_title = protect(en_title)
        p_abstract, s_abstract = protect(en_abstract)
        try:
            zh_title, zh_abstract, sep_ok = translate([p_title, p_abstract])
            if not zh_title:
                raise ValueError("空译文")
            cache["items"][cid] = {
                "title_zh": restore(zh_title, s_title),
                "abstract_zh": restore(zh_abstract, s_abstract) if (en_abstract and sep_ok) else "",
            }
            ok += 1
        except Exception as exc:
            failed += 1
            print("  [FAIL] #%d %s" % (i, str(exc)[:110]))
            if "配额" in str(exc):
                print("  [STOP] 达到每日配额，已完成部分已保存，明天重跑可续翻")
                break
        if i % SAVE_EVERY == 0:
            save_cache(cache)
            print("  进度 %d/%d | 成功 %d | 失败 %d" % (i, len(todo), ok, failed))
        time.sleep(PAUSE)

    save_cache(cache)
    print("完成: 成功 %d / 失败 %d / 缓存累计 %d 篇 -> %s" %
          (ok, failed, len(cache["items"]), OUTPUT))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
