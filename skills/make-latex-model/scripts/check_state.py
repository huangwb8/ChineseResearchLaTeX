#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目状态检查工具
AI 调用技能前执行此脚本，了解项目当前状态
"""

import sys
import json
from pathlib import Path
from datetime import datetime

import yaml

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent.parent
PROJECTS_ROOT = (REPO_ROOT / "projects").resolve()

sys.path.insert(0, str(SKILL_DIR))

from scripts.core.workspace_manager import WorkspaceManager


def load_skill_config() -> dict:
    """读取 skill 配置。"""
    config_path = SKILL_DIR / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def detect_product_line(project_path: Path, config: dict) -> str:
    """根据 config.yaml 的规则识别产品线。"""
    rules = config.get("product_line_rules") or {}
    haystacks = [project_path.name.lower()]
    try:
        haystacks.append(str(project_path.relative_to(PROJECTS_ROOT)).lower())
    except Exception:
        pass

    for product_line, rule in rules.items():
        for pattern in rule.get("detect_patterns", []):
            pattern_lc = str(pattern).lower()
            if any(pattern_lc in haystack for haystack in haystacks):
                return product_line
    return "unknown"


def get_required_markers(config: dict, product_line: str) -> list[str]:
    rules = config.get("product_line_rules") or {}
    rule = rules.get(product_line) or {}
    return [str(marker) for marker in rule.get("required_markers", [])]


def get_official_build_command(project_path: Path, config: dict, product_line: str) -> str:
    rules = config.get("product_line_rules") or {}
    commands = config.get("official_build_commands") or {}
    rule = rules.get(product_line) or {}
    command_key = rule.get("official_build_key", product_line)
    command = commands.get(command_key)
    if not command:
        return ""
    return command.replace("<project>", str(project_path.relative_to(REPO_ROOT)))


def check_project_state(project_path: Path) -> dict:
    """检查项目当前状态"""
    project_path = project_path.resolve()
    config = load_skill_config()
    product_line = detect_product_line(project_path, config)
    required_markers = get_required_markers(config, product_line)
    marker_status = {marker: (project_path / marker).exists() for marker in required_markers}
    official_build_command = get_official_build_command(project_path, config, product_line)

    state = {
        "project_path": str(project_path),
        "check_time": datetime.now().isoformat(),
        "status": {},
        "recommendations": []
    }

    ws_manager = WorkspaceManager(SKILL_DIR)
    ws_root = ws_manager.get_project_workspace(project_path)

    # 1. 检查项目是否已初始化（按产品线规则，而不是硬编码 NSFC）
    state["status"]["product_line"] = product_line
    state["status"]["required_markers"] = marker_status
    state["status"]["official_build_command"] = official_build_command
    state["status"]["initialized"] = all(marker_status.values()) if marker_status else (project_path / "main.tex").exists()
    if not state["status"]["initialized"]:
        missing_markers = [marker for marker, exists in marker_status.items() if not exists]
        if missing_markers:
            state["recommendations"].append(
                f"项目初始化标记不完整（产品线: {product_line}），缺少: {', '.join(missing_markers)}"
            )
        else:
            state["recommendations"].append("项目未初始化，请先补齐该产品线的入口文件")

    # 2. 检查是否有 PDF 基准（推荐 baseline.pdf；兼容 word.pdf）
    baseline_dir = ws_root / "baselines"
    pdf_files = list(baseline_dir.glob("*.pdf")) if baseline_dir.exists() else []
    state["status"]["has_baseline"] = len(pdf_files) > 0
    state["status"]["baseline_source"] = "unknown"
    state["status"]["baseline_dir"] = str(baseline_dir)

    if pdf_files:
        # 检测基准来源
        baseline_pdf = next(
            (p for p in pdf_files if p.name.lower() == "baseline.pdf"),
            next((p for p in pdf_files if p.name.lower() == "word.pdf"), pdf_files[0]),
        )
        baseline_info = detect_baseline_source(baseline_pdf)
        state["status"]["baseline_source"] = baseline_info["source"]
        state["status"]["baseline_quality"] = baseline_info["quality"]

        if baseline_info["source"] == "quicklook":
            state["recommendations"].append(
                "⚠️ 检测到 QuickLook 基准，像素对比结果可能不准确，建议使用 Word 导出 PDF"
            )

    if not state["status"]["has_baseline"]:
        preferred_candidates = config.get("baseline", {}).get("preferred_candidates", [])
        preferred_text = "、".join(preferred_candidates) if preferred_candidates else "template/baseline.pdf"
        state["recommendations"].append(
            f"缺少 PDF 基准。可优先提供官方 PDF / Word 导出 PDF / 已验收 baseline PDF，并放到 `{preferred_text}` 之一；旧版 `word.pdf` 路径仍兼容。"
        )

    # 3. 检查编译状态
    main_pdf = project_path / "main.pdf"
    if main_pdf.exists():
        # 检查修改时间
        pdf_time = datetime.fromtimestamp(main_pdf.stat().st_mtime)
        state["status"]["last_compilation"] = pdf_time.isoformat()
        state["status"]["compilation_status"] = "success"  # 简化判断
    else:
        state["status"]["compilation_status"] = "not_compiled"
        if official_build_command:
            state["recommendations"].append(f"项目未编译，建议先执行官方构建命令：{official_build_command}")
        else:
            state["recommendations"].append("项目未编译，建议先执行该产品线的官方构建测试")

    # 4. 检查是否有 PDF 分析结果
    analysis_files = list(baseline_dir.glob("*_analysis.json")) if baseline_dir.exists() else []
    state["status"]["has_analysis"] = len(analysis_files) > 0

    if state["status"]["has_analysis"]:
        latest_analysis = max(analysis_files, key=lambda p: p.stat().st_mtime)
        state["status"]["latest_analysis"] = str(latest_analysis.name)
    else:
        analysis_cmd = config.get("baseline", {}).get("analysis_command", "python skills/make-latex-model/scripts/analyze_pdf.py <baseline.pdf>")
        state["recommendations"].append(
            f"缺少 PDF 分析结果，建议执行: {analysis_cmd}"
        )

    return state


def detect_baseline_source(pdf_path: Path) -> dict:
    """检测 PDF 基准来源"""
    # 简化判断：通过文件名或元数据
    filename = pdf_path.name.lower()

    if "quicklook" in filename or "ql" in filename:
        return {"source": "quicklook", "quality": "low"}
    elif "baseline" in filename:
        return {"source": "baseline_pdf", "quality": "high"}
    elif "word" in filename:
        return {"source": "word_pdf", "quality": "high"}
    else:
        return {"source": "unknown", "quality": "medium"}


def print_report(state: dict):
    """打印状态报告"""
    print(f"\n{'='*60}")
    print("项目状态检查报告")
    print(f"{'='*60}")
    print(f"项目路径: {state['project_path']}")
    print(f"检查时间: {state['check_time']}")
    print(f"产品线: {state.get('status', {}).get('product_line', 'unknown')}")
    build_cmd = state.get("status", {}).get("official_build_command")
    if build_cmd:
        print(f"官方构建命令: {build_cmd}")
    print(f"\n状态概览:")

    status_map = {
        "initialized": ("✅ 已初始化", "❌ 未初始化"),
        "has_baseline": ("✅ 有基准", "❌ 无基准"),
        "compilation_status": ("✅ 编译成功", "⚠️ 未编译"),
        "has_analysis": ("✅ 有分析", "⚠️ 无分析"),
    }

    for key, (yes, no) in status_map.items():
        if key in state["status"]:
            value = state["status"][key]
            if isinstance(value, bool):
                print(f"  {yes if value else no}")
            elif isinstance(value, str):
                print(f"  {key}: {value}")

    baseline_source = state.get("status", {}).get("baseline_source")
    if baseline_source:
        print(f"\n基准来源: {baseline_source}")
        print(f"基准质量: {state.get('status', {}).get('baseline_quality', 'unknown')}")

    required_markers = state.get("status", {}).get("required_markers", {})
    if required_markers:
        print("\n初始化标记:")
        for marker, exists in required_markers.items():
            print(f"  {'✅' if exists else '❌'} {marker}")

    if state["recommendations"]:
        print(f"\n建议:")
        for i, rec in enumerate(state["recommendations"], 1):
            print(f"  {i}. {rec}")

    print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 2:
        print("用法: python check_state.py <project_path>")
        sys.exit(1)

    raw = str(sys.argv[1]).strip()
    p = Path(raw)
    if p.exists():
        project_path = p
    else:
        if p.is_absolute() or any(sep in raw for sep in ("/", "\\")):
            candidate = p if p.is_absolute() else (REPO_ROOT / p)
        else:
            candidate = REPO_ROOT / "projects" / raw
        project_path = candidate

    project_path = project_path.resolve()

    if not project_path.exists():
        print(f"❌ 错误: 项目路径不存在: {project_path}")
        sys.exit(1)

    try:
        project_path.relative_to(PROJECTS_ROOT)
    except Exception:
        print(f"❌ 错误: 项目必须位于 {PROJECTS_ROOT} 下: {project_path}")
        sys.exit(1)

    # 检查状态
    state = check_project_state(project_path)

    # 打印报告
    print_report(state)

    # 导出 JSON（供 AI 程序化读取）
    ws_root = WorkspaceManager(SKILL_DIR).get_project_workspace(project_path)
    output_file = ws_root / "reports" / "state_check.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    print(f"✅ 状态已保存到: {output_file}")


if __name__ == "__main__":
    main()
