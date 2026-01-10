#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
systematic-literature-review 集成功能验证脚本

手动验证核心功能是否正常工作
"""

import sys
import tempfile
from pathlib import Path

# 添加 core 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from review_integration import (
    analyze_review_directory,
    detect_slr_directory,
    extract_citation_keys_from_bib,
    extract_citations_from_tex,
    format_review_directory_summary,
    validate_citation_consistency,
    validate_read_access,
)


def create_test_slr_directory(tmp_dir: Path) -> None:
    """创建测试用的 systematic-literature-review 目录结构"""
    # 创建标记文件夹
    (tmp_dir / ".systematic-literature-review").mkdir()

    # 创建典型的 .tex 文件
    tex_content = r"""
\section{Introduction}
Some text here \cite{zhang2020}.

\section{Related Work}
More content \cite{li2021,wang2022}.
"""
    (tmp_dir / "topic_review.tex").write_text(tex_content)

    # 创建典型的 .bib 文件
    bib_content = """
@article{zhang2020,
    title = {Test Article 1},
    author = {Zhang, San},
    year = {2020}
}

@article{li2021,
    title = {Test Article 2},
    author = {Li, Si},
    year = {2021}
}

@article{wang2022,
    title = {Test Article 3},
    author = {Wang, Wu},
    year = {2022}
}

@article{unused2023,
    title = {Unused Article},
    author = {Unused, Author},
    year = {2023}
}
"""
    (tmp_dir / "topic_参考文献.bib").write_text(bib_content)


def test_detect_slr_directory():
    """测试目录检测功能"""
    print("测试 1: 目录检测")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # 测试空目录
        print("  - 空目录:", detect_slr_directory(tmp_path))

        # 测试 SLR 目录
        create_test_slr_directory(tmp_path)
        print("  - SLR 目录:", detect_slr_directory(tmp_path))

    print("  ✓ 测试通过\n")


def test_analyze_directory():
    """测试目录分析功能"""
    print("测试 2: 目录分析")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        create_test_slr_directory(tmp_path)

        info = analyze_review_directory(tmp_path)
        print(f"  - 路径: {info.path}")
        print(f"  - 是 SLR 目录: {info.is_slr_directory}")
        print(f"  - 只读: {info.read_only}")
        print(f"  - TeX 文件数: {len(info.tex_files)}")
        print(f"  - Bib 文件数: {len(info.bib_files)}")

    print("  ✓ 测试通过\n")


def test_extract_citations():
    """测试引用提取功能"""
    print("测试 3: 引用提取")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        create_test_slr_directory(tmp_path)

        tex_file = tmp_path / "topic_review.tex"
        bib_file = tmp_path / "topic_参考文献.bib"

        tex_keys = extract_citations_from_tex(tex_file)
        bib_keys = extract_citation_keys_from_bib(bib_file)

        print(f"  - .tex 中的引用: {sorted(tex_keys)}")
        print(f"  - .bib 中的条目: {sorted(bib_keys)}")

    print("  ✓ 测试通过\n")


def test_validate_consistency():
    """测试引用一致性验证"""
    print("测试 4: 引用一致性验证")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        create_test_slr_directory(tmp_path)

        tex_file = tmp_path / "topic_review.tex"
        bib_file = tmp_path / "topic_参考文献.bib"

        result = validate_citation_consistency(tex_file, bib_file)

        print(f"  - 缺失的引用 (在 .tex 中但不在 .bib 中): {sorted(result['missing_in_bib'])}")
        print(f"  - 未使用的引用 (在 .bib 中但不在 .tex 中): {sorted(result['unused_in_bib'])}")

    print("  ✓ 测试通过\n")


def test_format_summary():
    """测试格式化输出"""
    print("测试 5: 格式化输出")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        create_test_slr_directory(tmp_path)

        info = analyze_review_directory(tmp_path)
        summary = format_review_directory_summary(info)

        print("  - 目录摘要:")
        print("    " + "\n    ".join(summary.split("\n")))

    print("  ✓ 测试通过\n")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("systematic-literature-review 集成功能验证")
    print("=" * 60)
    print()

    try:
        test_detect_slr_directory()
        test_analyze_directory()
        test_extract_citations()
        test_validate_consistency()
        test_format_summary()

        print("=" * 60)
        print("所有测试通过!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
