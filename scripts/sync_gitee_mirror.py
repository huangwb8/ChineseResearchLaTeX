#!/usr/bin/env python3
"""将 GitHub 仓库默认分支最新 commit 同步推送到 Gitee 镜像仓库。

支持推送指定 tag 或默认分支的最新 commit。用于 GitHub Actions 自动化流程
（``.github/workflows/sync-gitee-mirror.yml``）和手动同步。

典型用法::

    python sync_gitee_mirror.py                          # 推送默认分支最新 commit
    python sync_gitee_mirror.py --tag v4.0.10            # 同时推送指定 tag
    python sync_gitee_mirror.py --repo huangwb8/ChineseResearchLaTeX
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def normalize_repo(repo: str) -> str:
    """将各种格式的 Gitee 仓库标识归一化为 ``owner/name`` 形式。

    支持的输入格式包括 SSH URL、HTTPS URL 和 ``owner/name`` 简写。
    """
    value = repo.strip()
    prefixes = (
        "git@gitee.com:",
        "ssh://git@gitee.com/",
        "https://gitee.com/",
        "http://gitee.com/",
    )
    for prefix in prefixes:
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    if value.endswith(".git"):
        value = value[:-4]
    value = value.strip("/")
    if value.count("/") != 1:
        raise ValueError(f"Invalid Gitee repo identifier: {repo}")
    return value


def build_gitee_remote_url(repo: str, host: str = "gitee.com") -> str:
    """构建 Gitee SSH 远程 URL（``git@<host>:<owner>/<name>.git``）。"""
    return f"git@{host}:{normalize_repo(repo)}.git"


def build_refspecs(branch: str, tag: str | None) -> list[str]:
    """构建 git push 的 refspec 列表。总是包含分支，tag 非空时追加 tag。"""
    refspecs = [f"HEAD:refs/heads/{branch}"]
    if tag:
        refspecs.append(f"refs/tags/{tag}:refs/tags/{tag}")
    return refspecs


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """执行 git 子命令并返回 CompletedProcess（不检查返回码）。"""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def ensure_git_repo(repo_root: Path) -> None:
    """验证指定路径位于一个有效的 git 工作区内。"""
    result = run_git(["rev-parse", "--is-inside-work-tree"], repo_root)
    if result.returncode != 0 or result.stdout.strip() != "true":
        raise RuntimeError(f"Not a git repository: {repo_root}")


def ensure_remote(repo_root: Path, remote_name: str, remote_url: str) -> None:
    """确保 git remote 存在且 URL 正确。已存在则更新 URL，不存在则添加。"""
    result = run_git(["remote", "get-url", remote_name], repo_root)
    if result.returncode == 0:
        current_url = result.stdout.strip()
        if current_url != remote_url:
            update = run_git(["remote", "set-url", remote_name, remote_url], repo_root)
            if update.returncode != 0:
                raise RuntimeError(update.stderr.strip() or update.stdout.strip())
        return

    create = run_git(["remote", "add", remote_name, remote_url], repo_root)
    if create.returncode != 0:
        raise RuntimeError(create.stderr.strip() or create.stdout.strip())


def infer_latest_tag(repo_root: Path) -> str | None:
    """获取本地仓库的最新 tag 名称（基于 ``git describe --tags --abbrev=0``）。"""
    result = run_git(["describe", "--tags", "--abbrev=0"], repo_root)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def resolve_local_ref(repo_root: Path, ref: str) -> str:
    """解析本地 git ref 为完整的 SHA-1 哈希值。"""
    result = run_git(["rev-parse", ref], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Unable to resolve {ref}")
    return result.stdout.strip()


def resolve_remote_ref(repo_root: Path, remote_name: str, ref: str) -> str | None:
    """通过 ``git ls-remote`` 查询远端 ref 的 SHA-1 哈希值。远端不存在该 ref 时返回 None。"""
    result = run_git(["ls-remote", remote_name, ref], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    line = next((item for item in result.stdout.splitlines() if item.strip()), "")
    if not line:
        return None
    return line.split()[0]


def branch_needs_sync(repo_root: Path, remote_name: str, branch: str) -> bool:
    """判断远端分支是否与本地 HEAD 一致，不一致则说明需要同步。"""
    local_sha = resolve_local_ref(repo_root, "HEAD")
    remote_sha = resolve_remote_ref(repo_root, remote_name, f"refs/heads/{branch}")
    return remote_sha != local_sha


def tag_needs_sync(repo_root: Path, remote_name: str, tag: str | None) -> bool:
    """判断远端 tag 是否与本地一致。tag 为 None 时直接返回 False。"""
    if not tag:
        return False
    local_sha = resolve_local_ref(repo_root, f"refs/tags/{tag}")
    remote_sha = resolve_remote_ref(repo_root, remote_name, f"refs/tags/{tag}")
    return remote_sha != local_sha


def push_with_retry(
    repo_root: Path,
    remote_name: str,
    refspecs: list[str],
    *,
    force: bool,
    retries: int,
    delay_seconds: int,
) -> None:
    """带重试机制的 git push。在指定次数内反复尝试推送，每次失败后等待指定秒数。

    Args:
        repo_root: 本地仓库根目录
        remote_name: 远程名称（如 ``gitee``）
        refspecs: 要推送的 refspec 列表
        force: 是否使用 ``--force`` 强制推送
        retries: 最大重试次数
        delay_seconds: 每次重试之间的等待秒数

    Raises:
        RuntimeError: 所有重试均失败后抛出最后一次的错误信息
    """
    base_cmd = ["push"]
    if force:
        base_cmd.append("--force")
    base_cmd.append(remote_name)
    base_cmd.extend(refspecs)

    last_error = ""
    for attempt in range(1, retries + 1):
        result = run_git(base_cmd, repo_root)
        if result.returncode == 0:
            return
        last_error = (result.stderr or result.stdout).strip()
        if attempt < retries:
            time.sleep(delay_seconds)
    raise RuntimeError(last_error or f"git {' '.join(base_cmd)} failed")


def verify_remote_refs_match(repo_root: Path, remote_name: str, branch: str, tag: str | None) -> None:
    """推送后验证远端分支和 tag 的 SHA-1 是否与本地一致。

    通过 ``git ls-remote`` 查询远端实际状态，与本地 HEAD / tag 进行比较。
    如果不一致则抛出 RuntimeError，说明推送可能未成功生效。

    Args:
        repo_root: 本地仓库根目录
        remote_name: 远程名称
        branch: 要验证的分支名
        tag: 要验证的 tag 名，None 表示不验证 tag

    Raises:
        RuntimeError: 远端引用与本地不一致时
    """
    local_branch_sha = resolve_local_ref(repo_root, "HEAD")
    remote_branch_sha = resolve_remote_ref(repo_root, remote_name, f"refs/heads/{branch}")
    if remote_branch_sha != local_branch_sha:
        raise RuntimeError(
            f"Remote branch '{branch}' mismatch: expected {local_branch_sha}, got {remote_branch_sha or '(missing)'}"
        )

    if tag:
        local_tag_sha = resolve_local_ref(repo_root, f"refs/tags/{tag}")
        remote_tag_sha = resolve_remote_ref(repo_root, remote_name, f"refs/tags/{tag}")
        if remote_tag_sha != local_tag_sha:
            raise RuntimeError(
                f"Remote tag '{tag}' mismatch: expected {local_tag_sha}, got {remote_tag_sha or '(missing)'}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync main branch and release tag to a Gitee mirror.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Git repository root")
    parser.add_argument("--remote-name", default="gitee", help="Git remote name for the Gitee mirror")
    parser.add_argument("--remote-url", default=os.environ.get("GITEE_REMOTE_URL", ""), help="Explicit Gitee remote URL")
    parser.add_argument("--repo", default=os.environ.get("GITEE_REPO", ""), help="Gitee repo in owner/name format")
    parser.add_argument("--host", default=os.environ.get("GITEE_HOST", "gitee.com"), help="Gitee host")
    parser.add_argument("--branch", default=os.environ.get("TARGET_BRANCH", "main"), help="Branch to sync")
    parser.add_argument("--tag", default=os.environ.get("RELEASE_TAG", ""), help="Tag to sync; defaults to latest local tag")
    parser.add_argument("--retries", type=int, default=3, help="Retry count for git push")
    parser.add_argument("--retry-delay", type=int, default=5, help="Delay between retries in seconds")
    parser.add_argument("--no-force", action="store_true", help="Disable force push")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without mutating remotes")
    return parser.parse_args()


def main() -> int:
    """脚本主入口：解析参数 -> 确保远端 -> 检测同步需求 -> 推送 -> 验证。

    执行流程：
    1. 解析命令行参数和环境变量
    2. 验证本地是有效的 git 仓库
    3. 构建 Gitee 远程 URL（优先使用显式参数，其次从 ``GITEE_REPO`` 环境变量推导）
    4. 若 ``--dry-run`` 则打印计划后退出
    5. 确保远程存在且 URL 正确
    6. 检测分支和 tag 是否需要同步
    7. 带重试地推送到 Gitee
    8. 验证远端引用与本地一致

    Returns:
        0 表示成功，非零表示失败
    """
    args = parse_args()
    repo_root = args.repo_root.expanduser().resolve()
    ensure_git_repo(repo_root)

    remote_url = args.remote_url.strip()
    if not remote_url:
        if not args.repo:
            raise RuntimeError("Missing GITEE_REPO or --remote-url")
        remote_url = build_gitee_remote_url(args.repo, host=args.host)

    if args.dry_run:
        tag = args.tag.strip() or None
        print(f"repo_root={repo_root}")
        print(f"remote_name={args.remote_name}")
        print(f"remote_url={remote_url}")
        print("refspecs=" + ",".join(build_refspecs(args.branch, tag)))
        return 0

    ensure_remote(repo_root, args.remote_name, remote_url)
    tag = args.tag.strip() or None
    needs_branch = branch_needs_sync(repo_root, args.remote_name, args.branch)
    needs_tag = tag_needs_sync(repo_root, args.remote_name, tag)
    if not needs_branch and not needs_tag:
        print(f"Gitee mirror is already up to date for branch '{args.branch}'")
        return 0

    refspecs: list[str] = []
    if needs_branch:
        refspecs.append(f"HEAD:refs/heads/{args.branch}")
    if needs_tag and tag:
        refspecs.append(f"refs/tags/{tag}:refs/tags/{tag}")

    push_with_retry(
        repo_root,
        args.remote_name,
        refspecs,
        force=not args.no_force,
        retries=args.retries,
        delay_seconds=args.retry_delay,
    )
    verify_remote_refs_match(repo_root, args.remote_name, args.branch, tag if needs_tag else None)

    if needs_branch:
        print(f"Synced branch '{args.branch}' to {remote_url}")
    if needs_tag and tag:
        print(f"Synced tag '{tag}' to {remote_url}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
