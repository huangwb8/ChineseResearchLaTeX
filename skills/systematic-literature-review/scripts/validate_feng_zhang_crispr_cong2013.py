#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable


OPENALEX_BASE = "https://api.openalex.org"


@dataclass(frozen=True)
class GoldItem:
    doi: str
    title: str | None


def _normalize_doi(doi_or_url: str) -> str | None:
    if not doi_or_url:
        return None
    value = doi_or_url.strip()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = value.strip().lower()
    if "/" not in value:
        return None
    return value


def _http_get_json(url: str, *, timeout_s: int = 30, retries: int = 5) -> Any:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "pipelines/skills systematic-literature-review validator (dev-only)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return json.load(resp)
        except Exception as e:  # pragma: no cover (best-effort network)
            last_err = e
            sleep_s = min(30.0, (2**attempt) + random.random())
            time.sleep(sleep_s)
    raise RuntimeError(f"GET failed after retries: {url}") from last_err


def _openalex_cursor_search(*, query: str, cutoff: date, per_page: int, max_pages: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    cursor = "*"
    pages = 0

    while pages < max_pages:
        params = {
            "search": query,
            "filter": f"to_publication_date:{cutoff.isoformat()}",
            "per-page": str(per_page),
            "cursor": cursor,
        }
        url = f"{OPENALEX_BASE}/works?" + urllib.parse.urlencode(params)
        data = _http_get_json(url)
        batch = data.get("results") or []
        items.extend(batch)

        cursor = (data.get("meta") or {}).get("next_cursor")
        pages += 1
        if not cursor or not batch:
            break

        time.sleep(0.4 + random.random() * 0.6)

    return items


def _extract_dois_from_openalex_works(works: Iterable[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for w in works:
        doi_url = w.get("doi")
        doi = _normalize_doi(doi_url) if isinstance(doi_url, str) else None
        if doi:
            out.add(doi)
    return out


def _load_gold(path: str) -> tuple[date, list[GoldItem]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cutoff = date(*data["cutoff"]["date"])
    items = [
        GoldItem(doi=_normalize_doi(i["doi"]) or i["doi"].lower(), title=i.get("title"))
        for i in (data.get("gold") or {}).get("items", [])
        if i.get("doi")
    ]
    return cutoff, items


def _load_found_dois(path: str) -> set[str]:
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            raw = data
        elif isinstance(data, dict):
            raw = data.get("dois") or data.get("items") or []
        else:
            raw = []
        out = set()
        for v in raw:
            if not isinstance(v, str):
                continue
            doi = _normalize_doi(v)
            if doi:
                out.add(doi)
        return out

    out: set[str] = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            doi = _normalize_doi(line)
            if doi:
                out.add(doi)
    return out


def _default_baseline_queries() -> list[str]:
    return [
        # CRISPR 核心术语（早期论文更可能包含全称/系统名）
        "CRISPR",
        "\"clustered regularly interspaced short palindromic repeats\"",
        "\"CRISPR-Cas\"",
        "\"CRISPR Cas\"",
        "\"type II\" CRISPR",
        "tracrRNA",
        "Cas9",
        "Csn1",
        "\"RNA-guided\" endonuclease",
        # 与 Cong et al. 2013 相关的“基因组工程”方法学背景（ZFN/TALEN/TALE）
        "\"zinc finger\" nuclease",
        "\"zinc-finger\" nuclease",
        "TALEN",
        "\"TALE\" nuclease",
        "\"genome engineering\" nuclease",
    ]


def _gapfill_queries_from_missing(missing: list[GoldItem], *, max_items: int) -> list[str]:
    queries: list[str] = []
    for item in missing[:max_items]:
        if not item.title:
            continue
        title = re.sub(r"\s+", " ", item.title).strip()
        # 用标题前 8–12 个词做“定位型查询”，模拟开发时的 gap analysis（非生产策略）
        words = re.split(r"\s+", title)
        short = " ".join(words[:12]).strip()
        if len(short) >= 12:
            queries.append(f"\"{short}\"")
    # 去重保序
    out: list[str] = []
    seen: set[str] = set()
    for q in queries:
        k = q.casefold()
        if k in seen:
            continue
        seen.add(k)
        out.append(q)
    return out


def _score(found: set[str], gold: list[GoldItem]) -> tuple[float, list[GoldItem]]:
    gold_dois = [g.doi for g in gold]
    gold_set = set(gold_dois)
    hit = len(found & gold_set)
    recall = hit / max(1, len(gold_set))
    missing = [g for g in gold if g.doi not in found]
    return recall, missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "开发/优化 systematic-literature-review 用的验证示例：\n"
            "- gold set: Cong et al. 2013 (Zhang Lab) 参考文献（按 cutoff 过滤）\n"
            "- 目标: 检索覆盖率 ≥ target\n"
            "说明：本脚本为开发验证用，会进行联网请求；不应在生产任务中默认调用。"
        )
    )
    parser.add_argument(
        "--gold",
        default="systematic-literature-review/references/validation_feng_zhang_crispr_cong2013_gold.json",
        help="gold set JSON 路径",
    )
    parser.add_argument(
        "--found-dois",
        default="",
        help="可选：从文件读取已检索到的 DOI 列表并直接评分（.json 或逐行文本）；提供后将跳过联网检索",
    )
    parser.add_argument("--target", type=float, default=0.95, help="目标覆盖率（默认 0.95）")
    parser.add_argument("--max-rounds", type=int, default=3, help="最多迭代轮数（默认 3）")
    parser.add_argument("--per-page", type=int, default=200, help="OpenAlex 每页条数（默认 200）")
    parser.add_argument("--max-pages", type=int, default=3, help="每个 query 最多翻页次数（默认 3）")
    parser.add_argument(
        "--gapfill-max",
        type=int,
        default=12,
        help="gapfill 阶段最多基于多少个 missing 生成定位查询（默认 12）",
    )
    parser.add_argument(
        "--show-missing",
        action="store_true",
        help="在未达标阶段输出 missing 列表（默认不输出；最终 FAIL 一定会输出）",
    )
    args = parser.parse_args()

    cutoff, gold = _load_gold(args.gold)
    baseline_queries = _default_baseline_queries()

    found: set[str] = set()

    if args.found_dois:
        found = _load_found_dois(args.found_dois)
        recall, missing = _score(found, gold)
        print(
            json.dumps(
                {
                    "mode": "score_only",
                    "cutoff": cutoff.isoformat(),
                    "found_dois": len(found),
                    "gold": len(gold),
                    "hit": len(gold) - len(missing),
                    "recall": round(recall, 4),
                },
                ensure_ascii=False,
            )
        )
        if recall >= args.target:
            print("PASS")
            return 0
        print(
            json.dumps(
                {
                    "result": "FAIL",
                    "target": args.target,
                    "recall": round(recall, 4),
                    "missing": [{"doi": m.doi, "title": m.title} for m in missing],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    for round_idx in range(1, max(1, args.max_rounds) + 1):
        if round_idx == 1:
            queries = baseline_queries
            phase = "baseline"
        else:
            _, missing = _score(found, gold)
            if not missing:
                break
            queries = _gapfill_queries_from_missing(missing, max_items=max(1, args.gapfill_max))
            phase = f"gapfill_{round_idx-1}"

        for q in queries:
            works = _openalex_cursor_search(query=q, cutoff=cutoff, per_page=max(1, args.per_page), max_pages=max(1, args.max_pages))
            found |= _extract_dois_from_openalex_works(works)

        recall, missing = _score(found, gold)
        print(
            json.dumps(
                {
                    "phase": phase,
                    "cutoff": cutoff.isoformat(),
                    "queries": len(queries),
                    "found_dois": len(found),
                    "gold": len(gold),
                    "hit": len(gold) - len(missing),
                    "recall": round(recall, 4),
                },
                ensure_ascii=False,
            )
        )

        if args.show_missing and recall < args.target:
            print(
                json.dumps(
                    {
                        "phase": f"{phase}_missing",
                        "count": len(missing),
                        "items": [{"doi": m.doi, "title": m.title} for m in missing],
                    },
                    ensure_ascii=False,
                )
            )

        if recall >= args.target:
            print("PASS")
            return 0

    # 最终失败：输出缺口（方便人工优化 query set）
    recall, missing = _score(found, gold)
    print(
        json.dumps(
            {
                "result": "FAIL",
                "target": args.target,
                "recall": round(recall, 4),
                "missing": [{"doi": m.doi, "title": m.title} for m in missing],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
