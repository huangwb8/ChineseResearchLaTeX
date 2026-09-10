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
    match = re.search(rf"^##[ \t]+{re.escape(section)}(?:[ \t]|$)[^\n]*$", text, re.MULTILINE)
    if match is None:
        return ""
    next_match = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    if next_match is None:
        return text[match.end() :]
    return text[match.end() : match.end() + next_match.start()]


def extract_candidates(text: str) -> list[str]:
    return [body for _, body in candidate_blocks(text)]


def candidate_blocks(text: str) -> list[tuple[str, str]]:
    section = extract_section(text, "候选评估") or extract_section(text, "多个科学问题-科学假设对")
    headings = list(re.finditer(r"^###[ \t]+([^\n]+)$", section, re.M))
    blocks = []
    for index, heading in enumerate(headings):
        match = re.match(r"(?:候选[ \t]*(?:C)?|C)(\d+)(?=[ \t:：、.\-]|$)", heading[1])
        if match:
            end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
            blocks.append((f"C{int(match[1])}", section[heading.end():end]))
    return blocks


def field_value(text: str, name: str) -> str:
    """读取单行字段及其列表续行；不把下一个字段当作本字段内容。"""
    match = re.search(rf"^(?:[-*][ \t]+)?(?:\*\*)?{re.escape(name)}(?:\*\*)?[：:](?:\*\*)?[ \t]*(.*)$", text, re.M)
    if not match:
        return ""
    rest = text[match.end():]
    end = re.search(r"^(?:#{1,6}[ \t]|(?:[-*][ \t]+)?(?:\*\*)?[^\n:：]{1,40}?(?:\*\*)?[：:])", rest, re.M)
    return (match[1] + (rest[:end.start()] if end else rest)).strip()


def substantive(value: str) -> bool:
    stripped = re.sub(r"[\s*\-:：]", "", value)
    return bool(stripped) and not re.fullmatch(r"(?:\{[^{}]*\}|待填|待补充|TODO|TBD|同上|略|\.{3}|…)+", stripped, re.I)


def without_code_blocks(text: str) -> str:
    """示例中的标题、状态与引用不能充当报告正文。"""
    lines, fence = [], None
    for line in text.splitlines(keepends=True):
        match = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence) and not line[match.end():].strip():
                fence = None
            continue
        if match:
            fence = match[1]
        else:
            lines.append(line)
    return ''.join(lines)


def validate_v2(text: str, config: dict, errors: list[str]) -> dict:
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
    try:
        metadata = yaml.safe_load(match[1]) if match else {}
    except yaml.YAMLError:
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    contract = config['output']['report_contract']
    if metadata.get('report_contract') != contract:
        errors.append(f"报告必须声明 report_contract: {contract}")
    outcome = metadata.get('outcome')
    rules = config['output']['outcomes'].get(outcome) if isinstance(outcome, str) else None
    if rules is None:
        errors.append('未知或缺失的 outcome')
        rules = {'sections': [], 'min_candidates': 0}
    for section in config['output']['common_sections'] + rules['sections']:
        if not substantive(extract_section(text, section)):
            errors.append(f'缺少实质章节: {section}')
    for other, other_rules in config['output']['outcomes'].items():
        if other != outcome:
            for section in other_rules['sections']:
                if has_section(text, section):
                    errors.append(f'章节与业务结论冲突: {section}')
    statuses = {key: metadata.get(key) for key in ('exploration', 'novelty', 'review')}
    for key, value in statuses.items():
        allowed = ('complete', 'incomplete', 'not_required') if key == 'novelty' else ('complete', 'incomplete')
        if value not in allowed:
            errors.append(f'缺少或非法执行状态: {key}')
    eligible = outcome in ('recommended', 'no_qualified')
    if eligible:
        if statuses['exploration'] != 'complete' or statuses['review'] != 'complete':
            errors.append('正式结论要求探索与约定审查均完成')
        if statuses['novelty'] not in (('complete',) if outcome == 'recommended' else ('complete', 'not_required')):
            errors.append('查新未完成不能形成正式结论')
    blocks = candidate_blocks(text)
    ids = [candidate_id for candidate_id, _ in blocks]
    if len(ids) != len(set(ids)):
        errors.append('候选编号重复')
    if len(blocks) < rules['min_candidates']:
        errors.append('可推荐结论至少需要一个完整候选')
    if outcome == 'no_qualified' and blocks:
        errors.append('无合格候选时将已淘汰候选放入淘汰表，不得列为保留候选')
    for candidate_id, body in blocks:
        for marker in config['validation']['v2_candidate_markers']:
            if not substantive(field_value(body, marker)):
                errors.append(f'{candidate_id} 缺少实质字段: {marker}')
        trace = field_value(body, '脉络依据')
        if not re.search(r'\[O\d+\]\(#[^\s)]+\)', trace) or not re.search(r'\[R\d+\]\(#[^\s)]+\)', trace):
            errors.append(f'{candidate_id} 缺少 map 机会或论文引用')
        if outcome == 'recommended':
            novelty = field_value(body, '查新结论')
            if not re.match(r'(?:未研究|部分研究但关键缺口存在)(?:[；;，,。\s]|$)', novelty):
                errors.append(f'{candidate_id} 尚无可保留的查新结论')
    anchor_matches = list(re.finditer(r'<a\s+id=[\"\']([^\"\']+)[\"\']\s*></a>', text))
    anchors = [match[1] for match in anchor_matches]
    definitions = {}
    for index, match in enumerate(anchor_matches):
        end = anchor_matches[index + 1].start() if index + 1 < len(anchor_matches) else len(text)
        label = re.match(r'\s*(?:#{1,6}\s+)?(?:\*\*)?([OR]\d+)(?:\*\*)?(?=[：:\s|])', text[match.end():end])
        if label:
            definitions[match[1]] = label[1]
    if len(anchors) != len(set(anchors)):
        errors.append('引用锚点重复')
    for label, anchor in re.findall(r'\[([OR]\d+)\]\(#([^\s)]+)\)', text):
        if anchor not in anchors:
            errors.append(f'引用不可定位: {label} → #{anchor}')
        elif definitions.get(anchor) != label:
            errors.append(f'引用编号与锚点定义不一致: {label} → #{anchor}')
    if outcome == 'no_qualified':
        for marker in ('评估范围', '淘汰依据', '重新探索', '重启条件'):
            if not substantive(field_value(extract_section(text, '淘汰理由与重启条件'), marker)):
                errors.append(f'无合格候选缺少: {marker}')
    if outcome == 'insufficient':
        for marker in ('关键缺口', '恢复位置'):
            if not substantive(field_value(extract_section(text, '证据缺口与恢复位置'), marker)):
                errors.append(f'阶段性评估缺少: {marker}')
    if statuses['novelty'] == 'not_required' and not substantive(field_value(extract_section(text, '查新摘要'), '免查新依据')):
        errors.append('无需完整查新须说明价值筛选淘汰的证据，不得以成本为由跳过')
    return {'outcome': outcome, 'completion_eligible': eligible and not errors}


def path_is_inside_named_dir(report_path: Path, names: set[str]) -> str | None:
    for parent in report_path.parents:
        if parent.name in names:
            return parent.name
    return None


def validate_report(report_path: Path, *, allow_custom_name: bool = False, project_root: Path | None = None) -> dict:
    """共享结构检查；通过只代表报告格式合格，不代表科研结论成立。"""
    config = load_config()
    report_path = report_path.expanduser().resolve()
    if not report_path.exists() or not report_path.is_file():
        raise SystemExit(f"report 不存在或不是文件: {report_path}")

    text = report_path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    if report_path.suffix.lower() != ".md":
        errors.append("最终报告必须是 Markdown 文件")
    if (
        not allow_custom_name
        and (not report_path.name.startswith("Research-Idea_") or report_path.suffix.lower() != ".md")
    ):
        errors.append("文件名应为 Research-Idea_{github仓库名}_{pr名}_{时间戳}.md")

    try:
        scoped_path = report_path.relative_to(project_root.resolve()) if project_root else report_path
    except ValueError:
        scoped_path = report_path
        errors.append("报告路径超出项目范围")
    inside = path_is_inside_named_dir(scoped_path, {".bensz-api", ".research-idea", "tests", ".parallel-vibe", ".parallel_vibe", "parallel-vibe"})
    if inside is not None:
        errors.append(f"最终报告不得放在中间目录或测试目录内: {inside}")

    for pattern in config["validation"]["forbidden_path_patterns"]:
        if re.search(pattern, text):
            errors.append(f"最终报告不应暴露中间路径: {pattern}")

    text = without_code_blocks(text)

    candidates = extract_candidates(text)
    pair_count = len(candidates)
    # 新报告显式选择结论；历史报告只读兼容，不能用于新运行完成。
    is_v2 = text.startswith('---\n') or has_section(text, '结论与研究目标') or has_section(text, '候选评估')
    outcome_result = {'outcome': 'legacy', 'completion_eligible': False}
    if is_v2:
        outcome_result = validate_v2(text, config, errors)
    else:
        warnings.append('历史报告仅作结构兼容读取；新运行须使用显式业务结论')
        for section in config["output"]["required_sections"]:
            if not has_section(text, section):
                errors.append(f"缺少二级标题: {section}")
        min_pairs = int(config["validation"]["min_question_hypothesis_pairs"])
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
        **outcome_result,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="验证 research-idea 最终 Markdown 报告")
    parser.add_argument("--report", required=True, help="最终 Research-Idea Markdown 文件")
    parser.add_argument("--allow-custom-name", action="store_true", help="用户显式指定输出文件名时放宽文件名模板检查")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    args = parser.parse_args()
    result = validate_report(Path(args.report), allow_custom_name=args.allow_custom_name)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"status={status}")
        print(f"pair_count={result['pair_count']}")
        print(f"outcome={result['outcome']}")
        print(f"completion_eligible={str(result['completion_eligible']).lower()}")
        for error in result["errors"]:
            print(f"error={error}")
        for warning in result["warnings"]:
            print(f"warning={warning}")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
