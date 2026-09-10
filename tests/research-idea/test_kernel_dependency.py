"""research-idea 的 Kernel 最低版本与原生声明加载回归。"""
from pathlib import Path

import yaml
from bensz_skill_kernel.states import SkillStateDeclaration


ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = ROOT / "skills/research-idea"


def load_config():
    return yaml.safe_load((SKILL_ROOT / "config.yaml").read_text(encoding="utf-8"))


def test_kernel_dependency_uses_minimum_version_range():
    config = load_config()
    assert config["dependencies"]["kernel"] == {
        "name": "bensz-skill-kernel",
        "version": ">=1.0.3",
    }
    assert "kernel" not in config["runtime"]


def test_kernel_1_0_3_can_load_native_runtime_declaration():
    declaration = SkillStateDeclaration.from_skill_root(SKILL_ROOT)
    assert declaration.initial_state == "bensz.research-ideation.literature"
    assert declaration.verifier_requirements() == (
        {
            "id": "bensz.research.stage-readiness",
            "version": "3.0.0",
            "required": True,
        },
    )
