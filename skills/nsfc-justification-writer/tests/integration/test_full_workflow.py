import os
import subprocess
import sys
from pathlib import Path


def _make_min_project(tmp_path: Path) -> Path:
    project_root = tmp_path / "proj"
    (project_root / "extraTex").mkdir(parents=True, exist_ok=True)
    (project_root / "references").mkdir(parents=True, exist_ok=True)
    (project_root / "extraTex" / "1.1.立项依据.tex").write_text("\\subsubsection{研究背景}\n\\indent\n", encoding="utf-8")
    return project_root


def _run_cli(skill_root: Path, args: list[str], *, env: dict, cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(skill_root / "scripts" / "run.py")] + args
    return subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True)


def test_full_workflow_coach_includes_example_recommendation(tmp_path: Path) -> None:
    skill_root = Path(__file__).resolve().parents[2]
    project_root = _make_min_project(tmp_path)

    env = os.environ.copy()
    env["NSFC_JUSTIFICATION_WRITER_RUNS_DIR"] = str(tmp_path / "runs")

    r = _run_cli(
        skill_root,
        ["coach", "--project-root", str(project_root), "--stage", "auto", "--topic", "联邦学习 隐私 推理", "--top-k", "1"],
        env=env,
        cwd=skill_root,
    )
    assert r.returncode == 0, r.stderr
    assert "推荐示例" in r.stdout
