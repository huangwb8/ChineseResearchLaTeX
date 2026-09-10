#!/usr/bin/env python3
"""在已声明、已由 bsk 创建的任务目录中初始化研究参数和候选模板。"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import unicodedata
from pathlib import Path

from check_dependencies import load_config, find_skill


def run_git(cwd: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def detect_repo_name(cwd: Path, fallback: str) -> str:
    remote = run_git(cwd, ["config", "--get", "remote.origin.url"])
    if remote:
        tail = remote.rstrip("/").rsplit("/", 1)[-1]
        if tail.endswith(".git"):
            tail = tail[:-4]
        if tail:
            return tail
    top = run_git(cwd, ["rev-parse", "--show-toplevel"])
    if top:
        return Path(top).name
    return cwd.name or fallback


def detect_pr_name(cwd: Path, fallback: str) -> str:
    branch = run_git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch and branch != "HEAD":
        return branch
    return fallback


def sanitize(value: str, *, unsafe_chars: str, fallback: str, max_len: int = 80) -> str:
    value = unicodedata.normalize("NFKC", value.strip() or fallback)
    cleaned = "".join(
        "-" if ch in set(unsafe_chars) or unicodedata.category(ch)[0] == "C" else ch
        for ch in value
    )
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = cleaned.strip(" .-_")
    cleaned = (cleaned or fallback)[:max_len].strip(" .-_")
    reserved = {"CON", "PRN", "AUX", "NUL", "COM1", "LPT1"}
    if cleaned.upper() in reserved:
        cleaned = f"{cleaned}-file"
    return cleaned or fallback


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-label", required=True)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--task-root", required=True, help="复用已由 bsk 初始化的项目内 .bensz-api/task-*")
    parser.add_argument("--output-dir", help="项目内正式报告目录，默认 docs/ideas")
    parser.add_argument("--repo-name")
    parser.add_argument("--pr-name")
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--agents", type=int)
    parser.add_argument("--allow-custom-name", action="store_true")
    parser.add_argument("--skip-dependency-check", action="store_true", help="仅开发测试使用")
    args = parser.parse_args()
    config = load_config()
    cwd = Path(args.cwd).expanduser().resolve()
    relative = Path(args.task_root)
    if relative.is_absolute() or len(relative.parts) != 2 or relative.parts[0] != ".bensz-api" or not relative.name.startswith("task-"):
        parser.error("task-root 必须为项目内 .bensz-api/task-* 相对路径")
    task_root = cwd / relative
    workspace_dir = task_root / "research-idea"
    # 这里只保护本脚本写入范围；工作区与状态均由 bsk 管理。
    write_paths = [task_root / ".workspace.json", workspace_dir / "input/manifest.json", workspace_dir / "output/candidate-schema.json", workspace_dir / "log"]
    for path in write_paths:
        if any(part.is_symlink() for part in [path, *path.parents] if part != cwd and cwd in part.parents):
            parser.error("任务目录不得含符号链接")
        if not path.resolve().is_relative_to(cwd):
            parser.error("任务目录越界")
    if not (task_root / ".workspace.json").is_file():
        parser.error("先执行 bsk workspace init --task-root；本脚本不创建任务根或状态")
    if json.loads((task_root / ".workspace.json").read_text()).get("protocol") != "bensz-api-task-v1":
        parser.error("工作区协议不匹配")
    manifest_path = workspace_dir / "input/manifest.json"
    schema_path = workspace_dir / "output/candidate-schema.json"
    if manifest_path.exists() or schema_path.exists() or (workspace_dir / "manifest.json").exists():
        parser.error("研究资料已存在；读取原参数恢复，不重复初始化或自动迁移旧任务")
    settings = {
        "rounds": args.rounds if args.rounds is not None else config["iteration"]["default_rounds"],
        "agents": args.agents if args.agents is not None else config["iteration"]["default_independent_agents"],
        "allow_custom_name": args.allow_custom_name,
    }
    if any(not 1 <= settings[key] <= 100 for key in ("rounds", "agents")):
        parser.error("rounds/agents 必须为 1..100 的整数")
    if not args.skip_dependency_check:
        deps = config["dependencies"]
        for name in deps["required_skills"]:
            names = [name, *deps.get("legacy_skill_aliases", {}).get(name, [])]
            if not any(find_skill(item, deps["search_roots"], cwd) for item in names):
                parser.error(f"缺少必需 Skill: {name}")
    output_config = config["output"]
    unsafe_chars = output_config["unsafe_filename_chars"]
    repo = sanitize(args.repo_name or detect_repo_name(cwd, output_config["fallback_repo"]), unsafe_chars=unsafe_chars, fallback=output_config["fallback_repo"])
    pr = sanitize(args.pr_name or detect_pr_name(cwd, output_config["fallback_pr"]), unsafe_chars=unsafe_chars, fallback=output_config["fallback_pr"])
    output_dir = (cwd / (args.output_dir or output_config["default_dir"])).resolve()
    if not output_dir.is_relative_to(cwd) or any(part.startswith(".") for part in output_dir.relative_to(cwd).parts):
        parser.error("正式报告目录必须位于项目内且不在隐藏目录；项目外交付由 Agent 按用户授权处理")
    output_path = output_dir / output_config["filename_template"].format(repo=repo, pr=pr, timestamp=dt.datetime.now().strftime(output_config["timestamp_format"]))
    if output_path.exists():
        parser.error("目标报告已存在，拒绝覆盖")
    for folder in ("input", "output", "log"):
        (workspace_dir / folder).mkdir(parents=True, exist_ok=True)
    manifest = {
        "skill": "research-idea",
        "input_label": sanitize(args.input_label, unsafe_chars=unsafe_chars, fallback="input"),
        "repo": repo, "pr": pr, "settings": settings,
        "output_path": output_path.relative_to(cwd).as_posix(),
    }
    with manifest_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    candidate_schema = {
        "report_contract": config["output"]["report_contract"],
        "outcome": "insufficient",
        "exploration": "incomplete",
        "novelty": "incomplete",
        "review": "incomplete",
        "research_goal": {"contribution": "待明确", "decision": "待明确", "resources": {"available": [], "unavailable": [], "unknown": []}},
        "candidates": [],
        "candidate_example": [
            {
                "id": "C1",
                "question": "明确、关键、可研究的科学问题",
                "hypothesis": "可被数据、实验或观察推翻的科学假设",
                "predictions": ["假设成立时应观察到的结果"],
                "falsification": ["能推翻该假设的结果"],
                "novelty_status": "未定",
                "opportunity_refs": ["O1"],
                "paper_refs": ["R1"],
                "value_and_nontriviality": "知识增量与常规解释为何不足",
                "nearest_work_and_delta": "已有答案、剩余未知及差异意义",
                "strongest_alternative": "同样投入的备选与改变排序的条件",
                "confidence_and_investment": "证据深度与已确认资源分开判断",
                "screening_decision": "待评估",
            }
        ]
    }
    (workspace_dir / "output" / "candidate-schema.json").write_text(
        json.dumps(candidate_schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"workspace_dir={workspace_dir}")
    print(f"output_path={output_path}")
    print(f"manifest_path={manifest_path}")


if __name__ == "__main__":
    main()
