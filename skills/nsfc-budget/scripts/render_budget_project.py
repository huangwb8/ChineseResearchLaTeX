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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from runtime_utils import dump_json, load_config, load_template_meta, resolve_under, safe_rel_path


SECTION_KEYS = ["equipment", "business", "labor", "transfer", "other_source"]
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
    dump_json(path, data)


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


def validate_latex_commands(paragraphs: list[str], allowed_commands: set[str]) -> list[str]:
    errors = []
    for index, paragraph in enumerate(paragraphs, start=1):
        commands = re.findall(r"\\([A-Za-z]+)", paragraph)
        disallowed = sorted({item for item in commands if item not in allowed_commands})
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


def resolve_template(skill_root: Path, template_id: str) -> tuple[Path, dict[str, Any], list[str]]:
    template_dir = resolve_under(skill_root / "models", template_id, label="template_id")
    if not template_dir.exists():
        raise FileNotFoundError(f"template not found: {template_dir}")
    template_meta, warnings = load_template_meta(template_dir)
    if not isinstance(template_meta, dict):
        template_meta = {}
    return template_dir, template_meta, warnings


def prepare_output_dir(output_dir: Path, template_dir: Path, force: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        if not force:
            raise FileExistsError(f"output directory already exists and is not empty: {output_dir}")
        shutil.rmtree(output_dir)
    shutil.copytree(template_dir, output_dir, ignore=TEMPLATE_IGNORE, dirs_exist_ok=False)


def validate_spec(spec_path: Path, spec: dict[str, Any], config: dict[str, Any], skill_root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    errors = []
    warnings = []

    meta = spec.get("meta") or {}
    budget = spec.get("budget") or {}
    sections = spec.get("sections") or {}
    defaults = config.get("defaults") or {}
    rules = config.get("rules") or {}
    validation_cfg = config.get("validation") or {}

    allowed_commands = set(rules.get("allowed_latex_commands") or [])
    budget_mode = str(meta.get("budget_mode") or rules.get("budget_mode_default") or "budget_based")
    if budget_mode not in {"budget_based", "package_based", "historical_budget_based"}:
        errors.append(f"meta.budget_mode 非法：{budget_mode}")

    workdir_raw = meta.get("workdir")
    if not workdir_raw:
        errors.append("meta.workdir 不能为空")
        workdir = None
    else:
        workdir = Path(str(workdir_raw)).expanduser().resolve()
        if not workdir.exists() or not workdir.is_dir():
            errors.append(f"meta.workdir 不存在或不是目录：{workdir}")

    budget_scope = str(meta.get("budget_scope") or "to_be_confirmed")
    if budget_scope not in {"direct", "total", "to_be_confirmed"}:
        errors.append(f"meta.budget_scope 非法：{budget_scope}")

    output_dirname = str(meta.get("output_dirname") or defaults.get("output_dirname") or "budget_output")
    template_id = str(meta.get("template_id") or defaults.get("template_id") or "01")
    if workdir is not None:
        try:
            resolve_under(workdir, output_dirname, label="output_dirname")
        except ValueError as exc:
            errors.append(str(exc))
        intermediate_dir = workdir / str(defaults.get("intermediate_dirname") or ".nsfc-budget")
        try:
            spec_path.resolve().relative_to(intermediate_dir.resolve())
        except Exception:
            errors.append(f"spec 必须位于 {intermediate_dir} 内：{spec_path}")
    try:
        template_dir = resolve_under(skill_root / "models", template_id, label="template_id")
        if not template_dir.exists() or not template_dir.is_dir():
            errors.append(f"template_id 对应模板不存在：{template_id}")
    except ValueError as exc:
        errors.append(str(exc))

    target_chars = defaults.get("target_chars") or {}
    target_min = int(meta.get("target_chars_min", target_chars.get("recommended_min") or 800) or 800)
    target_max = int(meta.get("target_chars_max", target_chars.get("recommended_max") or 1000) or 1000)
    per_section_max = int(meta.get("per_section_max_chars", defaults.get("per_section_max_chars") or 500) or 500)

    budget_amount_keys = {
        "equipment": "equipment_wan",
        "business": "business_wan",
        "labor": "labor_wan",
        "transfer": "transfer_wan",
        "other_source": "other_source_wan",
    }

    section_char_counts = {}
    for key in SECTION_KEYS:
        section = sections.get(key) or {}
        paragraphs = section.get("paragraphs") or []
        if not isinstance(paragraphs, list):
            errors.append(f"sections.{key}.paragraphs 必须是数组")
            paragraphs = []
        command_errors = validate_latex_commands([str(item) for item in paragraphs], allowed_commands)
        errors.extend(f"sections.{key}: {item}" for item in command_errors)

        amount = as_float(section.get("amount_wan"))
        if amount is None:
            warnings.append(f"sections.{key}.amount_wan 未填写，按 0 处理")
            amount = 0.0

        budget_amount = as_float(budget.get(budget_amount_keys[key]))
        if budget_amount is not None and abs(budget_amount - amount) > 1e-6:
            errors.append(f"budget.{budget_amount_keys[key]}={budget_amount:.2f}w 与 sections.{key}.amount_wan={amount:.2f}w 不一致")

        if bool(validation_cfg.get("require_section_text_when_amount_positive", True)) and amount > 0 and not [item for item in paragraphs if collapse_whitespace(str(item))]:
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
    tolerance = as_float(budget.get("requested_total_tolerance_wan")) or float(defaults.get("requested_total_tolerance_wan") or 1.0)

    if direct_costs_total is not None and abs(direct_sum - direct_costs_total) > 1e-6:
        errors.append(f"设备/业务/劳务之和为 {direct_sum:.2f}w，与 meta.direct_costs_total_wan={direct_costs_total:.2f}w 不一致")

    if budget_scope == "direct" and requested_total is not None and abs(direct_sum - requested_total) > tolerance:
        errors.append(f"预算口径为 direct，但直接费用合计 {direct_sum:.2f}w 与 requested_total_wan={requested_total:.2f}w 差值超过 {tolerance:.2f}w")

    if budget_scope == "total" and direct_costs_total is None:
        warnings.append("budget_scope=total，但未填写 direct_costs_total_wan，暂无法检查总额与说明书口径的一致性")

    if transfer > direct_sum and direct_sum > 0:
        errors.append(f"合作研究转拨资金 {transfer:.2f}w 不应大于直接费用合计 {direct_sum:.2f}w")

    equipment_ratio_warning = float(validation_cfg.get("equipment_ratio_warning") or 0.50)
    if direct_sum > 0 and equipment / direct_sum > equipment_ratio_warning:
        warnings.append(f"设备费占直接费用比例约为 {equipment / direct_sum:.1%}，请核对是否符合当年政策与单位要求")

    total_chars = sum(section_char_counts.values())
    if total_chars < target_min or total_chars > target_max:
        warnings.append(f"正文总可见字符数为 {total_chars}，当前推荐区间为 {target_min}–{target_max}")

    normalized = {
        "workdir": str(workdir) if workdir else "",
        "output_dirname": output_dirname,
        "template_id": template_id,
        "section_char_counts": section_char_counts,
        "total_chars": total_chars,
        "direct_sum_wan": direct_sum,
        "transfer_wan": transfer,
        "other_source_wan": other_source,
        "budget_scope": budget_scope,
    }
    return errors, warnings, normalized


def write_sections(output_dir: Path, sections: dict[str, Any], section_files: dict[str, str], zero_text: dict[str, str]) -> None:
    for key, relative_path in section_files.items():
        section = sections.get(key) or {}
        paragraphs = [str(item) for item in (section.get("paragraphs") or [])]
        content = render_paragraphs(paragraphs, str(zero_text[key]))
        target_path = resolve_under(output_dir, relative_path, label=f"section_files.{key}")
        target_path.write_text(content, encoding="utf-8")


def compile_project(output_dir: Path, latex_entry: str, build_dir: Path, runs: int) -> None:
    try:
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
    except FileNotFoundError as exc:
        raise RuntimeError("xelatex 不可用，请先安装 TeX Live/MacTeX 并确保 xelatex 在 PATH 中") from exc


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
    save_json(run_dir / "budget_spec.snapshot.json", spec)


def render_from_spec(spec_path: Path, force: bool = False, skip_compile: bool = False) -> dict[str, Any]:
    skill_root = Path(__file__).resolve().parents[1]
    config, config_warnings = load_config(skill_root)
    spec = load_json(spec_path)
    errors, warnings, normalized = validate_spec(spec_path, spec, config, skill_root)
    warnings.extend(config_warnings)
    run_dir = spec_path.parent
    template_dir = None
    template_meta: dict[str, Any] = {}
    if not errors:
        try:
            template_dir, template_meta, template_warnings = resolve_template(skill_root, normalized["template_id"])
            warnings.extend(template_warnings)
        except Exception as exc:
            errors.append(str(exc))
    write_report(run_dir, spec, normalized, errors, warnings)
    if errors:
        raise ValueError("spec validation failed")

    workdir = Path(normalized["workdir"])
    output_dir = resolve_under(workdir, normalized["output_dirname"], label="output_dirname")
    assert template_dir is not None
    prepare_output_dir(output_dir, template_dir, force=force)

    output_cfg = config.get("output") or {}
    rules_cfg = config.get("rules") or {}
    section_files = template_meta.get("section_files") or output_cfg.get("section_files") or {}
    if sorted(section_files.keys()) != sorted(SECTION_KEYS):
        raise ValueError(f"section_files 配置不完整：{section_files}")
    for key, relative_path in section_files.items():
        safe_rel_path(str(relative_path), label=f"section_files.{key}")
    zero_text = rules_cfg.get("zero_text") or {}
    if sorted(zero_text.keys()) != sorted(SECTION_KEYS):
        raise ValueError(f"zero_text 配置不完整：{zero_text}")

    write_sections(output_dir, spec.get("sections") or {}, section_files, zero_text)

    if not skip_compile:
        latex_entry = str(template_meta.get("latex_entry") or output_cfg.get("latex_entry") or "budget.tex")
        pdf_name = str(template_meta.get("pdf_name") or output_cfg.get("pdf_name") or "budget.pdf")
        safe_rel_path(latex_entry, label="latex_entry")
        safe_rel_path(pdf_name, label="pdf_name")
        build_dir = run_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        compile_project(output_dir, latex_entry, build_dir, runs=int((config.get("defaults") or {}).get("compile_runs") or 2))
        compiled_pdf = build_dir / pdf_name
        if not compiled_pdf.exists():
            raise FileNotFoundError(f"compiled pdf not found: {compiled_pdf}")
        shutil.copy2(compiled_pdf, output_dir / pdf_name)

    manifest = {
        "output_dir": str(output_dir),
        "pdf": str(output_dir / (str(template_meta.get("pdf_name") or output_cfg.get("pdf_name") or "budget.pdf"))) if not skip_compile else None,
        "pdf_generated": not skip_compile,
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
