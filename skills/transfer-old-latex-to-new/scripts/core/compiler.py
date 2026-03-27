#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import subprocess
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ERROR_RE = re.compile(r"^! ", re.MULTILINE)
UNDEF_REF_RE = re.compile(r"LaTeX Warning: Reference `[^']+' on page")
UNDEF_CITE_RE = re.compile(r"LaTeX Warning: Citation `[^']+' on page")


@dataclass(frozen=True)
class CompileStep:
    command: List[str]
    returncode: int
    stdout_path: str
    stderr_path: str


@dataclass(frozen=True)
class CompileSummary:
    success: bool
    steps: List[CompileStep]
    error_count: int
    undefined_ref_count: int
    undefined_cite_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "error_count": self.error_count,
            "undefined_ref_count": self.undefined_ref_count,
            "undefined_cite_count": self.undefined_cite_count,
            "steps": [asdict(s) for s in self.steps],
        }


def _run(cmd: List[str], cwd: Path, stdout_path: Path, stderr_path: Path, timeout_s: int) -> int:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=stdout_path.open("w", encoding="utf-8"),
        stderr=stderr_path.open("w", encoding="utf-8"),
        timeout=timeout_s,
        check=False,
        env=os.environ.copy(),
        text=True,
    )
    return int(p.returncode)


def compile_project(new_project: Path, logs_dir: Path, config: Dict[str, Any]) -> CompileSummary:
    new_project = new_project.resolve()
    logs_dir = logs_dir.resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 创建 LaTeX 中间文件目录(与日志分离)
    latex_aux_dir = logs_dir / "latex_aux"
    latex_aux_dir.mkdir(parents=True, exist_ok=True)

    compilation = config.get("compilation", {}) or {}
    engine = str(compilation.get("engine", "xelatex"))
    interaction = str(compilation.get("interaction_mode", "nonstopmode"))
    pass_sequence = compilation.get("pass_sequence") or ["xelatex", "bibtex", "xelatex", "xelatex"]
    halt_on_error = bool(compilation.get("halt_on_error", False))
    timeout_per_pass = int(compilation.get("timeout_per_pass", 120))
    total_timeout = int(compilation.get("total_timeout", 0) or 0)
    passes = compilation.get("passes")
    if passes is not None:
        try:
            pass_count = int(passes)
            if pass_count > 0:
                pass_sequence = list(pass_sequence)[:pass_count]
        except Exception:
            pass

    steps: List[CompileStep] = []
    start_time = time.time()

    for idx, step in enumerate(pass_sequence, start=1):
        remaining_total = None
        if total_timeout > 0:
            elapsed = time.time() - start_time
            remaining_total = total_timeout - int(elapsed)
            if remaining_total <= 0:
                stdout_path = logs_dir / f"compile_{idx}_{step}.out.txt"
                stderr_path = logs_dir / f"compile_{idx}_{step}.err.txt"
                stdout_path.write_text("", encoding="utf-8")
                stderr_path.write_text("total_timeout\n", encoding="utf-8")
                steps.append(
                    CompileStep(
                        command=[step],
                        returncode=124,
                        stdout_path=str(stdout_path),
                        stderr_path=str(stderr_path),
                    )
                )
                break

        timeout = min(timeout_per_pass, remaining_total) if remaining_total else timeout_per_pass

        if step in {"bibtex", "biber"}:
            # bibtex/biber 需要在 latex_aux_dir 中运行(因为 .aux/.bcf 文件在那里)
            cmd = [step, "main"]
            run_cwd = latex_aux_dir
        else:
            # xelatex 使用 -output-directory 参数将中间文件写到隔离目录
            cmd = [
                step,
                f"-interaction={interaction}",
                f"-output-directory={latex_aux_dir}",
                "main.tex",
            ]
            run_cwd = new_project

        stdout_path = logs_dir / f"compile_{idx}_{step}.out.txt"
        stderr_path = logs_dir / f"compile_{idx}_{step}.err.txt"

        try:
            # bibtex 在 latex_aux_dir 运行时，.aux 内的 bst/bib 路径通常是相对 new_project 的；
            # 通过 BSTINPUTS/BIBINPUTS 将 new_project 加入搜索路径，避免 “I couldn't open style/database file”。
            if step in {"bibtex", "biber"}:
                env = os.environ.copy()
                for key in ("BSTINPUTS", "BIBINPUTS"):
                    existing = env.get(key, "")
                    prefix = str(new_project) + os.pathsep
                    env[key] = prefix + existing
                rc = subprocess.run(
                    cmd,
                    cwd=str(run_cwd),
                    stdout=stdout_path.open("w", encoding="utf-8"),
                    stderr=stderr_path.open("w", encoding="utf-8"),
                    timeout=timeout,
                    check=False,
                    text=True,
                    env=env,
                ).returncode
                rc = int(rc)
            else:
                rc = _run(cmd, cwd=run_cwd, stdout_path=stdout_path, stderr_path=stderr_path, timeout_s=timeout)
        except FileNotFoundError:
            # 缺少 xelatex/bibtex 等环境时，输出可读错误
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text(f"command not found: {cmd[0]}\n", encoding="utf-8")
            rc = 127
        except subprocess.TimeoutExpired:
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text("timeout\n", encoding="utf-8")
            rc = 124

        steps.append(
            CompileStep(
                command=cmd,
                returncode=rc,
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
            )
        )

        if rc != 0 and halt_on_error:
            # 用户选择遇到错误立即中止
            break

    # 简易汇总：读取 main.log（若存在）统计未定义引用等
    # 注意：main.log 现在在 latex_aux_dir 中，但 main.pdf 仍在 new_project 中
    log_path = latex_aux_dir / "main.log"
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    error_count = len(ERROR_RE.findall(log_text))
    undef_ref = len(UNDEF_REF_RE.findall(log_text))
    undef_cite = len(UNDEF_CITE_RE.findall(log_text))

    # 将生成的 PDF 复制到项目根目录（方便用户查看）
    pdf_source = latex_aux_dir / "main.pdf"
    pdf_target = new_project / "main.pdf"
    if pdf_source.exists():
        import shutil
        shutil.copy2(pdf_source, pdf_target)

    success = steps and all(s.returncode == 0 for s in steps) and error_count == 0

    return CompileSummary(
        success=bool(success),
        steps=steps,
        error_count=error_count,
        undefined_ref_count=undef_ref,
        undefined_cite_count=undef_cite,
    )
