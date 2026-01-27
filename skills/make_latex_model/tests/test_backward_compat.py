#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向后兼容性测试

确保现有 NSFC 项目无需修改即可继续使用新的通用化配置系统
"""

import sys
import re
from pathlib import Path

# 添加 scripts/core 模块到路径（v2.8.0+ 迁移到 scripts/ 下）
core_dir = Path(__file__).parent.parent / "scripts" / "core"
sys.path.insert(0, str(core_dir))

from config_loader import ConfigLoader, load_config


def test_default_config_loading():
    """测试1: 默认配置加载"""
    print("\n=== Test 1: Default Config Loading ===")

    skill_dir = Path(__file__).parent.parent
    config = load_config(skill_dir)

    assert config is not None, "Config should not be None"
    assert "skill_info" in config, "Config should contain skill_info"
    assert config["skill_info"]["name"] == "make_latex_model"
    assert isinstance(config["skill_info"].get("version"), str)
    assert re.match(r"^\d+\.\d+\.\d+$", config["skill_info"]["version"]), "Version should be SemVer-like (x.y.z)"

    print("✅ Default config loaded successfully")
    print(f"   Version: {config['skill_info']['version']}")
    return True


def test_nsfc_young_template_loading():
    """测试2: NSFC 青年基金模板加载"""
    print("\n=== Test 2: NSFC Young Template Loading ===")

    skill_dir = Path(__file__).parent.parent
    project_path = skill_dir.parent.parent / "projects" / "NSFC_Young"

    if not project_path.exists():
        print(f"⚠️  Project path not found: {project_path}")
        print("   Skipping this test")
        return True

    config = load_config(skill_dir, project_path, "nsfc/young")

    assert config is not None, "Config should not be None"
    assert "template" in config, "Config should contain template info"

    # 检查模板继承
    assert config["template"]["name"] == "NSFC_Young"
    assert config["template"]["inherits"] == "nsfc/base"

    # 检查样式配置（应该从基础模板继承）
    assert "style_reference" in config, "Config should contain style_reference"
    assert "colors" in config["style_reference"], "Style reference should contain colors"
    assert config["style_reference"]["colors"]["MsBlue"] == "RGB 0,112,192"

    # 检查标题文字（应该从 young.yaml 覆盖）
    assert "heading_texts" in config["style_reference"]
    assert config["style_reference"]["heading_texts"]["section_1"] == "（一）立项依据与研究内容"

    print("✅ NSFC Young template loaded successfully")
    print(f"   Template: {config['template']['display_name']}")
    print(f"   Inherits: {config['template']['inherits']}")
    return True


def test_template_auto_detection():
    """测试3: 模板自动检测"""
    print("\n=== Test 3: Template Auto-Detection ===")

    skill_dir = Path(__file__).parent.parent
    project_path = skill_dir.parent.parent / "projects" / "NSFC_Young"

    if not project_path.exists():
        print(f"⚠️  Project path not found: {project_path}")
        print("   Skipping this test")
        return True

    # 不指定模板，让系统自动检测
    loader = ConfigLoader(skill_dir, project_path, template_name=None)
    detected_template = loader._detect_template()

    assert detected_template == "nsfc/young", f"Expected 'nsfc/young', got '{detected_template}'"

    config = loader.load()
    assert config["template"]["name"] == "NSFC_Young"

    print("✅ Template auto-detection works correctly")
    print(f"   Detected: {detected_template}")
    return True


def test_config_merge_priority():
    """测试4: 配置合并优先级"""
    print("\n=== Test 4: Config Merge Priority ===")

    skill_dir = Path(__file__).parent.parent
    project_path = skill_dir.parent.parent / "projects" / "NSFC_Young"

    if not project_path.exists():
        print(f"⚠️  Project path not found: {project_path}")
        print("   Skipping this test")
        return True

    # 加载配置（三层合并）
    config = load_config(skill_dir, project_path, "nsfc/young")

    # 验证优先级：项目本地 > 模板 > 默认
    # 1. 默认配置中的项
    assert "validation" in config, "Should have validation from default config"
    assert config["validation"]["max_iterations"] == 3

    # 2. 模板配置中的项
    assert "structure" in config, "Should have structure from template config"
    assert config["structure"]["content_dir"] == "extraTex"

    # 3. 项目本地配置（如果存在）
    local_config_path = project_path / ".template.yaml"
    if local_config_path.exists():
        # 检查本地配置是否正确覆盖
        loader = ConfigLoader(skill_dir, project_path, template_name="nsfc/young")
        local_config = loader._load_yaml(local_config_path)
        if "template" in local_config:
            assert config["template"]["name"] == local_config["template"]["name"]

    print("✅ Config merge priority works correctly")
    print("   Priority: local > template > default")
    return True


def test_backward_compatibility():
    """测试5: 向后兼容性 - 现有项目无需修改"""
    print("\n=== Test 5: Backward Compatibility ===")

    skill_dir = Path(__file__).parent.parent

    # 模拟现有项目的使用方式
    test_projects = ["NSFC_Young", "NSFC_General", "NSFC_Local"]

    for project_name in test_projects:
        project_path = skill_dir.parent.parent / "projects" / project_name

        if not project_path.exists():
            print(f"⚠️  Project not found: {project_name}")
            continue

        # 旧方式：直接使用配置（现在通过模板系统）
        try:
            # 检查是否能自动检测模板
            loader = ConfigLoader(skill_dir, project_path)
            detected = loader._detect_template()

            if detected:
                config = loader.load()
                assert config["template"]["name"] == f"NSFC_{project_name.split('_')[1]}"
                print(f"✅ {project_name}: Compatible (detected {detected})")
            else:
                print(f"⚠️  {project_name}: Template not detected, but config loaded")
        except Exception as e:
            print(f"❌ {project_name}: Failed - {e}")
            return False

    print("✅ Backward compatibility verified")
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Backward Compatibility Test Suite")
    print("=" * 60)

    tests = [
        ("Default Config Loading", test_default_config_loading),
        ("NSFC Young Template Loading", test_nsfc_young_template_loading),
        ("Template Auto-Detection", test_template_auto_detection),
        ("Config Merge Priority", test_config_merge_priority),
        ("Backward Compatibility", test_backward_compatibility),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {name} failed")
        except Exception as e:
            failed += 1
            print(f"❌ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
