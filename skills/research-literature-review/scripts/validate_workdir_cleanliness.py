#!/usr/bin/env python3
"""
validate_workdir_cleanliness.py - 校验工作目录根部的整洁性

检查工作目录根部是否有不符合约定的文件（最终交付物以外的文件）。
用于发现 AI 临时文件或中间产物泄漏到工作目录根部的问题。

使用示例：
    python validate_workdir_cleanliness.py --work-dir runs/my-topic
    python validate_workdir_cleanliness.py --work-dir runs/my-topic --strict
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List


# 允许存在于工作目录根部的文件模式（最终交付物）
ALLOWED_PATTERNS = [
    "*_工作条件.md",
    "*_review.tex",
    "*_参考文献.bib",
    "*_review.pdf",
    "*_review.docx",
    "*_验证报告.md",
]

# 允许存在的隐藏目录/文件
ALLOWED_HIDDEN = [
    ".systematic-literature-review",
    "output",
    "input",
    "log",
    ".DS_Store",
    ".gitignore",
]

PUBLISH_ALLOWED_PATTERNS = ["*_review.pdf", "*_review.docx"]
PUBLISH_SUPPORTING_PATTERNS = ["*_review.tex"]


def validate_publish_dir(publish_dir: Path, include_supporting: bool = False) -> List[Path]:
    """返回发布目录中不属于发布白名单的条目。"""
    publish_dir = Path(publish_dir).expanduser().resolve()
    if not publish_dir.exists() or not publish_dir.is_dir():
        return []
    patterns = PUBLISH_ALLOWED_PATTERNS + (PUBLISH_SUPPORTING_PATTERNS if include_supporting else [])
    allowed = {p.relative_to(publish_dir).as_posix() for p in publish_dir.iterdir()
               if p.is_file() and any(p.match(pattern) for pattern in patterns)}
    if include_supporting:
        from publish_deliverables import collect_tex_resources, collect_materials, resource_destination, PUBLISH_DIRS, PublishError
        allowed.update(p.relative_to(publish_dir).as_posix() for pattern in (
            "references/*.bib", "qc/*_工作条件.md", "qc/*_验证报告.md") for p in publish_dir.glob(pattern) if p.is_file())
        try:
            allowed.update(collect_materials(publish_dir))
        except PublishError:
            return [publish_dir / "materials"]
        for tex in publish_dir.glob("*_review.tex"):
            try:
                for name in collect_tex_resources(tex, publish_dir):
                    # 依赖存在也不能把旧的平铺文件视为符合新规范。
                    if name == tex.name or resource_destination(name) == name:
                        allowed.add(name)
            except PublishError:
                return [tex]  # 依赖不能复现，不能只凭文件后缀宣布整洁。
    else:
        PUBLISH_DIRS = set()
    return [p for p in sorted(publish_dir.rglob("*"))
            if p.is_symlink() or (p.is_file() and p.relative_to(publish_dir).as_posix() not in allowed)
            or (p.is_dir() and p.parent == publish_dir and p.name not in PUBLISH_DIRS)]


def validate_workdir(work_dir: Path, strict: bool = False) -> tuple[List[Path], List[Path]]:
    """
    校验工作目录根部的整洁性。

    返回：
        (unexpected_files, warnings)
        - unexpected_files: 不应存在的文件列表
        - warnings: 可能需要关注的文件列表（非严格模式下不视为错误）
    """
    unexpected: List[Path] = []
    warnings: List[Path] = []

    if not work_dir.exists() or not work_dir.is_dir():
        return unexpected, warnings

    for p in work_dir.iterdir():
        # 跳过允许的隐藏目录/文件
        if p.name in ALLOWED_HIDDEN:
            continue

        # 跳过其他隐藏文件/目录
        if p.name.startswith("."):
            if strict:
                warnings.append(p)
            continue

        # 非隐藏子目录不应存在于工作目录根部（视为 unexpected，严格隔离）
        if p.is_dir():
            unexpected.append(p)
            continue

        # 检查是否匹配允许的模式
        if any(p.match(pat) for pat in ALLOWED_PATTERNS):
            continue

        # 不匹配任何允许模式的文件
        unexpected.append(p)

    return unexpected, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="校验工作目录根部的整洁性（检测中间文件泄漏）"
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        required=False,
        help="工作目录路径",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：隐藏文件也会被警告",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )
    parser.add_argument("--publish-dir", type=Path, help="改为校验正式发布目录")
    parser.add_argument("--include-supporting", action="store_true", help="按 references/qc/materials 结构校验完整包")
    args = parser.parse_args()

    if args.publish_dir:
        publish_dir = args.publish_dir.expanduser().resolve()
        unexpected = validate_publish_dir(publish_dir, include_supporting=args.include_supporting)
        if unexpected:
            print(f"⚠️ 发布目录存在 {len(unexpected)} 个未授权条目：")
            for path in unexpected:
                print(f"  - {path.name}")
            return 1
        print("✓ 发布目录整洁")
        return 0

    if args.work_dir is None:
        parser.error("需要 --work-dir 或 --publish-dir")
    work_dir = args.work_dir.expanduser().resolve()
    if not work_dir.exists():
        print(f"错误：工作目录不存在: {work_dir}", file=sys.stderr)
        return 1

    unexpected, warnings = validate_workdir(work_dir, strict=args.strict)

    if args.json:
        import json

        result = {
            "work_dir": str(work_dir),
            "is_clean": len(unexpected) == 0,
            "unexpected_files": [str(p.relative_to(work_dir)) for p in unexpected],
            "warnings": [str(p.relative_to(work_dir)) for p in warnings],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if len(unexpected) == 0 else 1

    # 文本格式输出
    if unexpected:
        print(f"⚠️ 发现 {len(unexpected)} 个不应存在于工作目录根部的文件：")
        for p in unexpected:
            print(f"  - {p.name}")
        print()
        print("建议：运行以下命令整理")
        print(f"  python scripts/organize_run_dir.py --work-dir {work_dir} --apply")
        print()
        print("或者手动移动这些文件到 .systematic-literature-review/artifacts/")

    if warnings:
        print(f"\n⚠️ 发现 {len(warnings)} 个可能需要关注的条目：")
        for p in warnings:
            suffix = "（目录）" if p.is_dir() else ""
            print(f"  - {p.name}{suffix}")

    if not unexpected and not warnings:
        print("✓ 工作目录根部整洁")
        return 0

    return 1 if unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
