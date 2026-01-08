#!/usr/bin/env python3
"""
validate_working_conditions.py - 对 {主题}_工作条件.md 做最小静态校验

目标：
  - 把“必须落地”的内容变成可检测的静态约束，避免工作条件文件流于形式
  - 作为 pipeline_runner 的阶段 7（质量验证）的一部分

注意：
  - 这是静态自检，不替代人工检查与动态复现测试
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from pipeline_runner import PipelineRunner


def _load_layout_paths() -> tuple[str, str, str]:
    """
    读取 config.yaml 中的 layout 配置（fallback 到默认值）。
    返回：(hidden_dir_name, reference_dir_name, data_extraction_name)
    """
    hidden = ".systematic-literature-review"
    reference = "reference"
    data_name = "data_extraction_table.md"
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    try:
        import yaml  # type: ignore

        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            layout = cfg.get("layout") if isinstance(cfg, dict) else {}
            if isinstance(layout, dict):
                hidden = str(layout.get("hidden_dir_name", hidden))
                reference = str(layout.get("reference_dir_name", reference))
                data_name = str(layout.get("reference_data_extraction_name", data_name))
    except Exception:
        # 保持默认值，避免校验因配置问题失败
        pass
    return hidden, reference, data_name

def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def _extract_h2_section(text: str, title: str) -> str:
    """
    Extract the content under a given H2 title:
      ## {title}
      ... until next ## or EOF
    """
    m = re.search(rf"(?m)^##\s+{re.escape(title)}\s*$", text)
    if not m:
        return ""
    start = m.end()
    m2 = re.search(r"(?m)^##\s+", text[start:])
    end = start + m2.start() if m2 else len(text)
    return text[start:end]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate {topic}_工作条件.md minimal requirements.")
    parser.add_argument("--md", required=True, type=Path, help="Path to {主题}_工作条件.md")
    args = parser.parse_args()

    md = args.md.resolve()
    if not md.exists():
        print(f"✗ missing working conditions file: {md}", file=sys.stderr)
        return 1

    text = _read(md)
    errors: list[str] = []

    headings = PipelineRunner.WORKING_CONDITIONS_HEADINGS

    # 1) 章节结构：彻底以 pipeline_runner 的骨架标题为准
    for key in PipelineRunner.WORKING_CONDITIONS_REQUIRED_H2_KEYS:
        title = headings.get(key)
        if not title:
            errors.append(f"internal: missing runner heading for key={key}")
            continue
        if not re.search(rf"(?m)^##\s+{re.escape(title)}\s*$", text):
            errors.append(f"missing required H2 section: {title}")

    for key in PipelineRunner.WORKING_CONDITIONS_REQUIRED_H3_KEYS:
        title = headings.get(key)
        if not title:
            errors.append(f"internal: missing runner heading for key={key}")
            continue
        if not re.search(rf"(?m)^###\s+{re.escape(title)}\s*$", text):
            errors.append(f"missing required H3 section: {title}")

    # 2) “硬指标”关键词必须显式出现（与骨架/规范一致）
    missing_keywords = [k for k in PipelineRunner.WORKING_CONDITIONS_REQUIRED_KEYWORDS if k not in text]
    if missing_keywords:
        errors.append(f"missing hard-indicator keywords: {', '.join(missing_keywords)}")

    # 3) 去重与版本选择留痕（即使标题存在，也要有关键术语）
    if not _has_any(text, [r"去重", r"dedupe", r"合并映射", r"版本(选择|合并)"]):
        errors.append("missing dedupe/version-merge record (去重/合并映射/版本选择)")

    # 4) 数据抽取表：改为引用隐藏文件，正文不再强制嵌入表格
    data_title = headings.get("data_extraction")
    if data_title:
        section = _extract_h2_section(text, data_title)
        hidden_dir, reference_dir, data_name = _load_layout_paths()
        # 要求正文显式引用隐藏目录的 data_extraction_table.md（路径提示即可）
        expected_fragment = rf"{re.escape(hidden_dir)}/{re.escape(reference_dir)}/{re.escape(data_name)}"
        if not re.search(expected_fragment, section):
            errors.append(
                f"data extraction section should reference hidden data_extraction_table.md (expected fragment: {hidden_dir}/{reference_dir}/{data_name})"
            )

    if errors:
        print("Working conditions validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("✓ Working conditions validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
