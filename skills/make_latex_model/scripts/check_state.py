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

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent.parent
PROJECTS_ROOT = (REPO_ROOT / "projects").resolve()

sys.path.insert(0, str(SKILL_DIR))

from scripts.core.workspace_manager import WorkspaceManager


def check_project_state(project_path: Path) -> dict:
    """检查项目当前状态"""
    project_path = project_path.resolve()
    state = {
        "project_path": str(project_path),
        "check_time": datetime.now().isoformat(),
        "status": {},
        "recommendations": []
    }

    ws_manager = WorkspaceManager(SKILL_DIR)
    ws_root = ws_manager.get_project_workspace(project_path)

    # 1. 检查项目是否已初始化
    config_file = project_path / "extraTex" / "@config.tex"
    state["status"]["initialized"] = config_file.exists()
    if not state["status"]["initialized"]:
        state["recommendations"].append("项目未初始化，请先创建 @config.tex")

    # 2. 检查是否有 Word PDF 基准
    baseline_dir = ws_root / "baselines"
    pdf_files = list(baseline_dir.glob("*.pdf")) if baseline_dir.exists() else []
    state["status"]["has_baseline"] = len(pdf_files) > 0
    state["status"]["baseline_source"] = "unknown"
    state["status"]["baseline_dir"] = str(baseline_dir)

    if pdf_files:
        # 检测基准来源
        baseline_pdf = next((p for p in pdf_files if p.name.lower() == "word.pdf"), pdf_files[0])
        baseline_info = detect_baseline_source(baseline_pdf)
        state["status"]["baseline_source"] = baseline_info["source"]
        state["status"]["baseline_quality"] = baseline_info["quality"]

        if baseline_info["source"] == "quicklook":
            state["recommendations"].append(
                "⚠️ 检测到 QuickLook 基准，像素对比结果可能不准确，建议使用 Word 导出 PDF"
            )

    if not state["status"]["has_baseline"]:
        state["recommendations"].append(
            "缺少 Word PDF 基准，请先将 Word 模板导出为 PDF 并放到 projects/{project}/.make_latex_model/baselines/word.pdf"
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
        state["recommendations"].append("项目未编译，建议先执行编译测试")

    # 4. 检查是否有 PDF 分析结果
    analysis_files = list(baseline_dir.glob("*_analysis.json")) if baseline_dir.exists() else []
    state["status"]["has_analysis"] = len(analysis_files) > 0

    if state["status"]["has_analysis"]:
        latest_analysis = max(analysis_files, key=lambda p: p.stat().st_mtime)
        state["status"]["latest_analysis"] = str(latest_analysis.name)
    else:
        state["recommendations"].append(
            "缺少 PDF 分析结果，建议执行: python scripts/analyze_pdf.py <baseline.pdf>"
        )

    return state


def detect_baseline_source(pdf_path: Path) -> dict:
    """检测 PDF 基准来源"""
    # 简化判断：通过文件名或元数据
    filename = pdf_path.name.lower()

    if "quicklook" in filename or "ql" in filename:
        return {"source": "quicklook", "quality": "low"}
    elif "word" in filename or "baseline" in filename:
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
