from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import sync_vscode_configs as syncer


def test_infer_project_profile_recognizes_gxnsf_project():
    assert syncer.infer_project_profile("GXNSF_General") == "gxnsf"


def test_gxnsf_project_uses_its_own_latex_workshop_wrapper():
    project_dir = REPO_ROOT / "projects" / "GXNSF_General"

    messages = syncer.sync_project(project_dir, check_only=True)
    settings = (project_dir / ".vscode" / "settings.json").read_text(encoding="utf-8")

    assert all(not message.startswith("MISMATCH ") for message in messages)
    assert "scripts/gxnsf_build.py" in settings
    assert "gxnsf build (python)" in settings
