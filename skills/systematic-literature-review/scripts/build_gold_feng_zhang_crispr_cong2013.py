#!/usr/bin/env python3
from __future__ import annotations

import argparse
import calendar
import json
import random
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class WorkRef:
    doi: str
    title: str | None
    first_author: str | None
    issued: list[int] | None
    url: str


def _subtract_months(d: date, months: int) -> date:
    year = d.year
    month = d.month - months
    while month <= 0:
        month += 12
        year -= 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def _http_get_json(url: str, *, timeout_s: int = 30, retries: int = 6) -> Any:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "pipelines/skills systematic-literature-review gold-builder (dev-only)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return json.load(resp)
        except Exception as e:  # pragma: no cover (best-effort network)
            last_err = e
            time.sleep(min(20.0, (2**attempt) + random.random()))
    raise RuntimeError(f"GET failed after retries: {url}") from last_err


def _crossref_work(doi: str) -> dict[str, Any]:
    doi = doi.strip()
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    return _http_get_json(url)["message"]


def _issued_to_date(issued: list[int] | None) -> date | None:
    if not issued or not issued[0]:
        return None
    year = issued[0]
    month = issued[1] if len(issued) > 1 and issued[1] else 1
    day = issued[2] if len(issued) > 2 and issued[2] else 1
    try:
        return date(year, month, day)
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "生成/刷新开发验证用 gold set：\n"
            "- source: Cong et al. 2013 (Zhang Lab) 的 Crossref reference 列表（含 DOI）\n"
            "- cutoff: source paper 发布日期往前推 6 个月（按日历月）\n"
            "- gold: 发布日期 <= cutoff 的引用条目"
        )
    )
    parser.add_argument("--source-doi", default="10.1126/science.1231143", help="张峰团队标志性论文 DOI（默认 Cong et al., 2013）")
    parser.add_argument("--months", type=int, default=6, help="cutoff 回退月数（默认 6）")
    parser.add_argument(
        "--out",
        default="systematic-literature-review/references/validation_feng_zhang_crispr_cong2013_gold.json",
        help="输出 gold JSON 路径",
    )
    args = parser.parse_args()

    source = _crossref_work(args.source_doi)
    issued_parts = (source.get("issued") or {}).get("date-parts", [[None]])[0]
    if not issued_parts or not issued_parts[0]:
        raise RuntimeError("source paper missing issued date in Crossref")

    source_pub = date(*issued_parts)
    cutoff = _subtract_months(source_pub, max(0, args.months))

    references = source.get("reference") or []
    ref_dois = [r.get("DOI") for r in references if r.get("DOI")]
    ref_dois = [d.lower().strip() for d in ref_dois if isinstance(d, str) and d.strip()]

    gold_items: list[WorkRef] = []
    excluded: list[dict[str, Any]] = []

    for doi in ref_dois:
        work = _crossref_work(doi)
        issued = (work.get("issued") or {}).get("date-parts", [[None]])[0]
        pub_date = _issued_to_date(issued)

        ref = WorkRef(
            doi=doi,
            title=(work.get("title") or [None])[0],
            first_author=((work.get("author") or [{}])[0].get("family")),
            issued=issued if issued and issued[0] else None,
            url=work.get("URL") or f"https://doi.org/{doi}",
        )

        if pub_date and pub_date <= cutoff:
            gold_items.append(ref)
        else:
            excluded.append(
                {
                    "doi": ref.doi,
                    "title": ref.title,
                    "first_author": ref.first_author,
                    "issued": ref.issued,
                    "url": ref.url,
                    "excluded_reason": "published_after_cutoff" if pub_date else "missing_issued_date",
                }
            )

        time.sleep(0.2 + random.random() * 0.2)

    out = {
        "scenario": "feng_zhang_pre_cong2013_literature_review",
        "source_paper": {
            "doi": args.source_doi,
            "title": (source.get("title") or [None])[0],
            "published": issued_parts,
            "url": source.get("URL") or f"https://doi.org/{args.source_doi}",
        },
        "cutoff": {"rule": f"calendar_minus_{args.months}_months", "date": [cutoff.year, cutoff.month, cutoff.day]},
        "gold": {
            "definition": "Cong et al. 2013 reference list items with DOI and published on/before cutoff (by Crossref issued date).",
            "count": len(gold_items),
            "items": [
                {
                    "doi": g.doi,
                    "title": g.title,
                    "first_author": g.first_author,
                    "issued": g.issued,
                    "url": g.url,
                }
                for g in sorted(gold_items, key=lambda x: (x.first_author or "", x.doi))
            ],
        },
        "excluded": {"count": len(excluded), "items": excluded},
        "generated_by": "Crossref API",
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

