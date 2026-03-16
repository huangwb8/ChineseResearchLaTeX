#!/usr/bin/env python3
"""Sync the canonical GitHub repository state to a Gitee mirror."""

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


def verify_remote_refs(repo_root: Path, remote_name: str, branch: str, tag: str | None) -> None:
    refs = [f"refs/heads/{branch}"]
    if tag:
        refs.append(f"refs/tags/{tag}")
    result = run_git(["ls-remote", remote_name, *refs], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != len(refs):
        raise RuntimeError(f"Remote verification failed for refs: {', '.join(refs)}")


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

    tag = args.tag.strip() or infer_latest_tag(repo_root)
    refspecs = build_refspecs(args.branch, tag)

    if args.dry_run:
        print(f"repo_root={repo_root}")
        print(f"remote_name={args.remote_name}")
        print(f"remote_url={remote_url}")
        print("refspecs=" + ",".join(refspecs))
        return 0

    ensure_remote(repo_root, args.remote_name, remote_url)
    push_with_retry(
        repo_root,
        args.remote_name,
        refspecs,
        force=not args.no_force,
        retries=args.retries,
        delay_seconds=args.retry_delay,
    )
    verify_remote_refs(repo_root, args.remote_name, args.branch, tag)

    print(f"Synced branch '{args.branch}' to {remote_url}")
    if tag:
        print(f"Synced tag '{tag}' to {remote_url}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
