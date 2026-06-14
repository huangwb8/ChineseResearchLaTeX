#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config() -> dict:
    config_path = skill_root() / "config.yaml"
    if yaml is None:
        raise SystemExit("缺少 PyYAML，无法读取 research-idea/config.yaml；请安装 pyyaml 后重试")
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def find_skill(skill_name: str, search_roots: list[str], cwd: Path) -> Path | None:
    candidates: list[Path] = []
    for root in search_roots:
        root_path = (cwd if root == "." else Path(root).expanduser()).resolve()
        candidates.append(root_path / skill_name / "SKILL.md")
    for env_name in ("CODEX_HOME", "CLAUDE_HOME"):
        env_value = os.environ.get(env_name)
        if env_value:
            candidates.append(Path(env_value).expanduser().resolve() / "skills" / skill_name / "SKILL.md")
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 research-idea 依赖 skill 是否可发现")
    parser.add_argument("--cwd", default=".", help="用户当前工作目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    config = load_config()
    dependency_config = config.get("dependencies", {})
    required = dependency_config.get("required_skills", [])
    aliases = dependency_config.get("legacy_skill_aliases", {}) or {}
    search_roots = dependency_config.get("search_roots", ["."])
    cwd = Path(args.cwd).expanduser().resolve()
    found: dict[str, str] = {}
    missing: list[str] = []
    for skill_name in required:
        candidates = [skill_name, *[str(item) for item in aliases.get(skill_name, [])]]
        path = None
        resolved_name = skill_name
        for candidate_name in candidates:
            path = find_skill(candidate_name, search_roots, cwd)
            if path is not None:
                resolved_name = candidate_name
                break
        if path is None:
            missing.append(skill_name)
        else:
            found[skill_name] = str(path.parent)
            if resolved_name != skill_name:
                found[f"{skill_name}__legacy_alias"] = resolved_name

    result = {"passed": not missing, "found": found, "missing": missing}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("status=PASS" if result["passed"] else "status=FAIL")
        for skill_name, path in found.items():
            print(f"found={skill_name}:{path}")
        for skill_name in missing:
            print(f"missing={skill_name}")
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
