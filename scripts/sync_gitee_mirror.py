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
    return f"git@{host}:{normalize_repo(repo)}.git"


def build_refspecs(branch: str, tag: str | None) -> list[str]:
    refspecs = [f"HEAD:refs/heads/{branch}"]
    if tag:
        refspecs.append(f"refs/tags/{tag}:refs/tags/{tag}")
    return refspecs


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def ensure_git_repo(repo_root: Path) -> None:
    result = run_git(["rev-parse", "--is-inside-work-tree"], repo_root)
    if result.returncode != 0 or result.stdout.strip() != "true":
        raise RuntimeError(f"Not a git repository: {repo_root}")


def ensure_remote(repo_root: Path, remote_name: str, remote_url: str) -> None:
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
    result = run_git(["describe", "--tags", "--abbrev=0"], repo_root)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def resolve_local_ref(repo_root: Path, ref: str) -> str:
    result = run_git(["rev-parse", ref], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Unable to resolve {ref}")
    return result.stdout.strip()


def resolve_remote_ref(repo_root: Path, remote_name: str, ref: str) -> str | None:
    result = run_git(["ls-remote", remote_name, ref], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    line = next((item for item in result.stdout.splitlines() if item.strip()), "")
    if not line:
        return None
    return line.split()[0]


def branch_needs_sync(repo_root: Path, remote_name: str, branch: str) -> bool:
    local_sha = resolve_local_ref(repo_root, "HEAD")
    remote_sha = resolve_remote_ref(repo_root, remote_name, f"refs/heads/{branch}")
    return remote_sha != local_sha


def tag_needs_sync(repo_root: Path, remote_name: str, tag: str | None) -> bool:
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
