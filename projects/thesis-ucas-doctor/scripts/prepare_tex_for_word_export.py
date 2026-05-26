#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GLOB = "extraTex/*.tex"


@dataclass(frozen=True)
class WorkflowStep:
    name: str
    command: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Word 导出前统一执行 TeX 预处理：空格清理重建 -> 时间单位规范化。"
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=DEFAULT_PROJECT_DIR,
        help="UCAS 项目根目录",
    )
    parser.add_argument(
        "--glob",
        default=DEFAULT_GLOB,
        help="传给 normalize_time_unit_spacing.py 的扫描模式",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际写回文件；默认仅 dry-run",
    )
    return parser.parse_args()


def _quote_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def build_steps(
    python_cmd: str,
    project_dir: Path,
    apply: bool,
    glob_pattern: str = DEFAULT_GLOB,
) -> list[WorkflowStep]:
    fix_spacing_script = project_dir / "scripts" / "fix_spacing.py"
    normalize_script = project_dir / "scripts" / "normalize_time_unit_spacing.py"

    fix_cmd = [python_cmd, str(fix_spacing_script)]
    if not apply:
        fix_cmd.append("--dry-run")

    normalize_cmd = [
        python_cmd,
        str(normalize_script),
        "--project-dir",
        str(project_dir),
        "--glob",
        glob_pattern,
    ]
    if apply:
        normalize_cmd.append("--apply")

    return [
        WorkflowStep("Step 1/2: 空格清理重建", fix_cmd),
        WorkflowStep("Step 2/2: 时间单位规范化", normalize_cmd),
    ]


def run_step(step: WorkflowStep, cwd: Path) -> int:
    print(f"[RUN] {step.name}")
    print(f"$ {_quote_command(step.command)}")
    proc = subprocess.run(
        step.command,
        cwd=str(cwd),
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print(f"[DONE] {step.name} exit={proc.returncode}")
    return proc.returncode


def main() -> int:
    args = parse_args()
    project_dir = args.project_dir.expanduser().resolve()
    fix_spacing_script = project_dir / "scripts" / "fix_spacing.py"
    normalize_script = project_dir / "scripts" / "normalize_time_unit_spacing.py"
    if not project_dir.exists():
        print(f"[ERROR] 项目目录不存在：{project_dir}")
        return 1
    if not fix_spacing_script.exists():
        print(f"[ERROR] fix_spacing.py 不存在：{fix_spacing_script}")
        return 1
    if not normalize_script.exists():
        print(f"[ERROR] normalize_time_unit_spacing.py 不存在：{normalize_script}")
        return 1

    mode = "apply" if args.apply else "dry-run"
    print(f"[INFO] mode={mode} project_dir={project_dir}")
    steps = build_steps(
        sys.executable,
        project_dir,
        apply=args.apply,
        glob_pattern=args.glob,
    )
    for step in steps:
        exit_code = run_step(step, project_dir)
        if exit_code != 0:
            print(f"[STOP] {step.name} 失败，后续步骤已中止。")
            return exit_code
    print("[OK] 预处理链执行完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
