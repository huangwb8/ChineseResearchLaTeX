#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SECTION_KEYS = ["equipment", "business", "labor", "transfer", "other_source"]
SECTION_TEX_FILES = {
    "equipment": "extraTex/1.1.设备费.tex",
    "business": "extraTex/1.2.业务费.tex",
    "labor": "extraTex/1.3.劳务费.tex",
    "transfer": "extraTex/2.1.合作研究转拨资金.tex",
    "other_source": "extraTex/3.1.其他来源资金.tex",
}
ZERO_TEXT = {
    "equipment": "本项目不列支设备费。",
    "business": "本项目不列支业务费。",
    "labor": "本项目不列支劳务费。",
    "transfer": "本项目无合作研究转拨资金。",
    "other_source": "本项目无其他来源资金。",
}
ALLOWED_COMMANDS = {"linebreak", "BudgetBold"}
TEMPLATE_IGNORE = shutil.ignore_patterns(
    ".DS_Store",
    "*.aux",
    "*.log",
    "*.synctex.gz",
    "budget.pdf",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render NSFC budget project from budget_spec.json.")
    parser.add_argument("--spec", required=True, help="Path to budget_spec.json.")
    parser.add_argument("--force", action="store_true", help="Remove output directory before rendering.")
    parser.add_argument("--skip-compile", action="store_true", help="Skip xelatex compilation.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_allowed_latex(text: str) -> str:
    text = re.sub(r"\\linebreak\{\}", "", text)
    text = re.sub(r"\\BudgetBold\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"[{}]", "", text)
    return collapse_whitespace(text)


def visible_char_count(paragraphs: list[str]) -> int:
    joined = "".join(strip_allowed_latex(item) for item in paragraphs)
    return len(re.sub(r"\s+", "", joined))


def validate_latex_commands(paragraphs: list[str]) -> list[str]:
    errors = []
    for index, paragraph in enumerate(paragraphs, start=1):
        commands = re.findall(r"\\([A-Za-z]+)", paragraph)
        disallowed = sorted({item for item in commands if item not in ALLOWED_COMMANDS})
        if disallowed:
            errors.append(f"第 {index} 段包含未允许的 LaTeX 命令：{', '.join(disallowed)}")
    return errors


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value.strip())
    return None


def render_paragraphs(paragraphs: list[str], fallback: str) -> str:
    effective = [collapse_whitespace(item) for item in paragraphs if collapse_whitespace(item)]
    if not effective:
        effective = [fallback]
    return "\n\n".join(f"\\BudgetParagraph{{{item}}}" for item in effective) + "\n"


def load_template_meta(template_dir: Path) -> dict[str, Any]:
    meta_path = template_dir / ".template.yaml"
    data: dict[str, Any] = {}
    if not meta_path.exists():
        return data
    for raw_line in meta_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.lower() in {"true", "false"}:
            data[key] = value.lower() == "true"
            continue
        if value.startswith(("[", "{")):
            data[key] = json.loads(value)
            continue
        if value.startswith('"') and value.endswith('"'):
            data[key] = json.loads(value)
            continue
        data[key] = value
    return data


def resolve_template(skill_root: Path, template_id: str) -> tuple[Path, dict[str, Any]]:
    template_dir = skill_root / "models" / template_id
    if not template_dir.exists():
        raise FileNotFoundError(f"template not found: {template_dir}")
    return template_dir, load_template_meta(template_dir)


def prepare_output_dir(output_dir: Path, template_dir: Path, force: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        if not force:
            raise FileExistsError(f"output directory already exists and is not empty: {output_dir}")
        shutil.rmtree(output_dir)
    shutil.copytree(template_dir, output_dir, ignore=TEMPLATE_IGNORE, dirs_exist_ok=False)


def validate_spec(spec: dict[str, Any]) -> tuple[list[str], list[str], dict[str, Any]]:
    errors = []
    warnings = []

    meta = spec.get("meta") or {}
    budget = spec.get("budget") or {}
    sections = spec.get("sections") or {}

    workdir_raw = meta.get("workdir")
    if not workdir_raw:
        errors.append("meta.workdir 不能为空")
        workdir = None
    else:
        workdir = Path(str(workdir_raw)).expanduser().resolve()
        if not workdir.exists() or not workdir.is_dir():
            errors.append(f"meta.workdir 不存在或不是目录：{workdir}")

    target_min = int(meta.get("target_chars_min", 800) or 800)
    target_max = int(meta.get("target_chars_max", 1000) or 1000)
    per_section_max = int(meta.get("per_section_max_chars", 500) or 500)

    section_char_counts = {}
    for key in SECTION_KEYS:
        section = sections.get(key) or {}
        paragraphs = section.get("paragraphs") or []
        if not isinstance(paragraphs, list):
            errors.append(f"sections.{key}.paragraphs 必须是数组")
            paragraphs = []
        command_errors = validate_latex_commands([str(item) for item in paragraphs])
        errors.extend(f"sections.{key}: {item}" for item in command_errors)

        amount = as_float(section.get("amount_wan"))
        if amount is None:
            warnings.append(f"sections.{key}.amount_wan 未填写，按 0 处理")
            amount = 0.0

        if amount > 0 and not [item for item in paragraphs if collapse_whitespace(str(item))]:
            errors.append(f"sections.{key} 金额大于 0，但正文段落为空")

        count = visible_char_count([str(item) for item in paragraphs])
        section_char_counts[key] = count
        if count > per_section_max:
            errors.append(f"sections.{key} 可见字符数 {count} 超过上限 {per_section_max}")

    equipment = as_float((sections.get("equipment") or {}).get("amount_wan")) or 0.0
    business = as_float((sections.get("business") or {}).get("amount_wan")) or 0.0
    labor = as_float((sections.get("labor") or {}).get("amount_wan")) or 0.0
    transfer = as_float((sections.get("transfer") or {}).get("amount_wan")) or 0.0
    other_source = as_float((sections.get("other_source") or {}).get("amount_wan")) or 0.0
    direct_sum = round(equipment + business + labor, 4)

    direct_costs_total = as_float(meta.get("direct_costs_total_wan"))
    requested_total = as_float(meta.get("requested_total_wan"))
    tolerance = as_float(budget.get("requested_total_tolerance_wan")) or 1.0
    budget_scope = str(meta.get("budget_scope") or "to_be_confirmed")

    if direct_costs_total is not None and abs(direct_sum - direct_costs_total) > 1e-6:
        errors.append(f"设备/业务/劳务之和为 {direct_sum:.2f}w，与 meta.direct_costs_total_wan={direct_costs_total:.2f}w 不一致")

    if budget_scope == "direct" and requested_total is not None and abs(direct_sum - requested_total) > tolerance:
        errors.append(f"预算口径为 direct，但直接费用合计 {direct_sum:.2f}w 与 requested_total_wan={requested_total:.2f}w 差值超过 {tolerance:.2f}w")

    if budget_scope == "total" and direct_costs_total is None:
        warnings.append("budget_scope=total，但未填写 direct_costs_total_wan，暂无法检查总额与说明书口径的一致性")

    if transfer > direct_sum and direct_sum > 0:
        errors.append(f"合作研究转拨资金 {transfer:.2f}w 不应大于直接费用合计 {direct_sum:.2f}w")

    if direct_sum > 0 and equipment / direct_sum > 0.50:
        warnings.append(f"设备费占直接费用比例约为 {equipment / direct_sum:.1%}，请核对是否符合当年政策与单位要求")

    total_chars = sum(section_char_counts.values())
    if total_chars < target_min or total_chars > target_max:
        warnings.append(f"正文总可见字符数为 {total_chars}，当前推荐区间为 {target_min}–{target_max}")

    normalized = {
        "workdir": str(workdir) if workdir else "",
        "output_dirname": str(meta.get("output_dirname") or "budget_output"),
        "template_id": str(meta.get("template_id") or "01"),
        "section_char_counts": section_char_counts,
        "total_chars": total_chars,
        "direct_sum_wan": direct_sum,
        "transfer_wan": transfer,
        "other_source_wan": other_source,
        "budget_scope": budget_scope,
    }
    return errors, warnings, normalized


def write_sections(output_dir: Path, sections: dict[str, Any]) -> None:
    for key, relative_path in SECTION_TEX_FILES.items():
        section = sections.get(key) or {}
        paragraphs = [str(item) for item in (section.get("paragraphs") or [])]
        content = render_paragraphs(paragraphs, ZERO_TEXT[key])
        (output_dir / relative_path).write_text(content, encoding="utf-8")


def compile_project(output_dir: Path, latex_entry: str, build_dir: Path, runs: int) -> None:
    for _ in range(runs):
        result = subprocess.run(
            [
                "xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={build_dir}",
                latex_entry,
            ],
            cwd=output_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        (build_dir / "xelatex.stdout.log").write_text(result.stdout, encoding="utf-8")
        (build_dir / "xelatex.stderr.log").write_text(result.stderr, encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeError(f"xelatex failed with exit code {result.returncode}")


def write_report(run_dir: Path, spec: dict[str, Any], normalized: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    report_json = {
        "errors": errors,
        "warnings": warnings,
        "normalized": normalized,
    }
    save_json(run_dir / "validation_report.json", report_json)

    lines = [
        "# nsfc-budget 校验报告",
        "",
        f"- 模板 ID：`{normalized['template_id']}`",
        f"- 输出目录：`{normalized['output_dirname']}`",
        f"- 正文总可见字符数：`{normalized['total_chars']}`",
        f"- 直接费用合计：`{normalized['direct_sum_wan']:.2f}w`",
        "",
        "## 各部分字符数",
        "",
    ]
    for key in SECTION_KEYS:
        lines.append(f"- `{key}`：{normalized['section_char_counts'][key]}")
    lines.extend(["", "## Errors", ""])
    if errors:
        lines.extend(f"- {item}" for item in errors)
    else:
        lines.append("- 无")
    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- 无")
    (run_dir / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    save_json(run_dir / "normalized_spec.snapshot.json", spec)


def render_from_spec(spec_path: Path, force: bool = False, skip_compile: bool = False) -> dict[str, Any]:
    skill_root = Path(__file__).resolve().parents[1]
    spec = load_json(spec_path)
    errors, warnings, normalized = validate_spec(spec)
    run_dir = spec_path.parent
    write_report(run_dir, spec, normalized, errors, warnings)
    if errors:
        raise ValueError("spec validation failed")

    workdir = Path(normalized["workdir"])
    output_dir = workdir / normalized["output_dirname"]
    template_dir, template_meta = resolve_template(skill_root, normalized["template_id"])
    prepare_output_dir(output_dir, template_dir, force=force)
    write_sections(output_dir, spec.get("sections") or {})

    if not skip_compile:
        latex_entry = str(template_meta.get("latex_entry") or "budget.tex")
        pdf_name = str(template_meta.get("pdf_name") or "budget.pdf")
        build_dir = run_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        compile_project(output_dir, latex_entry, build_dir, runs=2)
        compiled_pdf = build_dir / pdf_name
        if not compiled_pdf.exists():
            raise FileNotFoundError(f"compiled pdf not found: {compiled_pdf}")
        shutil.copy2(compiled_pdf, output_dir / pdf_name)

    manifest = {
        "output_dir": str(output_dir),
        "pdf": str(output_dir / "budget.pdf"),
        "validation_report": str(run_dir / "validation_report.md"),
    }
    save_json(run_dir / "deliverables_manifest.json", manifest)
    return manifest


def main() -> int:
    args = parse_args()
    spec_path = Path(args.spec).expanduser().resolve()
    if not spec_path.exists():
        print(f"[nsfc-budget] spec not found: {spec_path}", file=sys.stderr)
        return 2
    try:
        manifest = render_from_spec(spec_path, force=args.force, skip_compile=args.skip_compile)
    except Exception as exc:
        print(f"[nsfc-budget] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
