#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作空间管理器

统一管理 skill 工作目录，避免污染用户项目目录。

使用方法:
    from scripts.core.workspace_manager import WorkspaceManager

    ws_manager = WorkspaceManager()
    project_ws = ws_manager.get_project_workspace("NSFC_Young")
    baseline_dir = ws_manager.get_baseline_path("NSFC_Young")
"""

import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union


class WorkspaceManager:
    """工作空间管理器"""

    def __init__(self, skill_root: Optional[Path] = None):
        """
        初始化工作空间管理器

        Args:
            skill_root: skill 根目录，默认为本文件所在目录的父目录
        """
        if skill_root is None:
            # 自动检测 skill 根目录
            # scripts/core/workspace_manager.py -> parents[2] == skills/make_latex_model
            self.skill_root = Path(__file__).resolve().parents[2]
        else:
            self.skill_root = Path(skill_root)

        self.repo_root = self.skill_root.parent.parent
        self.projects_root = (self.repo_root / "projects").resolve()

        # 默认配置
        self.config = {
            "root": ".make_latex_model",
            "location": "project_level",
            "auto_cleanup": True,
            "cache_max_age_hours": 24,
            "keep_iterations": True,
            "max_iterations_kept": 30,
            "auto_migrate_legacy": True,
            "verbose_migration": True,
        }

        # 尽早加载 config.yaml（允许用户覆盖 workspace.root 等）
        self.load_config()

    def load_config(self, config_path: Optional[Path] = None) -> None:
        """
        从配置文件加载工作空间配置

        Args:
            config_path: 配置文件路径，默认为 skill 根目录下的 config.yaml
        """
        if config_path is None:
            config_path = self.skill_root / "config.yaml"

        if config_path.exists():
            try:
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    full_config = yaml.safe_load(f)
                    if "workspace" in full_config:
                        self.config.update(full_config["workspace"])
            except Exception:
                pass  # 使用默认配置

    def _resolve_project_path(self, project: Union[str, Path]) -> Path:
        """
        将 project 参数解析为 projects/ 下的绝对路径（防路径遍历）。

        支持：
        - 项目名（如 NSFC_Young）
        - 相对路径（如 projects/NSFC_Young）
        - 绝对路径（必须位于 repo_root/projects 下）
        """
        if isinstance(project, Path):
            raw = project
            raw_str = str(project)
        else:
            raw = Path(str(project).strip())
            raw_str = str(project).strip()

        # 允许用户传入 projects/<name>，或仅 <name>
        if raw.is_absolute() or any(sep in raw_str for sep in ("/", "\\")):
            candidate = raw if raw.is_absolute() else (self.repo_root / raw)
        else:
            candidate = self.repo_root / "projects" / raw_str

        candidate = candidate.resolve()
        try:
            candidate.relative_to(self.projects_root)
        except Exception:
            raise ValueError(f"--project 必须位于 {self.projects_root} 下: {project}")

        return candidate

    def _get_workspace_root(self, project_path: Path) -> Path:
        root = self.config.get("root", ".make_latex_model")
        root_path = Path(str(root))
        if root_path.is_absolute() or ".." in root_path.parts:
            raise ValueError(f"workspace.root 必须为相对于项目根目录的安全相对路径: {root}")

        project_root = project_path.resolve()
        ws_root = (project_root / root_path).resolve()
        try:
            ws_root.relative_to(project_root)
        except Exception:
            raise ValueError(f"workspace.root 解析后不在项目目录内: {ws_root}")

        return ws_root

    def _load_or_init_metadata(self, ws_root: Path, project_path: Path) -> Dict[str, Any]:
        meta_path = ws_root / "workspace_manager.json"
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        data = {
            "schema_version": 1,
            "created_at": datetime.now().isoformat(),
            "project_path": str(project_path),
            "workspace_root": str(ws_root),
            "legacy_migration_done": False,
        }
        meta_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return data

    def _copy_newer_tree(self, src: Path, dest: Path, stats: Dict[str, int]) -> None:
        if not src.exists():
            return
        for p in src.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(src)
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            if out.exists():
                stats["skipped"] += 1
                continue
            shutil.copy2(p, out)
            stats["migrated"] += 1

    def _maybe_migrate_legacy(self, project_path: Path, ws_root: Path) -> Dict[str, int]:
        """
        向后兼容：尝试将旧工作空间/旧产物复制到新工作空间。

        支持来源：
        - 技能级旧工作空间：skills/make_latex_model/workspace/{project}/
        - 项目旧 artifacts：projects/{project}/artifacts/
        """
        if not self.config.get("auto_migrate_legacy", True):
            return {"migrated": 0, "skipped": 0}

        stats = {"migrated": 0, "skipped": 0}
        project_name = project_path.name

        legacy_skill_ws = self.skill_root / "workspace" / project_name
        if legacy_skill_ws.exists():
            self._copy_newer_tree(legacy_skill_ws / "baseline", ws_root / "baselines", stats)
            self._copy_newer_tree(legacy_skill_ws / "iterations", ws_root / "iterations", stats)
            self._copy_newer_tree(legacy_skill_ws / "reports", ws_root / "reports", stats)
            self._copy_newer_tree(legacy_skill_ws / "cache", ws_root / "cache", stats)
            self._copy_newer_tree(legacy_skill_ws / "backup", ws_root / "backup", stats)

        legacy_artifacts = project_path / "artifacts"
        if legacy_artifacts.exists():
            self._copy_newer_tree(legacy_artifacts / "baseline", ws_root / "baselines", stats)
            # round-* 迭代产物：尽量映射到 iteration_XXX/
            old_output = legacy_artifacts / "output"
            if old_output.exists():
                for f in old_output.glob("round-*"):
                    try:
                        round_num = int(f.name.split("-")[1])
                    except Exception:
                        continue
                    iter_dir = ws_root / "iterations" / f"iteration_{round_num:03d}"
                    iter_dir.mkdir(parents=True, exist_ok=True)
                    if f.is_file():
                        dest = iter_dir / f.name
                        if dest.exists():
                            stats["skipped"] += 1
                        else:
                            shutil.copy2(f, dest)
                            stats["migrated"] += 1

        return stats

    def get_project_workspace(self, project: Union[str, Path]) -> Path:
        """
        获取项目工作空间路径

        自动创建必要的目录结构：
        - baselines/: PDF 基准文件
        - iterations/: 迭代历史记录
        - reports/: 生成的报告
        - cache/: 缓存文件
        - backup/: 备份文件

        Args:
            project: 项目名称或路径（如 NSFC_Young 或 projects/NSFC_Young）

        Returns:
            项目工作空间路径
        """
        project_path = self._resolve_project_path(project)
        ws = self._get_workspace_root(project_path)
        ws.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (ws / "baselines").mkdir(exist_ok=True)
        (ws / "iterations").mkdir(exist_ok=True)
        (ws / "reports").mkdir(exist_ok=True)
        (ws / "cache").mkdir(exist_ok=True)
        (ws / "backup").mkdir(exist_ok=True)

        # 元数据文件 + 旧路径迁移（复制，不删除旧目录）
        meta = self._load_or_init_metadata(ws, project_path)
        if not meta.get("legacy_migration_done", False):
            stats = self._maybe_migrate_legacy(project_path, ws)
            meta["legacy_migration_done"] = True
            meta["legacy_migration_at"] = datetime.now().isoformat()
            meta["legacy_migration_stats"] = stats
            (ws / "workspace_manager.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            if self.config.get("verbose_migration", True) and stats.get("migrated", 0) > 0:
                print(
                    f"ℹ️  检测到旧工作空间/旧产物，已复制 {stats['migrated']} 个文件到: {ws}（旧目录保留，可手动清理）"
                )

        return ws

    def get_baseline_path(self, project: Union[str, Path]) -> Path:
        """
        获取基准文件目录路径

        Args:
            project: 项目名称或路径

        Returns:
            基准文件目录路径
        """
        return self.get_project_workspace(project) / "baselines"

    def get_reports_path(self, project: Union[str, Path]) -> Path:
        """
        获取报告目录路径

        Args:
            project_name: 项目名称

        Returns:
            报告目录路径
        """
        return self.get_project_workspace(project) / "reports"

    def get_cache_path(self, project: Union[str, Path]) -> Path:
        """
        获取缓存目录路径

        Args:
            project_name: 项目名称

        Returns:
            缓存目录路径
        """
        return self.get_project_workspace(project) / "cache"

    def get_backup_path(self, project: Union[str, Path]) -> Path:
        """
        获取备份目录路径

        Args:
            project_name: 项目名称

        Returns:
            备份目录路径
        """
        return self.get_project_workspace(project) / "backup"

    def get_iteration_path(self, project: Union[str, Path], iteration_num: int) -> Path:
        """
        获取迭代目录路径

        Args:
            project_name: 项目名称
            iteration_num: 迭代编号（从 1 开始）

        Returns:
            迭代目录路径
        """
        iterations_dir = self.get_project_workspace(project) / "iterations"
        iter_dir = iterations_dir / f"iteration_{iteration_num:03d}"
        iter_dir.mkdir(parents=True, exist_ok=True)
        return iter_dir

    def get_latest_iteration_num(self, project: Union[str, Path]) -> int:
        """
        获取最新的迭代编号

        Args:
            project_name: 项目名称

        Returns:
            最新迭代编号，如果没有迭代则返回 0
        """
        iterations_dir = self.get_project_workspace(project) / "iterations"
        if not iterations_dir.exists():
            return 0

        iteration_dirs = sorted(iterations_dir.glob("iteration_*"))
        if not iteration_dirs:
            return 0

        # 解析最新的迭代编号
        latest = iteration_dirs[-1].name
        try:
            return int(latest.split("_")[1])
        except (IndexError, ValueError):
            return 0

    def save_iteration_result(self, project: Union[str, Path], iteration_num: int,
                             pdf_path: Optional[Path] = None,
                             config_path: Optional[Path] = None,
                             metrics: Optional[Dict[str, Any]] = None) -> Path:
        """
        保存迭代结果

        Args:
            project_name: 项目名称
            iteration_num: 迭代编号
            pdf_path: PDF 文件路径（可选）
            config_path: 配置文件路径（可选）
            metrics: 指标数据（可选）

        Returns:
            迭代目录路径
        """
        iter_dir = self.get_iteration_path(project, iteration_num)

        # 复制 PDF
        if pdf_path and pdf_path.exists():
            shutil.copy2(pdf_path, iter_dir / "main.pdf")

        # 复制配置文件
        if config_path and config_path.exists():
            shutil.copy2(config_path, iter_dir / "config.tex")

        # 保存指标
        if metrics:
            metrics["iteration"] = iteration_num
            metrics["timestamp"] = datetime.now().isoformat()
            metrics_file = iter_dir / "metrics.json"
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)

        return iter_dir

    def cleanup_cache(self, project: Union[str, Path],
                     max_age_hours: Optional[int] = None) -> int:
        """
        清理过期缓存

        Args:
            project: 项目名称或路径
            max_age_hours: 缓存最大保留时间（小时），默认使用配置值

        Returns:
            清理的文件数量
        """
        if max_age_hours is None:
            max_age_hours = self.config.get("cache_max_age_hours", 24)

        cache_dir = self.get_cache_path(project)
        if not cache_dir.exists():
            return 0

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0

        for file_path in cache_dir.rglob("*"):
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1

        return cleaned_count

    def cleanup_old_iterations(self, project: Union[str, Path],
                               max_kept: Optional[int] = None) -> int:
        """
        清理旧的迭代历史

        Args:
            project: 项目名称或路径
            max_kept: 最多保留的迭代数量，默认使用配置值

        Returns:
            清理的迭代数量
        """
        if max_kept is None:
            max_kept = self.config.get("max_iterations_kept", 30)

        iterations_dir = self.get_project_workspace(project) / "iterations"
        if not iterations_dir.exists():
            return 0

        iteration_dirs = sorted(iterations_dir.glob("iteration_*"))

        if len(iteration_dirs) <= max_kept:
            return 0

        # 删除最旧的迭代
        to_delete = iteration_dirs[:-max_kept]
        for dir_path in to_delete:
            shutil.rmtree(dir_path)

        return len(to_delete)

    def get_workspace_info(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        获取工作空间信息

        Args:
            project: 项目名称或路径

        Returns:
            工作空间信息字典
        """
        ws = self.get_project_workspace(project)

        # 统计各目录文件数
        baseline_files = list((ws / "baselines").glob("*"))
        iteration_dirs = list((ws / "iterations").glob("iteration_*"))
        report_files = list((ws / "reports").glob("*"))
        cache_files = list((ws / "cache").rglob("*"))

        # 计算总大小
        total_size = 0
        for f in ws.rglob("*"):
            if f.is_file():
                total_size += f.stat().st_size

        return {
            "project_name": ws.parent.name,
            "workspace_path": str(ws),
            "baseline_files": len(baseline_files),
            "iterations": len(iteration_dirs),
            "report_files": len(report_files),
            "cache_files": len([f for f in cache_files if f.is_file()]),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "has_word_pdf": (ws / "baselines" / "word.pdf").exists(),
            "has_analysis": any(f.suffix == ".json" for f in baseline_files),
        }


# 便捷函数
def get_workspace_manager() -> WorkspaceManager:
    """获取全局工作空间管理器实例"""
    return WorkspaceManager()


def get_project_workspace(project_name: str) -> Path:
    """
    便捷函数：获取项目工作空间路径

    Args:
        project_name: 项目名称

    Returns:
        项目工作空间路径
    """
    return get_workspace_manager().get_project_workspace(project_name)


if __name__ == "__main__":
    # 测试代码
    import sys

    ws_manager = WorkspaceManager()

    if len(sys.argv) > 1:
        project_name = sys.argv[1]
    else:
        project_name = "NSFC_Young"

    print(f"工作空间管理器测试")
    print(f"=" * 60)
    print(f"Skill 根目录: {ws_manager.skill_root}")
    print(f"工作空间模式: project_level")
    print(f"工作空间相对根: {ws_manager.config.get('root', '.make_latex_model')}")

    # 创建项目工作空间
    ws = ws_manager.get_project_workspace(project_name)
    print(f"\n项目工作空间: {ws}")

    # 获取各目录路径
    print(f"\n目录结构:")
    print(f"  基准文件: {ws_manager.get_baseline_path(project_name)}")
    print(f"  报告: {ws_manager.get_reports_path(project_name)}")
    print(f"  缓存: {ws_manager.get_cache_path(project_name)}")
    print(f"  备份: {ws_manager.get_backup_path(project_name)}")

    # 获取工作空间信息
    info = ws_manager.get_workspace_info(project_name)
    print(f"\n工作空间信息:")
    for key, value in info.items():
        print(f"  {key}: {value}")
