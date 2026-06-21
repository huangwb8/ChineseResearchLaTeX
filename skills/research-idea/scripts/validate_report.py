#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


DEFAULT_CONFIG = {
    "output": {
        "required_sections": [
            "多个科学问题-科学假设对",
            "为什么选择这些科学问题-科学假设对",
            "最佳科学问题-科学假设对",
            "查新摘要",
            "风险与下一步",
        ]
    },
    "validation": {
        "forbidden_path_patterns": [
            r"\.bensz-api(?:[\\/]|$)",
            r"\.research-idea(?:[\\/]|$)",
            r"tests[\\/]research-idea(?:[\\/]|$)",
            r"\.parallel-vibe(?:[\\/]|$)",
            r"\.parallel_vibe(?:[\\/]|$)",
        ],
        "require_falsifiability_terms": ["可证伪", "反证", "推翻"],
        "min_question_hypothesis_pairs": 2,
    },
}


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config() -> dict:
    config_path = skill_root() / "config.yaml"
    if yaml is None and config_path.exists():
        raise SystemExit("缺少 PyYAML，无法读取 research-idea/config.yaml；请安装 pyyaml 后重试")
    if not config_path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config = copy.deepcopy(DEFAULT_CONFIG)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            merged = config[key].copy()
            merged.update(value)
            config[key] = merged
        else:
            config[key] = value
    return config


def has_section(text: str, section: str) -> bool:
    return re.search(rf"^##\s+{re.escape(section)}(?:\s|$)", text, re.MULTILINE) is not None


def extract_section(text: str, section: str) -> str:
    match = re.search(rf"^##\s+{re.escape(section)}(?:\s|$).*$", text, re.MULTILINE)
    if match is None:
        return ""
    next_match = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    if next_match is None:
        return text[match.end() :]
    return text[match.end() : match.end() + next_match.start()]


def extract_candidates(text: str) -> list[str]:
    section = extract_section(text, "多个科学问题-科学假设对")
    chunks = re.split(r"^###\s+候选\s*\d+[:：]?.*$", section, flags=re.MULTILINE)
    return [chunk for chunk in chunks[1:] if chunk.strip()]


def path_is_inside_named_dir(report_path: Path, names: set[str]) -> str | None:
    for parent in report_path.parents:
        if parent.name in names:
            return parent.name
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="验证 research-idea 最终 Markdown 报告")
    parser.add_argument("--report", required=True, help="最终 Research-Idea Markdown 文件")
    parser.add_argument("--allow-custom-name", action="store_true", help="用户显式指定输出文件名时放宽文件名模板检查")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    args = parser.parse_args()

    config = load_config()
    report_path = Path(args.report).expanduser().resolve()
    if not report_path.exists() or not report_path.is_file():
        raise SystemExit(f"report 不存在或不是文件: {report_path}")

    text = report_path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    if report_path.suffix.lower() != ".md":
        errors.append("最终报告必须是 Markdown 文件")
    if (
        not args.allow_custom_name
        and (not report_path.name.startswith("Research-Idea_") or report_path.suffix.lower() != ".md")
    ):
        errors.append("文件名应为 Research-Idea_{github仓库名}_{pr名}_{时间戳}.md")

    inside = path_is_inside_named_dir(report_path, {".bensz-api", ".research-idea", "tests", ".parallel-vibe", ".parallel_vibe", "parallel-vibe"})
    if inside is not None:
        errors.append(f"最终报告不得放在中间目录或测试目录内: {inside}")

    for section in config["output"]["required_sections"]:
        if not has_section(text, section):
            errors.append(f"缺少二级标题: {section}")

    for pattern in config["validation"]["forbidden_path_patterns"]:
        if re.search(pattern, text):
            errors.append(f"最终报告不应暴露中间路径: {pattern}")

    candidates = extract_candidates(text)
    pair_count = len(candidates)
    min_pairs = int(
        config.get("iteration", {}).get(
            "min_candidates",
            config["validation"]["min_question_hypothesis_pairs"],
        )
    )
    if pair_count < min_pairs:
        errors.append(f"科学问题-假设对数量不足: 需要至少 {min_pairs} 对，实际 {pair_count} 对")

    candidate_markers = config["validation"].get("required_candidate_markers", [])
    for index, candidate in enumerate(candidates, start=1):
        for marker in candidate_markers:
            if marker not in candidate:
                errors.append(f"候选 {index} 缺少字段: {marker}")
        if "同上" in candidate:
            errors.append(f"候选 {index} 不得使用“同上”代替完整字段")

    terms = config["validation"]["require_falsifiability_terms"]
    if not any(term in text for term in terms):
        errors.append("报告缺少可证伪/反证/推翻等反证路径表述")

    if "Premium" not in text:
        errors.append("查新摘要必须明确说明使用 research-literature-review Premium 档")

    novelty_section = extract_section(text, "查新摘要")
    for status in ("未研究", "部分研究但关键缺口存在", "已充分研究"):
        if status in novelty_section:
            break
    else:
        errors.append("查新摘要必须包含候选的新颖性状态")

    best_section = extract_section(text, "最佳科学问题-科学假设对")
    for marker in config["validation"].get("required_best_markers", []):
        if marker not in best_section:
            errors.append(f"最佳方案章节缺少理由字段: {marker}")

    result = {
        "report": str(report_path),
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "pair_count": pair_count,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"status={status}")
        print(f"pair_count={pair_count}")
        for error in errors:
            print(f"error={error}")
        for warning in warnings:
            print(f"warning={warning}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
