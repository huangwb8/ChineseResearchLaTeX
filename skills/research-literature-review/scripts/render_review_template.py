#!/usr/bin/env python3
"""把正文片段放入真实的学术版式；不改写已有完整 TeX 或临床主张。"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

from path_scope import get_effective_scope_root, resolve_and_check

TEMPLATE = Path(__file__).resolve().parents[1] / "latex-template/review-article.tex"


def escape_title(text: str) -> str:
    substitutions = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                     "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(substitutions.get(c, c) for c in text)


def render(title: str, body: Path, bib: Path, output: Path) -> None:
    if not title.strip():
        raise ValueError("题名不能为空")
    content = body.read_text(encoding="utf-8")
    active = re.sub(r"(?<!\\)%[^\n]*", "", content)
    if re.search(r"\\(?:documentclass|bibliography|bibliographystyle)\b|\\(?:begin|end)\s*\{document\}", active):
        raise ValueError("body 只能包含摘要和正文章节；已有完整 TeX 请直接编译")
    if not bib.is_file():
        raise ValueError("参考文献文件不存在")
    try:
        bib_name = bib.resolve().relative_to(output.parent.resolve()).with_suffix("").as_posix()
    except ValueError as exc:
        raise ValueError("请先将 Bib 放入输出目录或其子目录，保证可复现") from exc
    if any(c in bib_name for c in "{}%\\#$~"):
        raise ValueError("Bib 相对路径含 TeX 控制字符")
    template = TEMPLATE.read_text(encoding="utf-8")
    # 一次替换，正文或题名中的标记不被二次求值。
    values = {"TITLE": escape_title(title), "BODY": content, "BIB": bib_name}
    rendered = re.sub(r"@@(TITLE|BODY|BIB)@@", lambda m: values[m.group(1)], template)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        handle.write(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--bib", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scope-root", type=Path)
    args = parser.parse_args()
    scope = get_effective_scope_root(args.scope_root)
    if scope is not None:
        args.body = resolve_and_check(args.body, scope, must_exist=True)
        args.bib = resolve_and_check(args.bib, scope, must_exist=True)
        args.output = resolve_and_check(args.output, scope, must_exist=False)
    render(args.title, args.body, args.bib, args.output)
    print(f"已生成学术版式：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
