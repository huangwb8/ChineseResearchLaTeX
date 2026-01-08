#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transfer_old_latex_to_new - Smoke Test

验证最小可执行闭环（不依赖 LaTeX 编译环境）：
- 结构分析
- 映射与计划生成
- apply（含备份）
- restore
"""

import json
import tempfile
from pathlib import Path

import sys
import asyncio

skill_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(skill_root))

from core.config_loader import DEFAULT_CONFIG
from core.mapping_engine import compute_structure_diff
from core.migration_plan import build_plan_from_diff
from core.migrator import apply_plan, restore_snapshot
from core.project_analyzer import analyze_project
from core.security_manager import SecurityManager


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_mvp_flow() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        old = root / "old"
        new = root / "new"
        runs = root / "runs"

        _write(
            old / "main.tex",
            r"""
\documentclass{article}
\begin{document}
\input{extraTex/1.1.立项依据}
\end{document}
""".strip()
            + "\n",
        )
        _write(
            old / "extraTex/1.1.立项依据.tex",
            "旧内容：立项依据正文。\n\\label{sec:rationale}\n",
        )

        _write(
            new / "main.tex",
            r"""
\documentclass{article}
\begin{document}
\input{extraTex/1.项目的立项依据}
\end{document}
""".strip()
            + "\n",
        )
        _write(new / "extraTex/1.项目的立项依据.tex", "新模板占位。\n")

        config = dict(DEFAULT_CONFIG)

        old_analysis = analyze_project(old)
        new_analysis = analyze_project(new)

        diff = compute_structure_diff(old_analysis, new_analysis, config)
        diff_dict = diff.to_dict()
        plan = build_plan_from_diff(diff_dict, config, strategy="smart").to_dict()

        security = SecurityManager.for_new_project(new, runs)
        backup_root = runs / "run_x" / "backup"
        result = asyncio.run(
            apply_plan(
                old_project=old,
                new_project=new,
                plan=plan,
                config=config,
                security=security,
                backup_root=backup_root,
            )
        ).to_dict()

        target = new / "extraTex/1.项目的立项依据.tex"
        assert "旧内容：立项依据正文" in target.read_text(encoding="utf-8")
        assert (backup_root / "extraTex/1.项目的立项依据.tex").exists()

        _write(target, "人为改坏。\n")
        restored = restore_snapshot(new_project=new, backup_root=backup_root, security=security)
        assert "extraTex/1.项目的立项依据.tex" in restored
        assert "新模板占位" in target.read_text(encoding="utf-8")

    return True


def main() -> int:
    ok = test_mvp_flow()
    print("✅ smoke test passed" if ok else "❌ smoke test failed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
