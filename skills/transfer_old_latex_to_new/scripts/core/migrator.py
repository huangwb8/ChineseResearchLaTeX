#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .ai_integration import AIIntegration
from .latex_utils import safe_read_text
from .progress_utils import progress
from .reference_validator import validate_migration_reference_integrity
from .resource_manager import copy_resources, scan_project_resources, validate_resource_integrity
from .security_manager import SecurityManager


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


@dataclass(frozen=True)
class ApplyResult:
    applied: List[Dict[str, Any]]
    skipped: List[Dict[str, Any]]
    warnings: List[str]
    resources: Dict[str, Any]  # 资源文件处理结果
    references: Dict[str, Any]  # 引用完整性验证结果
    optimization: List[Dict[str, Any]] = field(default_factory=list)
    adaptation: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applied": self.applied,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "resources": self.resources,
            "references": self.references,
            "optimization": self.optimization,
            "adaptation": self.adaptation,
        }


def snapshot_targets(new_project: Path, backup_root: Path, targets: List[str], security: SecurityManager) -> Dict[str, str]:
    """
    备份目标文件到备份目录

    Returns:
        备份文件映射 {相对路径: 备份文件绝对路径}
    """
    new_project = new_project.resolve()
    backup_root = backup_root.resolve()
    backup_map: Dict[str, str] = {}

    for rel in targets:
        abs_path = (new_project / rel).resolve()
        if not abs_path.exists():
            continue
        security.assert_can_write(abs_path)  # 允许写入的才需要备份
        backup_path = (backup_root / rel).resolve()
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(abs_path, backup_path)
        backup_map[rel] = str(backup_path)

    return backup_map


def restore_snapshot(new_project: Path, backup_root: Path, security: SecurityManager, files: Optional[List[str]] = None) -> List[str]:
    """
    恢复备份文件

    Args:
        new_project: 新项目路径
        backup_root: 备份目录路径
        security: 安全管理器
        files: 要恢复的文件列表（None 表示恢复所有）

    Returns:
        已恢复的文件列表
    """
    restored: List[str] = []
    new_project = new_project.resolve()
    backup_root = backup_root.resolve()

    if not backup_root.exists():
        return restored

    # 如果指定了文件列表，只恢复这些文件
    if files:
        for rel in files:
            backup_path = (backup_root / rel).resolve()
            if not backup_path.exists():
                continue
            target = (new_project / rel).resolve()
            security.assert_can_write(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target)
            restored.append(str(rel).replace("\\", "/"))
        return restored

    # 否则恢复所有文件
    for file_path in backup_root.rglob("*"):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(backup_root)
        target = (new_project / rel).resolve()
        security.assert_can_write(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
        restored.append(str(rel).replace("\\", "/"))

    return restored


def _infer_target_word_count(section_title: str, config: Dict[str, Any]) -> int:
    word_count_config = (config.get("word_count_adaptation", {}) or {}) if isinstance(config, dict) else {}
    targets = (word_count_config.get("targets", {}) or {}) if isinstance(word_count_config, dict) else {}
    if isinstance(targets, dict):
        for key, value in targets.items():
            if key and (key in section_title or section_title in key):
                try:
                    return int(value)
                except Exception:
                    pass

    default_targets = {
        "立项依据": 4000,
        "研究内容": 6000,
        "研究目标": 2000,
        "关键科学问题": 2000,
        "研究方案": 4000,
        "特色与创新": 1500,
        "研究基础": 3000,
        "工作条件": 1500,
    }
    for key, target in default_targets.items():
        if key in section_title or section_title in key:
            return int(target)

    try:
        return int(word_count_config.get("default_target", 3000))
    except Exception:
        return 3000


def _optimization_goals_from_config(config: Dict[str, Any]) -> Dict[str, bool]:
    opt = (config.get("content_optimization", {}) or {}) if isinstance(config, dict) else {}
    types = opt.get("optimization_types", []) if isinstance(opt, dict) else []
    goals = {
        "remove_redundancy": "redundancy" in types,
        "improve_logic": "logic" in types,
        "add_evidence": "evidence" in types,
        "improve_clarity": "clarity" in types,
        "reorganize_structure": "structure" in types,
    }
    # 若未配置 types，默认不开启具体目标（保持最小惊讶）
    if not any(goals.values()):
        return {}
    return goals


async def apply_plan(
    old_project: Path,
    new_project: Path,
    plan: Dict[str, Any],
    config: Dict[str, Any],
    security: SecurityManager,
    backup_root: Path,
    allow_low_confidence: bool = False,
    enable_optimization: bool = False,
    enable_word_count_adaptation: bool = False,
    ai_enabled: bool = True,
) -> ApplyResult:
    tasks = (plan or {}).get("tasks") or []
    placeholder = ((config.get("migration", {}) or {}).get("content_generation", {}) or {}).get(
        "placeholder_text", "\\textbf{[此部分内容需要补充]}"
    )
    verbose = bool((config.get("output", {}) or {}).get("verbose", True)) if isinstance(config, dict) else True

    target_files: List[str] = []
    for t in tasks:
        if t.get("target"):
            target_files.append(t["target"])

    snapshot_targets(new_project, backup_root, target_files, security)

    applied: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    warnings: List[str] = []

    # ========== 第一步：迁移 .tex 内容文件 ==========
    p1 = progress("迁移内容文件", total=len(tasks), enabled=verbose)
    for t in tasks:
        t_type = t.get("type")
        target_rel = t.get("target")
        source_rel = t.get("source")

        if t_type == "needs_manual":
            skipped.append({**t, "skip_reason": "needs_manual"})
            p1.update()
            continue

        if t.get("confidence") == "low" and not allow_low_confidence:
            skipped.append({**t, "skip_reason": "low_confidence"})
            p1.update()
            continue

        if not target_rel:
            skipped.append({**t, "skip_reason": "missing_target"})
            p1.update()
            continue

        target_abs = (new_project / target_rel).resolve()
        security.assert_can_write(target_abs)

        if t_type == "copy_one_to_one":
            if not source_rel:
                skipped.append({**t, "skip_reason": "missing_source"})
                p1.update()
                continue
            source_abs = (old_project / source_rel).resolve()
            if not source_abs.exists():
                skipped.append({**t, "skip_reason": f"source_not_found: {source_rel}"})
                p1.update()
                continue
            content = safe_read_text(source_abs)
            _atomic_write(target_abs, content)
            applied.append({**t, "status": "copied"})
            p1.update()
            continue

        if t_type == "placeholder_new_added":
            _atomic_write(target_abs, placeholder + "\n")
            applied.append({**t, "status": "placeholder_written"})
            p1.update()
            continue

        skipped.append({**t, "skip_reason": f"unknown_task_type: {t_type}"})
        p1.update()
    p1.finish("迁移内容文件完成")

    if skipped:
        warnings.append(f"有 {len(skipped)} 个任务未自动执行，详见 apply 结果。")

    # ========== 第二步：内容优化（可选） ==========
    optimization_log: List[Dict[str, Any]] = []
    opt_cfg = (config.get("content_optimization", {}) or {}) if isinstance(config, dict) else {}
    opt_enabled_in_config = bool(opt_cfg.get("enabled", False)) if isinstance(opt_cfg, dict) else False
    min_improvement = float(opt_cfg.get("min_improvement_threshold", 0.1)) if isinstance(opt_cfg, dict) else 0.1

    ai_integration = AIIntegration(enable_ai=bool(ai_enabled), config=config)

    if enable_optimization and opt_enabled_in_config and applied:
        from .content_optimizer import ContentOptimizer

        optimizer = ContentOptimizer(config, skill_root=str(new_project))
        goals = _optimization_goals_from_config(config)

        p2 = progress("内容优化", total=len(applied), enabled=verbose)
        for task in applied:
            if task.get("status") != "copied":
                p2.update()
                continue
            target_rel = task.get("target")
            if not target_rel:
                p2.update()
                continue
            target_abs = (new_project / target_rel).resolve()
            try:
                content = safe_read_text(target_abs)
                section_title = Path(target_rel).stem
                result = await optimizer.optimize_content(
                    content=content,
                    section_title=section_title,
                    optimization_goals=goals,
                    ai_integration=ai_integration,
                )

                optimized = result.get("optimized_content") if isinstance(result, dict) else None
                improvement_score = float(result.get("improvement_score", 0) or 0) if isinstance(result, dict) else 0.0
                applied_count = len((result.get("optimization_log") or [])) if isinstance(result, dict) else 0

                if isinstance(optimized, str) and optimized and optimized != content and improvement_score >= min_improvement:
                    _atomic_write(target_abs, optimized)
                    task["status"] = "optimized"
                    optimization_log.append(
                        {
                            "file": target_rel,
                            "improvement_score": round(improvement_score, 3),
                            "optimization_applied": int(applied_count),
                        }
                    )
            except Exception as e:
                task["optimization_error"] = str(e)
                warnings.append(f"内容优化失败：{target_rel}: {e}")
            finally:
                p2.update()
        p2.finish("内容优化完成")

    # ========== 第三步：字数适配（可选） ==========
    adaptation_log: List[Dict[str, Any]] = []
    wc_cfg = (config.get("word_count_adaptation", {}) or {}) if isinstance(config, dict) else {}
    wc_enabled_in_config = bool(wc_cfg.get("enabled", False)) if isinstance(wc_cfg, dict) else False

    if enable_word_count_adaptation and wc_enabled_in_config and applied:
        from .word_count_adapter import WordCountAdapter

        adapter = WordCountAdapter(config, skill_root=str(new_project))

        p3 = progress("字数适配", total=len(applied), enabled=verbose)
        for task in applied:
            if task.get("status") not in {"copied", "optimized"}:
                p3.update()
                continue
            target_rel = task.get("target")
            if not target_rel:
                p3.update()
                continue
            target_abs = (new_project / target_rel).resolve()
            try:
                content = safe_read_text(target_abs)
                section_title = Path(target_rel).stem
                target_count = _infer_target_word_count(section_title, config)
                result = await adapter.adapt_content(
                    content=content,
                    section_title=section_title,
                    target_word_count=target_count,
                    ai_integration=ai_integration,
                )

                adapted = result.get("adapted_content") if isinstance(result, dict) else None
                if isinstance(adapted, str) and adapted and adapted != content:
                    _atomic_write(target_abs, adapted)
                    task["status"] = "adapted"
                    adaptation_log.append(
                        {
                            "file": target_rel,
                            "original_count": int(result.get("original_count", 0) or 0),
                            "target_count": int(result.get("target_count", target_count) or target_count),
                            "final_count": int(result.get("final_count", 0) or 0),
                            "action": result.get("action", ""),
                        }
                    )
            except Exception as e:
                task["adaptation_error"] = str(e)
                warnings.append(f"字数适配失败：{target_rel}: {e}")
            finally:
                p3.update()
        p3.finish("字数适配完成")

    # ========== 第四步：扫描并迁移资源文件 ==========
    # 资源文件处理配置
    resource_config = (config.get("migration", {}) or {}).get("figure_handling", "copy")
    copy_resources_enabled = resource_config in {"copy", "link"}

    resources_result: Dict[str, Any] = {
        "enabled": copy_resources_enabled,
        "scanned": False,
        "copied": False,
        "validated": False,
        "scan_summary": {},
        "copy_summary": {},
        "validation_summary": {},
    }

    if resource_config == "skip":
        resources_result["enabled"] = False
        resources_result["scan_summary"] = {"skipped": True}
    elif copy_resources_enabled and applied:
        # 收集已迁移的 .tex 文件列表
        migrated_tex_files = [t["target"] for t in applied if t.get("status") in {"copied", "optimized", "adapted"}]

        if migrated_tex_files:
            # 扫描旧项目的资源文件
            scan_result = scan_project_resources(
                old_project,
                migrated_tex_files,
                exclude_dirs={".git", "__pycache__", "node_modules"},
            )

            resources_result["scanned"] = True
            resources_result["scan_summary"] = {
                "total": scan_result.total_count,
                "missing": scan_result.missing_count,
                "directories": sorted(scan_result.directories),
                "outside_paths": list(scan_result.outside_paths),
            }

            # 复制资源文件到新项目（只复制缺失的）
            copy_result = copy_resources(
                old_project,
                new_project,
                scan_result.resources,
                copy_strategy="link" if resource_config == "link" else "missing",  # link or missing-copy
                dry_run=False,
            )

            resources_result["copied"] = True
            resources_result["copy_summary"] = copy_result["summary"]

            # 验证新项目中的资源引用完整性
            validation_result = validate_resource_integrity(
                new_project,
                scan_result.resources,
            )

            resources_result["validated"] = True
            resources_result["validation_summary"] = validation_result["summary"]

            # 如果有缺失资源，添加警告
            if validation_result["summary"]["missing_count"] > 0:
                warnings.append(
                    f"有 {validation_result['summary']['missing_count']} 个资源文件在新项目中缺失，"
                    "可能导致编译失败。请检查 resources 部分。"
                )
            if scan_result.outside_paths:
                warnings.append(
                    f"检测到 {len(scan_result.outside_paths)} 个资源路径超出项目根目录，已跳过复制。"
                )

    # ========== 第五步：验证引用完整性 ==========
    references_result: Dict[str, Any] = {
        "validated": False,
        "old_report": {},
        "new_report": {},
        "comparison": {},
        "passed": False,
    }

    if applied:
        # 收集已迁移的 .tex 文件列表
        migrated_tex_files = [t["target"] for t in applied if t.get("status") in {"copied", "optimized", "adapted"}]

        if migrated_tex_files:
            # 获取参考文献文件
            old_bib_files = []
            new_bib_files = []
            # 假设参考文献文件位置相同，都在 references/ 目录
            for tex_file in migrated_tex_files:
                # 这里简化处理，实际可以从项目分析中获取
                pass

            # 执行引用完整性验证
            ref_validation = validate_migration_reference_integrity(
                old_project,
                new_project,
                migrated_tex_files,
                [],  # bib_files (暂时为空，可以后续增强)
                min_intact_rate=0.95,
            )

            references_result["validated"] = True
            references_result["old_report"] = ref_validation["old_report"]
            references_result["new_report"] = ref_validation["new_report"]
            references_result["comparison"] = ref_validation["comparison"]
            references_result["passed"] = ref_validation["passed"]

            # 如果引用完整性下降，添加警告
            if not ref_validation["passed"]:
                warnings.append(
                    f"引用完整性验证失败：{ref_validation['recommendation']}"
                )

    return ApplyResult(
        applied=applied,
        skipped=skipped,
        warnings=warnings,
        resources=resources_result,
        references=references_result,
        optimization=optimization_log,
        adaptation=adaptation_log,
    )
