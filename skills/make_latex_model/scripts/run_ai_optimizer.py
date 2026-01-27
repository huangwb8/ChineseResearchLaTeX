#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 优化器入口（单轮）

用途：
- 在已有 baseline + 已编译 main.pdf 的前提下，执行一次“分析→决策→应用→（可选）验证”
- 便于独立调试 AIOptimizer（不必跑完整 enhanced_optimize 流程）

示例：
  python3 skills/make_latex_model/scripts/run_ai_optimizer.py --project NSFC_Local --iteration 1 --mode heuristic
  python3 skills/make_latex_model/scripts/run_ai_optimizer.py --project NSFC_Local --iteration 1 --mode manual_file
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_optimizer import AIOptimizer


def compile_project(project_path: Path) -> bool:
    import subprocess

    main_tex = project_path / "main.tex"
    if not main_tex.exists():
        return False

    compile_steps = [
        ["xelatex", "-interaction=nonstopmode", "main.tex"],
        ["bibtex", "main"],
        ["xelatex", "-interaction=nonstopmode", "main.tex"],
        ["xelatex", "-interaction=nonstopmode", "main.tex"],
    ]

    try:
        for cmd in compile_steps:
            result = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=60)
            if result.returncode != 0 and cmd[0] == "xelatex":
                return False
        return (project_path / "main.pdf").exists()
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="AI 优化器（单轮）")
    parser.add_argument("--project", "-p", required=True, help="项目名称或 projects/ 下相对路径（如 NSFC_Local 或 projects/NSFC_Local）")
    parser.add_argument("--iteration", "-i", type=int, required=True, help="迭代编号（从 1 开始）")
    parser.add_argument("--mode", choices=["heuristic", "manual_file"], default="heuristic", help="决策模式")
    parser.add_argument("--no-eval", action="store_true", help="只应用调整，不做编译/对比验证（不推荐）")
    parser.add_argument("--current-ratio", type=float, default=None, help="当前差异比例（0-1），不填则从 diff_features.json 读取")
    args = parser.parse_args()

    skill_root = Path(__file__).parent.parent
    repo_root = skill_root.parent.parent
    projects_root = (repo_root / "projects").resolve()

    raw = str(args.project).strip()
    p = Path(raw)
    if p.is_absolute() or any(sep in raw for sep in ("/", "\\")):
        project_path = p if p.is_absolute() else (repo_root / p)
    else:
        project_path = repo_root / "projects" / raw

    project_path = project_path.resolve()
    try:
        project_path.relative_to(projects_root)
    except Exception:
        print(f"❌ --project 必须位于 {projects_root} 下: {args.project}")
        return 1

    config_path = project_path / "extraTex" / "@config.tex"

    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return 1

    project_key = project_path.name

    # 读取当前 ratio（优先使用入参）
    current_ratio = args.current_ratio
    if current_ratio is None:
        features_path = skill_root / "workspace" / project_key / "iterations" / f"iteration_{args.iteration:03d}" / "diff_features.json"
        if features_path.exists():
            import json

            data = json.loads(features_path.read_text(encoding="utf-8"))
            current_ratio = float(data.get("avg_diff_ratio", 1.0))
        else:
            current_ratio = 1.0

    optimizer = AIOptimizer(
        skill_root=skill_root,
        project_name=project_key,
        mode=args.mode,
        evaluate_after_apply=not args.no_eval,
    )

    def _compile() -> bool:
        return compile_project(project_path)

    def _compare() -> float:
        # 复用 compare_pdf_pixels 脚本输出（enhanced_optimize 会把 baseline 放入 workspace/baseline/word.pdf）
        import subprocess
        import json

        baseline_pdf = skill_root / "workspace" / project_key / "baseline" / "word.pdf"
        output_pdf = project_path / "main.pdf"
        if not baseline_pdf.exists() or not output_pdf.exists():
            return None

        iter_dir = skill_root / "workspace" / project_key / "iterations" / f"iteration_{args.iteration:03d}"
        iter_dir.mkdir(parents=True, exist_ok=True)
        json_out = iter_dir / "pixel_compare.json"
        features_out = iter_dir / "diff_features.json"

        cmd = [
            "python3",
            str(skill_root / "scripts" / "compare_pdf_pixels.py"),
            str(baseline_pdf),
            str(output_pdf),
            "--json-out",
            str(json_out),
            "--features-out",
            str(features_out),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return None

        data = json.loads(json_out.read_text(encoding="utf-8"))
        return float(data.get("avg_diff_ratio", 1.0))

    result = optimizer.optimize_iteration(
        iteration=args.iteration,
        current_ratio=current_ratio,
        config_path=config_path,
        compile_func=_compile,
        compare_func=_compare,
    )

    print(f"状态: {result.status}")
    if result.new_ratio is not None:
        print(f"新差异: {result.new_ratio:.2%}")
    if result.reason:
        print(f"原因: {result.reason}")
    return 0 if result.status in ("success", "neutral") else 2


if __name__ == "__main__":
    raise SystemExit(main())
