#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAlex 最新文献监控 + Resend 邮件推送（单文件脚本，Python >= 3.9）。

默认主题：植物结构变异附近的抗病基因（以番茄为主）。

必填环境变量:
    RESEND_API_KEY     Resend API Key，形如 re_xxx
    ALERT_TO_EMAILS    收件邮箱，多个用英文逗号分隔

选填环境变量:
    RESEND_FROM        发件人，默认 onboarding@resend.dev（生产需改为已验证域名）
    SEARCH_QUERIES     OpenAlex 检索式，多个用英文分号 ; 分隔；兼容旧变量 SEARCH_KEYWORDS
    TOPIC_LABEL        邮件中展示的主题名，默认「植物结构变异附近的抗病基因（番茄为主）」
    OPENALEX_MAILTO    OpenAlex 礼貌池邮箱，默认取第一个收件邮箱
    LOOKBACK_DAYS      回溯天数，默认 7
    MAX_PAGES          每个检索式的最大翻页数（每页 200 条），默认 10
    MAX_EMAIL_ITEMS    单封邮件最多展示文献数，默认 50
    SEEN_FILE          去重记录文件，默认脚本同目录 seen_ids.json
    LOG_LEVEL          日志级别，默认 INFO

退出码: 0 = 成功 / 无新增; 1 = 配置、检索或发送失败
"""

from __future__ import annotations

import html
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from string import Template
from typing import Any

try:
    import requests
    import resend
except ImportError as exc:
    print(
        "[FATAL] 缺少依赖 %s，请执行: pip install -r requirements.txt" % exc.name,
        file=sys.stderr,
    )
    sys.exit(1)


OPENALEX_WORKS_URL = "https://api.openalex.org/works"
PER_PAGE = 200
HTTP_TIMEOUT = 30
MAX_RETRIES = 3
SELECT_FIELDS = (
    "id,doi,title,publication_date,authorships,"
    "primary_location,abstract_inverted_index"
)

# 番茄为主线，兼顾泛基因组 / 结构变异 / NLR 抗病基因等表述
DEFAULT_QUERIES = (
    "tomato structural variation disease resistance gene",
    "Solanum lycopersicum pan-genome NLR resistance gene",
    "plant structural variation resistance gene cluster",
)
DEFAULT_TOPIC_LABEL = "植物结构变异附近的抗病基因（番茄为主）"

TOMATO_TERMS = ("tomato", "solanum lycopersicum", "s. lycopersicum")
SV_TERMS = (
    "structural variation", "structural variant", "presence/absence",
    "presence absence", "copy number variation", "pan-genome", "pangenome",
    "genome-wide cnv", "large inversion",
)
RES_TERMS = (
    "disease resistance", "resistance gene", "nbs-lrr", "nlr", "r gene",
    "r-protein", "pathogen", "resistance locus",
)

logger = logging.getLogger("lit-monitor")


class ConfigError(Exception):
    """配置缺失或非法。"""


@dataclass(frozen=True)
class Config:
    resend_api_key: str
    to_emails: list[str]
    from_email: str
    queries: list[str]
    topic_label: str
    mailto: str
    lookback_days: int
    max_pages: int
    max_email_items: int
    seen_file: Path


# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #

def _env(name: str, default: str = "") -> str:
    # CI 常把未配置的 Secret/Variable 注入为空字符串，空值等同「未设置」
    return (os.environ.get(name) or default).strip()


def _env_int(name: str, default: int, low: int, high: int) -> int:
    raw = _env(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError("%s 必须是整数，当前值=%r" % (name, raw)) from exc
    if not low <= value <= high:
        raise ConfigError("%s 必须在 [%d, %d] 范围内，当前值=%d" % (name, low, high, value))
    return value


def load_config() -> Config:
    api_key = _env("RESEND_API_KEY")
    if not api_key:
        raise ConfigError("缺少必填环境变量 RESEND_API_KEY")

    to_emails = [a.strip() for a in _env("ALERT_TO_EMAILS").split(",") if a.strip()]
    if not to_emails:
        raise ConfigError("缺少必填环境变量 ALERT_TO_EMAILS")

    raw_queries = _env("SEARCH_QUERIES") or _env("SEARCH_KEYWORDS")
    queries = [q.strip() for q in raw_queries.split(";") if q.strip()] if raw_queries else list(DEFAULT_QUERIES)
    if not queries:
        raise ConfigError("SEARCH_QUERIES 解析后为空")

    from_email = _env("RESEND_FROM", "onboarding@resend.dev")
    mailto = _env("OPENALEX_MAILTO") or to_emails[0]
    seen_raw = _env("SEEN_FILE")
    seen_file = (
        Path(seen_raw).expanduser()
        if seen_raw
        else Path(__file__).resolve().with_name("seen_ids.json")
    )

    cfg = Config(
        resend_api_key=api_key,
        to_emails=to_emails,
        from_email=from_email,
        queries=queries,
        topic_label=_env("TOPIC_LABEL", DEFAULT_TOPIC_LABEL),
        mailto=mailto,
        lookback_days=_env_int("LOOKBACK_DAYS", 7, 1, 30),
        max_pages=_env_int("MAX_PAGES", 10, 1, 50),
        max_email_items=_env_int("MAX_EMAIL_ITEMS", 50, 1, 200),
        seen_file=seen_file,
    )
    if from_email.endswith("@resend.dev"):
        logger.warning(
            "当前使用 Resend 测试发件人 %s，仅能投递到账号所属邮箱；"
            "生产环境请设置 RESEND_FROM 为已验证域名",
            from_email,
        )
    return cfg


# --------------------------------------------------------------------------- #
# OpenAlex 检索
# --------------------------------------------------------------------------- #

def _date_window(days: int) -> tuple[str, str]:
    today = datetime.now(timezone.utc).date()
    return (today - timedelta(days=days)).isoformat(), today.isoformat()


def _headers(cfg: Config) -> dict[str, str]:
    # mailto 查询参数 + 带 mailto 的 User-Agent，双保险进入礼貌请求池
    return {
        "User-Agent": "openalex-lit-monitor/1.0 (mailto:%s)" % cfg.mailto,
        "Accept": "application/json",
    }


def _fetch_page(session: Any, cfg: Config, query: str, cursor: str) -> dict[str, Any]:
    start, end = _date_window(cfg.lookback_days)
    params = {
        "search": query,
        "filter": "from_publication_date:%s,to_publication_date:%s" % (start, end),
        "per-page": PER_PAGE,
        "cursor": cursor,
        "mailto": cfg.mailto,
        "select": SELECT_FIELDS,
    }
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(
                OPENALEX_WORKS_URL,
                params=params,
                headers=_headers(cfg),
                timeout=HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict) or "results" not in data:
                raise ValueError("OpenAlex 响应结构异常：缺少 results 字段")
            return data
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            wait = 2 ** attempt
            logger.warning(
                "OpenAlex 请求失败(第 %d/%d 次): %s，%ds 后重试",
                attempt, MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)
    raise RuntimeError("OpenAlex 请求在 %d 次重试后仍失败: %s" % (MAX_RETRIES, last_error))


def fetch_recent_works(cfg: Config) -> list[dict[str, Any]]:
    """逐个检索式取结果并按 DOI/OpenAlex ID 取并集；单个检索式失败不阻断其余。"""
    session = requests.Session()
    collected: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    try:
        for q_idx, query in enumerate(cfg.queries, 1):
            cursor = "*"
            for page in range(1, cfg.max_pages + 1):
                try:
                    data = _fetch_page(session, cfg, query, cursor)
                except Exception as exc:
                    errors.append("%r -> %s" % (query, exc))
                    logger.error("检索式 %d/%d 失败: %r -> %s", q_idx, len(cfg.queries), query, exc)
                    break
                batch = [w for w in (data.get("results") or []) if isinstance(w, dict)]
                for work in batch:
                    cid = canonical_id(work)
                    if cid:
                        collected.setdefault(cid, work)
                logger.info(
                    "检索式 %d/%d 第 %d 页: %d 条，去重累计 %d 条",
                    q_idx, len(cfg.queries), page, len(batch), len(collected),
                )
                next_cursor = (data.get("meta") or {}).get("next_cursor")
                if not batch or not next_cursor or next_cursor == cursor:
                    break
                cursor = next_cursor
            else:
                logger.warning("检索式 %r 达到最大翻页数 %d，结果可能被截断", query, cfg.max_pages)
    finally:
        session.close()

    if not collected and errors:
        raise RuntimeError("全部 %d 个检索式均失败，最后错误: %s" % (len(errors), errors[-1]))
    if errors:
        logger.warning("有 %d 个检索式失败，本次仅基于成功结果推送（失败部分下次仍会重试）", len(errors))
    return list(collected.values())


# --------------------------------------------------------------------------- #
# 去重记录
# --------------------------------------------------------------------------- #

def canonical_id(work: dict[str, Any]) -> str:
    """优先用 DOI 作为唯一键，缺失时回退到 OpenAlex ID。"""
    doi = str(work.get("doi") or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
            break
    if doi.strip():
        return "doi:" + doi.strip()
    oa_id = str(work.get("id") or "").strip()
    if oa_id:
        return "openalex:" + oa_id.rsplit("/", 1)[-1]
    return ""


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        logger.info("未发现去重记录 %s，首次运行将推送窗口内全部文献", path)
        return set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        ids = raw if isinstance(raw, list) else raw.get("ids", []) if isinstance(raw, dict) else []
        return {str(x) for x in ids if isinstance(x, str) and x}
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("去重记录 %s 读取失败(%s)，本次按空记录处理", path, exc)
        return set()


def save_seen(path: Path, ids: set[str]) -> None:
    """先写临时文件再原子替换，避免中途崩溃损坏记录。"""
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(ids),
        "ids": sorted(ids),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# 字段解析与相关度
# --------------------------------------------------------------------------- #

def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _safe_url(value: Any) -> str:
    url = str(value if value is not None else "").strip()
    return url if url.lower().startswith(("http://", "https://")) else ""


def format_authors(work: dict[str, Any], limit: int = 6) -> str:
    names = []
    for item in work.get("authorships") or []:
        name = ((item or {}).get("author") or {}).get("display_name")
        if name and str(name).strip():
            names.append(str(name).strip())
    if not names:
        return "未知作者"
    if len(names) > limit:
        return ", ".join(names[:limit]) + " 等（共 %d 位作者）" % len(names)
    return ", ".join(names)


def extract_venue(work: dict[str, Any]) -> str:
    loc = work.get("primary_location") or {}
    src = loc.get("source") or {}
    name = str(src.get("display_name") or "").strip()
    return name or "未标注期刊/会议"


def extract_link(work: dict[str, Any]) -> str:
    doi = str(work.get("doi") or "").strip()
    if doi.lower().startswith(("http://", "https://")):
        return _safe_url(doi)
    if doi:
        if doi.lower().startswith("doi:"):
            doi = doi[4:]
        return "https://doi.org/" + doi.lstrip("/")
    loc = work.get("primary_location") or {}
    landing = _safe_url(loc.get("landing_page_url"))
    return landing or _safe_url(work.get("id"))


def reconstruct_abstract(work: dict[str, Any], limit: int = 320) -> str:
    """OpenAlex 以倒排索引返回摘要，需按位置还原；limit<=0 表示不截断。"""
    inv = work.get("abstract_inverted_index")
    if not isinstance(inv, dict) or not inv:
        return ""
    positions = []
    for word, indexes in inv.items():
        if not isinstance(indexes, list):
            continue
        for pos in indexes:
            if isinstance(pos, int):
                positions.append((pos, str(word)))
    positions.sort(key=lambda p: p[0])
    text = " ".join(w for _, w in positions)
    text = " ".join(text.split())
    if limit > 0 and len(text) > limit:
        text = text[:limit].rstrip() + "..."
    return text


def relevance_score(work: dict[str, Any]) -> int:
    """番茄相关文献优先，其次是结构变异与抗病基因信号。"""
    text = (str(work.get("title") or "") + " " + reconstruct_abstract(work, 0)).lower()
    score = 0
    if any(term in text for term in TOMATO_TERMS):
        score += 4
    if any(term in text for term in SV_TERMS):
        score += 2
    if any(term in text for term in RES_TERMS):
        score += 2
    return score


# --------------------------------------------------------------------------- #
# 邮件渲染
# --------------------------------------------------------------------------- #

CARD_TEMPLATE = Template("""
<div style="padding:16px 0;border-bottom:1px solid #f3f4f6;">
  <h2 style="margin:0 0 8px;font-size:16px;line-height:1.5;color:#111827;font-weight:600;">$title_block</h2>
  <p style="margin:0 0 6px;font-size:13px;color:#374151;line-height:1.5;">$authors</p>
  <p style="margin:0 0 10px;font-size:12px;color:#6b7280;">$venue &nbsp;|&nbsp; $pub_date</p>
  $abstract_block
  <p style="margin:10px 0 0;font-size:13px;">$link_block</p>
</div>
""")

PAGE_TEMPLATE = Template("""
<div style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
  <div style="max-width:680px;margin:0 auto;padding:24px 12px;">
    <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:24px;">
      <h1 style="margin:0 0 6px;font-size:20px;color:#111827;">最新文献速递</h1>
      <p style="margin:0 0 18px;font-size:13px;color:#6b7280;line-height:1.6;">
        监测主题：$topic<br>
        检索式：$queries<br>
        发表窗口：$window_start ~ $window_end<br>
        本次新增 <strong style="color:#111827;">$total</strong> 篇（下方展示 $shown 篇，按主题相关度排序）
      </p>
      $cards
      $truncated
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0 12px;">
      <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">
        数据来源 OpenAlex，由自动化脚本生成。已推送文献记录于 $seen_name，后续不再重复发送。
      </p>
    </div>
  </div>
</div>
""")


def render_html(cfg: Config, items: list[dict[str, Any]], total: int,
                start: str, end: str) -> str:
    cards = []
    for work in items:
        title = _esc(work.get("title") or "（无标题）")
        link = _safe_url(extract_link(work))
        if link:
            title_block = '<a href="%s" style="color:#1d4ed8;text-decoration:none;">%s</a>' % (_esc(link), title)
            link_block = '<a href="%s" style="color:#1d4ed8;text-decoration:none;">查看原文 / DOI &rarr;</a>' % _esc(link)
        else:
            title_block = title
            link_block = '<span style="color:#9ca3af;">暂无可用原文链接</span>'

        abstract = reconstruct_abstract(work)
        abstract_block = (
            '<p style="margin:0;font-size:13px;line-height:1.7;color:#4b5563;">%s</p>' % _esc(abstract)
            if abstract else
            '<p style="margin:0;font-size:13px;color:#9ca3af;">（OpenAlex 未提供摘要）</p>'
        )
        cards.append(CARD_TEMPLATE.substitute(
            title_block=title_block,
            authors=_esc(format_authors(work)),
            venue=_esc(extract_venue(work)),
            pub_date=_esc(work.get("publication_date") or "未知日期"),
            abstract_block=abstract_block,
            link_block=link_block,
        ))

    truncated = ""
    if total > len(items):
        truncated = (
            '<p style="margin:16px 0 0;font-size:13px;color:#b45309;">'
            '另有 %d 篇新文献未在本邮件展开，已全部计入去重记录。</p>' % (total - len(items))
        )

    return PAGE_TEMPLATE.substitute(
        topic=_esc(cfg.topic_label),
        queries=_esc(" ; ".join(cfg.queries)),
        window_start=_esc(start),
        window_end=_esc(end),
        total=total,
        shown=len(items),
        cards="".join(cards),
        truncated=truncated,
        seen_name=_esc(cfg.seen_file.name),
    )


def render_text(cfg: Config, items: list[dict[str, Any]], total: int,
                start: str, end: str) -> str:
    lines = [
        "最新文献速递",
        "监测主题: %s" % cfg.topic_label,
        "检索式: %s" % " ; ".join(cfg.queries),
        "发表窗口: %s ~ %s" % (start, end),
        "本次新增 %d 篇" % total,
        "",
    ]
    for i, work in enumerate(items, 1):
        lines.extend([
            "%d. %s" % (i, work.get("title") or "（无标题）"),
            "   作者: %s" % format_authors(work),
            "   来源: %s | 日期: %s" % (extract_venue(work), work.get("publication_date") or "未知"),
            "   摘要: %s" % (reconstruct_abstract(work, 200) or "暂无摘要"),
            "   原文: %s" % (extract_link(work) or "暂无链接"),
            "",
        ])
    return "\n".join(lines)


def send_email(cfg: Config, subject: str, html_body: str, text_body: str) -> Any:
    resend.api_key = cfg.resend_api_key
    params = {
        "from": cfg.from_email,
        "to": cfg.to_emails,
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    # 兼容 resend SDK 2.x 的 Emails.send 与部分新版小写命名空间
    emails_api = getattr(resend, "Emails", None) or getattr(resend, "emails", None)
    send = getattr(emails_api, "send", None) if emails_api is not None else None
    if send is None:
        raise RuntimeError("resend SDK 未暴露 Emails.send，请确认已安装 resend>=2.0")
    result = send(params)
    rid = result.get("id") if isinstance(result, dict) else result
    logger.info("邮件发送成功，resend id=%s", rid)
    return result


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #

def setup_logging() -> None:
    level = getattr(logging, _env("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    setup_logging()
    try:
        cfg = load_config()
    except ConfigError as exc:
        logger.error("配置错误: %s", exc)
        return 1

    logger.info(
        "开始检索 | 主题=%r | 检索式=%d 个 | 回溯=%d 天 | 收件人=%d 个 | mailto=%s",
        cfg.topic_label, len(cfg.queries), cfg.lookback_days, len(cfg.to_emails), cfg.mailto,
    )
    try:
        works = fetch_recent_works(cfg)
    except Exception as exc:
        logger.error("OpenAlex 检索失败，本次终止: %s", exc)
        return 1

    seen = load_seen(cfg.seen_file)
    fresh_ids: set[str] = set()
    new_works: list[dict[str, Any]] = []
    for work in works:
        cid = canonical_id(work)
        if not cid or cid in seen or cid in fresh_ids:
            continue
        fresh_ids.add(cid)
        new_works.append(work)

    if not new_works:
        logger.info(
            "无新增文献（检索 %d 条 / 历史已推送 %d 条），跳过邮件发送",
            len(works), len(seen),
        )
        return 0

    new_works.sort(
        key=lambda w: (relevance_score(w), str(w.get("publication_date") or "")),
        reverse=True,
    )
    logger.info("发现 %d 篇新文献，准备推送", len(new_works))

    start, end = _date_window(cfg.lookback_days)
    shown = new_works[:cfg.max_email_items]
    subject = "[文献速递] %s | 新增 %d 篇 | %s" % (cfg.topic_label, len(new_works), end)
    html_body = render_html(cfg, shown, len(new_works), start, end)
    text_body = render_text(cfg, shown, len(new_works), start, end)

    try:
        send_email(cfg, subject, html_body, text_body)
    except Exception as exc:
        logger.error("邮件发送失败: %s（去重记录未更新，下次运行会自动重试）", exc)
        return 1

    # 仅在邮件发送成功后落盘：发送失败时下一轮仍会重试这些文献
    try:
        save_seen(cfg.seen_file, seen | fresh_ids)
    except Exception as exc:
        logger.error("去重记录写入失败: %s", exc)
        return 1

    logger.info(
        "完成: 已推送 %d 篇（邮件展示 %d 篇），累计记录 %d 条",
        len(new_works), len(shown), len(seen) + len(fresh_ids),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
