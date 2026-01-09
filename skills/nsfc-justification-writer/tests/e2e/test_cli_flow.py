import os
import subprocess
import sys
from pathlib import Path


def _make_min_project(tmp_path: Path) -> Path:
    project_root = tmp_path / "proj"
    (project_root / "extraTex").mkdir(parents=True, exist_ok=True)
    (project_root / "references").mkdir(parents=True, exist_ok=True)

    tex = r"""
\subsubsection{研究背景}
\justifying\indent
这里是研究背景，不写引用。

\subsubsection{国内外研究现状}
\indent
这里是现状段落，引用示例 \cite{test2020}。

\subsubsection{现有研究的局限性}
\indent
局限性段落：避免国际领先等表述。

\subsubsection{研究切入点}
\indent
切入点段落：承上启下到研究内容。
""".lstrip()
    (project_root / "extraTex" / "1.1.立项依据.tex").write_text(tex, encoding="utf-8")
    (project_root / "extraTex" / "2.1.研究内容.tex").write_text("% stub\n患者\n", encoding="utf-8")
    (project_root / "extraTex" / "3.1.研究基础.tex").write_text("% stub\n病例\n", encoding="utf-8")

    bib = r"""
@article{test2020,
  title={A test paper},
  author={Doe, John},
  journal={Test Journal},
  year={2020},
  doi={10.5555/12345678}
}
""".lstrip()
    (project_root / "references" / "mypaper.bib").write_text(bib, encoding="utf-8")
    return project_root


def _run_cli(skill_root: Path, args: list[str], *, env: dict, cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(skill_root / "scripts" / "run.py")] + args
    return subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True)


def test_cli_basic_flow(tmp_path: Path) -> None:
    skill_root = Path(__file__).resolve().parents[2]
    project_root = _make_min_project(tmp_path)

    env = os.environ.copy()
    env["NSFC_JUSTIFICATION_WRITER_RUNS_DIR"] = str(tmp_path / "runs")

    r = _run_cli(skill_root, ["diagnose", "--project-root", str(project_root)], env=env, cwd=skill_root)
    assert r.returncode == 0, r.stderr
    assert "诊断结果" in r.stdout

    r = _run_cli(
        skill_root,
        ["diagnose", "--project-root", str(project_root), "--html-report", "auto", "--run-id", "testdiag"],
        env=env,
        cwd=skill_root,
    )
    assert r.returncode == 0, r.stderr
    html_path = (tmp_path / "runs" / "testdiag" / "reports" / "diagnose.html").resolve()
    assert html_path.is_file()

    out_info = (tmp_path / "info_form.md").resolve()
    r = _run_cli(skill_root, ["init", "--out", str(out_info)], env=env, cwd=skill_root)
    assert r.returncode == 0, r.stderr
    assert "写作信息表" in out_info.read_text(encoding="utf-8", errors="ignore")

    body_with_missing = "这里新增了引用 \\cite{missingKey}，但 bib 没有。\n"
    body_file = (tmp_path / "body.txt").resolve()
    body_file.write_text(body_with_missing, encoding="utf-8")
    r = _run_cli(
        skill_root,
        [
            "apply-section",
            "--project-root",
            str(project_root),
            "--title",
            "国内外研究现状",
            "--body-file",
            str(body_file),
            "--run-id",
            "testrun",
        ],
        env=env,
        cwd=skill_root,
    )
    assert r.returncode == 2
    assert "缺失引用" in (r.stderr + r.stdout)

    original = (project_root / "extraTex" / "1.1.立项依据.tex").read_text(encoding="utf-8", errors="ignore")
    good_body = "这里是替换后的现状段落，引用仍然是 \\cite{test2020}。\n"
    body_file.write_text(good_body, encoding="utf-8")
    r = _run_cli(
        skill_root,
        [
            "apply-section",
            "--project-root",
            str(project_root),
            "--title",
            "国内外研究现状",
            "--body-file",
            str(body_file),
            "--run-id",
            "testrun2",
            "--log-json",
        ],
        env=env,
        cwd=skill_root,
    )
    assert r.returncode == 0, r.stderr

    r = _run_cli(
        skill_root,
        ["diff", "--project-root", str(project_root), "--run-id", "testrun2"],
        env=env,
        cwd=skill_root,
    )
    assert r.returncode == 0, r.stderr
    assert "@@" in r.stdout

    # 破坏性修改后回滚
    (project_root / "extraTex" / "1.1.立项依据.tex").write_text("BROKEN\n", encoding="utf-8")
    r = _run_cli(
        skill_root,
        ["rollback", "--project-root", str(project_root), "--run-id", "testrun2", "--yes", "--new-run-id", "rb1"],
        env=env,
        cwd=skill_root,
    )
    assert r.returncode == 0, r.stderr
    restored = (project_root / "extraTex" / "1.1.立项依据.tex").read_text(encoding="utf-8", errors="ignore")
    assert restored != "BROKEN\n"
    assert "研究背景" in restored
    assert (tmp_path / "runs" / "rb1" / "backup").is_dir()

