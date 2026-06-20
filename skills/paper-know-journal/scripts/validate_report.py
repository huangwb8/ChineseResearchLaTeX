#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - dependency fallback
    yaml = None

URL_RE = re.compile(r"https?://[^\s)>\"]+")
TRAILING_URL_PUNCTUATION = ".,;:!?，。；：！？、）】》"

DEFAULT_CONFIG = {
    "report": {
        "required_sections": [
            "调研摘要",
            "期刊概况",
            "官方投稿要求",
            "投稿形式要求与格式清单",
            "费用、开放获取与版权",
            "审稿流程与周期",
            "近期发表文章格式观察",
            "社区评价与作者体验",
            "投稿建议",
            "来源与可信度",
        ]
    },
    "validation": {
        "min_urls": 5,
        "require_access_date": True,
        "require_source_markers": True,
        "official_markers": ["官方", "官网", "出版社", "author guidelines"],
        "community_markers": ["社区", "第三方", "作者体验", "SciRev", "LetPub"],
        "official_table_types": ["官方", "官网", "出版社"],
        "community_table_types": ["社区", "第三方", "作者体验"],
        "community_absence_phrases": ["未找到足够社区评价", "社区评价稀少"],
        "min_format_requirement_markers": 6,
        "format_requirement_markers": [
            "标题页",
            "摘要",
            "关键词",
            "正文结构",
            "图表",
            "补充材料",
            "参考文献",
            "声明",
            "伦理",
            "数据",
            "代码",
            "AI",
            "cover letter",
        ],
        "required_named_headings": ["目标文体/文章类型具体要求"],
        "min_article_type_requirement_markers": 5,
        "article_type_requirement_markers": [
            "目标文体",
            "文章类型",
            "官方名称",
            "章节标题",
            "章节顺序",
            "字数",
            "页数",
            "摘要类型",
            "关键词",
            "图表",
            "补充材料",
            "参考文献限制",
            "报告清单",
            "未在官方页面确认",
        ],
    },
}


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config() -> dict:
    config_path = skill_root() / "config.yaml"
    if yaml is None or not config_path.exists():
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


def extract_urls(text: str) -> set[str]:
    return {url.rstrip(TRAILING_URL_PUNCTUATION) for url in URL_RE.findall(text)}


def has_any_marker(text: str, markers: list[str]) -> bool:
    lower_text = text.lower()
    return any(marker.lower() in lower_text for marker in markers)


def has_source_type_row(text: str, source_types: tuple[str, ...]) -> bool:
    source_type_pattern = "|".join(re.escape(item) for item in source_types)
    pattern = rf"^\|[^|\n]+\|[^|\n]*https?://[^|\n]*\|\s*(?:{source_type_pattern})\s*\|"
    return re.search(pattern, text, re.MULTILINE | re.IGNORECASE) is not None


def count_markers(text: str, markers: list[str]) -> int:
    lower_text = text.lower()
    return sum(1 for marker in markers if marker.lower() in lower_text)


def has_heading(text: str, heading: str) -> bool:
    return re.search(rf"^#+\s+{re.escape(heading)}(?:\s|$)", text, re.MULTILINE) is not None


def extract_heading_section(text: str, heading: str) -> str:
    pattern = rf"^(?P<marks>#+)\s+{re.escape(heading)}(?:\s|$).*$"
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        return ""
    level = len(match.group("marks"))
    start = match.start()
    next_heading = re.search(rf"^#{{1,{level}}}\s+", text[match.end() :], re.MULTILINE)
    if next_heading is None:
        return text[start:]
    return text[start : match.end() + next_heading.start()]


def main() -> None:
    parser = argparse.ArgumentParser(description="验证 paper-know-journal 报告的基本结构")
    parser.add_argument("--report", required=True, help="最终 KnowJournal Markdown 文件")
    parser.add_argument("--journal", help="期刊名，用于检查标题或正文是否包含")
    parser.add_argument("--min-urls", type=int, help="最少来源链接数量，默认读取 config.yaml")
    args = parser.parse_args()
    config = load_config()
    report_config = config["report"]
    validation_config = config["validation"]

    report_path = Path(args.report).expanduser().resolve()
    if not report_path.exists() or not report_path.is_file():
        raise SystemExit(f"report 不存在或不是文件: {report_path}")

    text = report_path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    if not report_path.name.startswith("KnowJournal-") or report_path.suffix.lower() != ".md":
        errors.append("文件名应为 KnowJournal-{杂志名}.md")

    if args.journal and args.journal.lower() not in text.lower():
        warnings.append("正文中未直接包含传入的 journal 名称")

    for section in report_config["required_sections"]:
        if not re.search(rf"^##\s+{re.escape(section)}(?:\s|$)", text, re.MULTILINE):
            errors.append(f"缺少二级标题: {section}")

    for heading in validation_config.get("required_named_headings", []):
        if not has_heading(text, heading):
            errors.append(f"缺少标题: {heading}")

    urls = extract_urls(text)
    min_urls = args.min_urls or int(validation_config["min_urls"])
    if len(urls) < min_urls:
        errors.append(f"来源链接不足: 需要至少 {min_urls} 个，实际 {len(urls)} 个")

    forbidden_patterns = [
        r"\.paper-know-journal(?:[\\/]|$)",
        r"tests[\\/]paper-know-journal(?:[\\/]|$)",
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, text):
            errors.append(f"最终报告不应暴露中间目录或测试目录: {pattern}")

    if validation_config["require_access_date"] and "访问日期" not in text and "accessed" not in text.lower():
        errors.append("缺少访问日期提示")

    if validation_config["require_source_markers"]:
        if not has_any_marker(text, validation_config["official_markers"]):
            errors.append("缺少官方来源标记")
        if not has_any_marker(text, validation_config["community_markers"]):
            errors.append("缺少社区/第三方来源标记")
        community_absence_stated = has_any_marker(
            text,
            validation_config["community_absence_phrases"],
        )
        if not has_source_type_row(text, tuple(validation_config["official_table_types"])):
            errors.append("来源表缺少官方来源行")
        if (
            not community_absence_stated
            and not has_source_type_row(text, tuple(validation_config["community_table_types"]))
        ):
            errors.append("来源表缺少社区/第三方来源行")
    if not re.search(r"^\|\s*信息\s*\|\s*来源\s*\|\s*类型\s*\|\s*访问日期\s*\|\s*可信度\s*\|", text, re.MULTILINE):
        errors.append("缺少来源与可信度表头")

    format_markers = validation_config.get("format_requirement_markers", [])
    min_format_markers = int(validation_config.get("min_format_requirement_markers", 0) or 0)
    if min_format_markers and format_markers:
        marker_count = count_markers(text, list(format_markers))
        if marker_count < min_format_markers:
            errors.append(
                "投稿形式要求覆盖不足: "
                f"需要至少 {min_format_markers} 类格式要点，实际命中 {marker_count} 类"
            )

    article_type_markers = validation_config.get("article_type_requirement_markers", [])
    min_article_type_markers = int(
        validation_config.get("min_article_type_requirement_markers", 0) or 0
    )
    if min_article_type_markers and article_type_markers:
        article_type_section = extract_heading_section(text, "目标文体/文章类型具体要求")
        marker_count = count_markers(article_type_section, list(article_type_markers))
        if marker_count < min_article_type_markers:
            errors.append(
                "目标文体/文章类型要求覆盖不足: "
                f"需要至少 {min_article_type_markers} 类具体要点，实际命中 {marker_count} 类"
            )

    result = {
        "report": str(report_path),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "unique_url_count": len(urls),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
