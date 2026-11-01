#!/usr/bin/env python3
"""用隔离样稿验证公开 CLI；所有运行产物写入已有任务工作区。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/nsfc-justification-writer"
CLI = SKILL / "scripts/run.py"
sys.dont_write_bytecode = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root", required=True, type=Path)
    args = parser.parse_args()
    task = args.task_root.resolve()
    task.relative_to(ROOT / ".bensz-api")
    if not task.is_dir():
        parser.error("请先声明并创建任务工作区")
    output = task / "skill-creator/output"
    output.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="revision-safety-", dir=output))
    project = workspace / "project"
    target = project / "extraTex/1.1.立项依据.tex"
    target.parent.mkdir(parents=True)
    (project / "references").mkdir()
    (project / "references/test.bib").write_text(
        "@misc{known, title={Anonymous test reference}}\n", encoding="utf-8"
    )
    original = "\\subsection{原有合理标题}\n\\label{sec:original}\n原始判断\\cite{known}。\n"
    revised = original.replace("原始判断", "澄清后的判断")
    target.write_text(original, encoding="utf-8")
    proposal = workspace / "proposal.tex"
    proposal.write_text(revised, encoding="utf-8")
    runs = workspace / "runs"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               NSFC_JUSTIFICATION_WRITER_DISABLE_USER_OVERRIDE="1",
               NSFC_JUSTIFICATION_WRITER_RUNS_DIR=str(runs))
    results: list[dict] = []

    def run(name: str, *argv: str, expected: int = 0) -> str:
        command = [sys.executable, str(CLI), "--no-user-override", *argv]
        result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                capture_output=True, timeout=30, check=False)
        text = result.stdout + result.stderr
        # 日志保留项目相对路径，不记录解释器绝对路径或宿主身份。
        text = text.replace(str(ROOT), "<repo>")
        (workspace / f"{name}.txt").write_text(text, encoding="utf-8")
        assert result.returncode == expected, (name, result.returncode, text)
        results.append({"check": name, "exit_code": result.returncode, "passed": True})
        return text

    run("config", "validate-config")
    run("dry-run", "preview", "--project-root", str(project),
        "--proposal-file", str(proposal), "--dry-run")
    assert target.read_text(encoding="utf-8") == original
    assert not runs.exists(), "只读预览不得生成写入记录"
    assert not any(workspace.rglob("backup")), "只读预览不得生成备份"

    run("apply", "preview", "--project-root", str(project), "--proposal-file", str(proposal))
    assert target.read_text(encoding="utf-8") == revised
    logs = list(runs.glob("*/logs/auto_apply.json"))
    assert len(logs) == 1
    record = json.loads(logs[0].read_text(encoding="utf-8"))
    assert Path(record["backup"]).read_text(encoding="utf-8") == original
    run_id = record["run_id"]
    run("diff", "diff", "--project-root", str(project), "--run-id", run_id)
    run("rollback", "rollback", "--project-root", str(project), "--run-id", run_id, "--yes")
    assert target.read_text(encoding="utf-8") == original
    assert any(p.read_text(encoding="utf-8") == revised for p in runs.rglob("*.tex"))

    proposal.write_text(revised.replace("known", "missing"), encoding="utf-8")
    run("missing-key", "preview", "--project-root", str(project),
        "--proposal-file", str(proposal), expected=2)
    assert target.read_text(encoding="utf-8") == original

    proposal.write_text(revised.replace("原有合理标题", "未经授权的新标题"), encoding="utf-8")
    run("structural-change", "preview", "--project-root", str(project),
        "--proposal-file", str(proposal), expected=2)
    assert target.read_text(encoding="utf-8") == original

    proposal.write_text(revised, encoding="utf-8")
    forbidden = project / "main.tex"
    forbidden.write_text(original, encoding="utf-8")
    run("forbidden-target", "preview", "--project-root", str(project),
        "--target-file", "main.tex", "--proposal-file", str(proposal), expected=2)
    assert forbidden.read_text(encoding="utf-8") == original
    outside = workspace / "outside.tex"
    outside.write_text(original, encoding="utf-8")
    run("outside-target", "preview", "--project-root", str(project),
        "--target-file", str(outside), "--proposal-file", str(proposal), expected=2)
    assert outside.read_text(encoding="utf-8") == original

    diagnosis = workspace / "diagnosis.json"
    run("diagnose", "diagnose", "--project-root", str(project), "--json-out", str(diagnosis))
    checks = json.loads(diagnosis.read_text(encoding="utf-8"))["checks"]
    assert checks["citation_ok"] and not checks["structure_check_enabled"]
    run("wordcount", "wordcount", "--project-root", str(project))
    sys.path.insert(0, str(SKILL / "scripts"))
    from core.config_loader import load_config
    from core.coordinator import Coordinator

    config = load_config(SKILL, load_user_override=False)
    assert config["_config_loader"]["yaml_available"], "验证必须实际加载 PyYAML 配置"
    coord = Coordinator(skill_root=SKILL, config=config)
    status = coord.word_count_status(project_root=project)
    assert status["status"] == "unconstrained" and "target" not in status and "tolerance" not in status
    results.append({"check": "unconstrained-wordcount", "passed": True})
    summary = {"checks": results, "passed": len(results), "workspace": str(workspace.relative_to(ROOT))}
    (workspace / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
