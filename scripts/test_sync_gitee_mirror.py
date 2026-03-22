from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


sync_script = _load_module("sync_gitee_mirror", REPO_ROOT / "scripts" / "sync_gitee_mirror.py")


def test_normalize_repo_accepts_owner_repo_and_urls():
    assert sync_script.normalize_repo("huangwb8/ChineseResearchLaTeX") == "huangwb8/ChineseResearchLaTeX"
    assert (
        sync_script.normalize_repo("https://gitee.com/huangwb8/ChineseResearchLaTeX.git")
        == "huangwb8/ChineseResearchLaTeX"
    )
    assert (
        sync_script.normalize_repo("git@gitee.com:huangwb8/ChineseResearchLaTeX.git")
        == "huangwb8/ChineseResearchLaTeX"
    )


def test_build_gitee_remote_url_uses_ssh_transport():
    assert (
        sync_script.build_gitee_remote_url("huangwb8/ChineseResearchLaTeX")
        == "git@gitee.com:huangwb8/ChineseResearchLaTeX.git"
    )


def test_build_refspecs_includes_branch_and_optional_tag():
    assert sync_script.build_refspecs("main", None) == ["HEAD:refs/heads/main"]
    assert sync_script.build_refspecs("main", "v4.0.3") == [
        "HEAD:refs/heads/main",
        "refs/tags/v4.0.3:refs/tags/v4.0.3",
    ]


def test_main_does_not_infer_latest_tag_when_tag_argument_is_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    recorded: dict[str, list[str]] = {}

    monkeypatch.setattr(sync_script, "ensure_git_repo", lambda repo_root: None)
    monkeypatch.setattr(sync_script, "ensure_remote", lambda *args, **kwargs: None)
    monkeypatch.setattr(sync_script, "branch_needs_sync", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        sync_script,
        "push_with_retry",
        lambda repo_root, remote_name, refspecs, **kwargs: recorded.setdefault("refspecs", refspecs),
    )
    monkeypatch.setattr(sync_script, "verify_remote_refs_match", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        sync_script,
        "infer_latest_tag",
        lambda repo_root: (_ for _ in ()).throw(AssertionError("should not infer latest tag")),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sync_gitee_mirror.py",
            "--repo-root",
            str(tmp_path),
            "--repo",
            "huangwb8/ChineseResearchLaTeX",
            "--tag",
            "",
        ],
    )

    assert sync_script.main() == 0
    assert recorded["refspecs"] == ["HEAD:refs/heads/main"]


def test_verify_remote_refs_match_rejects_branch_commit_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    calls: list[tuple[str, ...]] = []

    class Result:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run_git(args: list[str], cwd: Path):
        calls.append(tuple(args))
        if args == ["rev-parse", "HEAD"]:
            return Result(0, "local-sha\n")
        if args == ["ls-remote", "gitee", "refs/heads/main"]:
            return Result(0, "remote-sha\trefs/heads/main\n")
        raise AssertionError(f"unexpected git args: {args}")

    monkeypatch.setattr(sync_script, "run_git", fake_run_git)

    with pytest.raises(RuntimeError, match="main"):
        sync_script.verify_remote_refs_match(tmp_path, "gitee", "main", None)
