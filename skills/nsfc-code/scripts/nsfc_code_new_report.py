#!/usr/bin/env python3
"""
Create a new NSFC code recommendation report skeleton with the required filename:
  NSFC-CODE-vYYYYMMDDHHmm.md

This is a deterministic helper to reduce human/LLM mistakes on timestamp formatting
and document structure. It does NOT read or modify any proposal files.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence


TEMPLATE = """# NSFC 申请代码推荐

- 生成时间：{generated_at}
- 输入来源：{input_hint}
- 参考库：skills/nsfc-code/references/nsfc_2026_recommend_overrides.toml

## 标书内容要点（只读提炼）

- 研究对象：
- 核心科学问题：
- 主要方法/技术路线：
- 关键应用场景/系统：
- 关键词（10-20 个）：

## 5 组代码推荐（主/次）

### 推荐 1
- 申请代码1（主）：
- 申请代码2（次）：
- 理由：

### 推荐 2
- 申请代码1（主）：
- 申请代码2（次）：
- 理由：

### 推荐 3
- 申请代码1（主）：
- 申请代码2（次）：
- 理由：

### 推荐 4
- 申请代码1（主）：
- 申请代码2（次）：
- 理由：

### 推荐 5
- 申请代码1（主）：
- 申请代码2（次）：
- 理由：
"""


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".", help="Directory to write the report (default: .)")
    ap.add_argument(
        "--ts",
        default="",
        help="Explicit timestamp in YYYYMMDDHHmm (optional; default is now)",
    )
    ap.add_argument("--input-hint", default="（待填写：标书路径/文件列表）", help="Text to fill into 输入来源")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite if file exists")
    args = ap.parse_args(list(argv) if argv is not None else None)

    ts = args.ts.strip()
    if not ts:
        ts = datetime.now().strftime("%Y%m%d%H%M")
    if len(ts) != 12 or not ts.isdigit():
        raise SystemExit("FAIL: --ts must be YYYYMMDDHHmm (12 digits)")

    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"NSFC-CODE-v{ts}.md"

    if out_path.exists() and not args.overwrite:
        raise SystemExit(f"FAIL: output exists (use --overwrite): {out_path}")

    generated_at = datetime.strptime(ts, "%Y%m%d%H%M").strftime("%Y-%m-%d %H:%M")
    out_path.write_text(
        TEMPLATE.format(generated_at=generated_at, input_hint=args.input_hint),
        encoding="utf-8",
    )
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

