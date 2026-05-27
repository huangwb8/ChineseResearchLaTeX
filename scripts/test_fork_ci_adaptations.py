from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_readme_template_sync_uses_upstream_release_source() -> None:
    workflow = _read(".github/workflows/update-template-list.yml")

    assert "TARGET_REPO: ${{ inputs.repo || 'huangwb8/ChineseResearchLaTeX' }}" in workflow
    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow


def test_gitee_mirror_skips_successfully_when_unconfigured() -> None:
    workflow = _read(".github/workflows/sync-gitee-mirror.yml")

    assert "id: config" in workflow
    assert "should_sync=false" in workflow
    assert "Gitee mirror is not configured" in workflow
    assert "set repository variable GITEE_REPO or GITEE_REMOTE_URL" in workflow
    assert "set secret GITEE_SSH_PRIVATE_KEY" in workflow
    assert "if: steps.config.outputs.should_sync == 'true'" in workflow
    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow
    assert "webfactory/ssh-agent@v0.10.0" in workflow
