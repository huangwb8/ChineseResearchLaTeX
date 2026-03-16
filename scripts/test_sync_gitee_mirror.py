from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


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
