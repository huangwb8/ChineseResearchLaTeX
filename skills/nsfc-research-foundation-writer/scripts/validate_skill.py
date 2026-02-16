#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

from _yaml_utils import extract_yaml_list_under_block, extract_yaml_value_under_block


def _err(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def _extract_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return ""
    return parts[0]


def _extract_frontmatter_field(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", frontmatter)
    if not match:
        return None
    return match.group(1).strip().strip('"').strip("'")


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    repo_root = skill_root.parents[1]
    skill_md = skill_root / "SKILL.md"
    config_yaml = skill_root / "config.yaml"

    required_files = [
        skill_md,
        config_yaml,
        skill_root / "README.md",
        skill_root / "CHANGELOG.md",
        skill_root / "references" / "info_form.md",
        skill_root / "references" / "dod_checklist.md",
        skill_root / "references" / "example_output.md",
        skill_root / "scripts" / "_yaml_utils.py",
    ]
    for path in required_files:
        if not path.exists():
            return _err(f"missing required file: {path}")

    skill_text = skill_md.read_text(encoding="utf-8")
    frontmatter = _extract_frontmatter(skill_text)
    if not frontmatter:
        return _err("SKILL.md missing YAML frontmatter block")

    fm_name = _extract_frontmatter_field(frontmatter, "name")
    fm_version = _extract_frontmatter_field(frontmatter, "version")
    fm_config = _extract_frontmatter_field(frontmatter, "config")
    fm_references = _extract_frontmatter_field(frontmatter, "references")
    if not fm_name or not fm_version or not fm_config or not fm_references:
        return _err("SKILL.md frontmatter missing required fields: name/version/config/references")

    fm_config_path = Path(fm_config)
    resolved_config_path = (
        (repo_root / fm_config_path) if str(fm_config_path).startswith("skills/") else (skill_root / fm_config_path)
    ).resolve()
    if resolved_config_path != config_yaml.resolve():
        return _err(f"config path mismatch: SKILL.md={resolved_config_path} expected={config_yaml.resolve()}")

    fm_refs_path = Path(fm_references)
    resolved_refs_path = (
        (repo_root / fm_refs_path) if str(fm_refs_path).startswith("skills/") else (skill_root / fm_refs_path)
    ).resolve()
    if not resolved_refs_path.exists() or not resolved_refs_path.is_dir():
        return _err(f"references path invalid: {resolved_refs_path}")

    config_lines = config_yaml.read_text(encoding="utf-8").splitlines()
    cfg_name = extract_yaml_value_under_block(config_lines, "skill_info", "name")
    cfg_version = extract_yaml_value_under_block(config_lines, "skill_info", "version")
    if not cfg_name or not cfg_version:
        return _err("config.yaml missing skill_info.name or skill_info.version")
    if cfg_name != fm_name:
        return _err(f"skill name mismatch: SKILL.md={fm_name} config.yaml={cfg_name}")
    if cfg_version != fm_version:
        return _err(f"skill version mismatch: SKILL.md={fm_version} config.yaml={cfg_version}")

    target_foundation = extract_yaml_value_under_block(config_lines, "targets", "foundation_tex")
    target_conditions = extract_yaml_value_under_block(config_lines, "targets", "conditions_tex")
    if not target_foundation or not target_conditions:
        return _err("config.yaml missing targets.foundation_tex or targets.conditions_tex")

    allowed = extract_yaml_list_under_block(config_lines, "guardrails", "allowed_write_files") or []
    if target_foundation not in allowed or target_conditions not in allowed:
        return _err("config.yaml guardrails.allowed_write_files must include both targets.* paths")

    # Heuristic checks: keep them lightweight; warn rather than fail when ambiguous.
    for needle in [target_foundation, target_conditions, "main.tex", "extraTex/@config.tex"]:
        if needle not in skill_text:
            _warn(f"SKILL.md does not mention expected guardrail/target string: {needle}")

    info_form = (skill_root / "references" / "info_form.md").read_text(encoding="utf-8")
    if re.search(r"(?i)\bNSFC\s*20\d{2}\b", info_form):
        _warn("references/info_form.md contains a year-like token (e.g., 'NSFC 2026'); consider keeping it year-agnostic")

    print("OK: skill validation passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

