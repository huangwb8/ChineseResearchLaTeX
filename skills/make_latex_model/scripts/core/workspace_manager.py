#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作空间管理器

统一管理 skill 工作目录，避免污染用户项目目录。

使用方法:
    from core.workspace_manager import WorkspaceManager

    ws_manager = WorkspaceManager()
    project_ws = ws_manager.get_project_workspace("NSFC_Young")
    baseline_dir = ws_manager.get_baseline_path("NSFC_Young")
"""

import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


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
            self.skill_root = Path(__file__).parent.parent
        else:
            self.skill_root = Path(skill_root)

        self.workspace_root = self.skill_root / "workspace"

        # 默认配置
        self.config = {
            "auto_cleanup": True,
            "cache_max_age_hours": 24,
            "keep_iterations": True,
            "max_iterations_kept": 10,
        }

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

    def get_project_workspace(self, project_name: str) -> Path:
        """
        获取项目工作空间路径

        自动创建必要的目录结构：
        - baseline/: PDF 基准文件
        - iterations/: 迭代历史记录
        - reports/: 生成的报告
        - cache/: 缓存文件
        - backup/: 备份文件

        Args:
            project_name: 项目名称（如 NSFC_Young）

        Returns:
            项目工作空间路径
        """
        ws = self.workspace_root / project_name
        ws.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (ws / "baseline").mkdir(exist_ok=True)
        (ws / "iterations").mkdir(exist_ok=True)
        (ws / "reports").mkdir(exist_ok=True)
        (ws / "cache").mkdir(exist_ok=True)
        (ws / "backup").mkdir(exist_ok=True)

        return ws

    def get_baseline_path(self, project_name: str) -> Path:
        """
        获取基准文件目录路径

        Args:
            project_name: 项目名称

        Returns:
            基准文件目录路径
        """
        return self.get_project_workspace(project_name) / "baseline"

    def get_reports_path(self, project_name: str) -> Path:
        """
        获取报告目录路径

        Args:
            project_name: 项目名称

        Returns:
            报告目录路径
        """
        return self.get_project_workspace(project_name) / "reports"

    def get_cache_path(self, project_name: str) -> Path:
        """
        获取缓存目录路径

        Args:
            project_name: 项目名称

        Returns:
            缓存目录路径
        """
        return self.get_project_workspace(project_name) / "cache"

    def get_backup_path(self, project_name: str) -> Path:
        """
        获取备份目录路径

        Args:
            project_name: 项目名称

        Returns:
            备份目录路径
        """
        return self.get_project_workspace(project_name) / "backup"

    def get_iteration_path(self, project_name: str, iteration_num: int) -> Path:
        """
        获取迭代目录路径

        Args:
            project_name: 项目名称
            iteration_num: 迭代编号（从 1 开始）

        Returns:
            迭代目录路径
        """
        iterations_dir = self.get_project_workspace(project_name) / "iterations"
        iter_dir = iterations_dir / f"iteration_{iteration_num:03d}"
        iter_dir.mkdir(parents=True, exist_ok=True)
        return iter_dir

    def get_latest_iteration_num(self, project_name: str) -> int:
        """
        获取最新的迭代编号

        Args:
            project_name: 项目名称

        Returns:
            最新迭代编号，如果没有迭代则返回 0
        """
        iterations_dir = self.get_project_workspace(project_name) / "iterations"
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

    def save_iteration_result(self, project_name: str, iteration_num: int,
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
        iter_dir = self.get_iteration_path(project_name, iteration_num)

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

    def cleanup_cache(self, project_name: str,
                     max_age_hours: Optional[int] = None) -> int:
        """
        清理过期缓存

        Args:
            project_name: 项目名称
            max_age_hours: 缓存最大保留时间（小时），默认使用配置值

        Returns:
            清理的文件数量
        """
        if max_age_hours is None:
            max_age_hours = self.config.get("cache_max_age_hours", 24)

        cache_dir = self.get_cache_path(project_name)
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

    def cleanup_old_iterations(self, project_name: str,
                               max_kept: Optional[int] = None) -> int:
        """
        清理旧的迭代历史

        Args:
            project_name: 项目名称
            max_kept: 最多保留的迭代数量，默认使用配置值

        Returns:
            清理的迭代数量
        """
        if max_kept is None:
            max_kept = self.config.get("max_iterations_kept", 10)

        iterations_dir = self.get_project_workspace(project_name) / "iterations"
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

    def migrate_old_paths(self, project_path: Path, project_name: str) -> Dict[str, int]:
        """
        迁移旧路径下的文件到新工作空间

        用于向后兼容，自动迁移以下位置的文件：
        - projects/{project}/artifacts/ -> workspace/{project}/
        - 根目录下的 *_analysis.json -> workspace/{project}/baseline/

        Args:
            project_path: 项目路径
            project_name: 项目名称

        Returns:
            迁移统计 {"migrated": 数量, "skipped": 数量}
        """
        stats = {"migrated": 0, "skipped": 0}
        ws = self.get_project_workspace(project_name)

        # 迁移旧的 artifacts 目录
        old_artifacts = project_path / "artifacts"
        if old_artifacts.exists():
            # 迁移 baseline
            old_baseline = old_artifacts / "baseline"
            if old_baseline.exists():
                for file in old_baseline.iterdir():
                    dest = ws / "baseline" / file.name
                    if not dest.exists():
                        shutil.copy2(file, dest)
                        stats["migrated"] += 1
                    else:
                        stats["skipped"] += 1

            # 迁移 output（如果存在）
            old_output = old_artifacts / "output"
            if old_output.exists():
                # 查找迭代文件并迁移
                for file in old_output.glob("round-*"):
                    # 解析轮次编号
                    try:
                        round_num = int(file.name.split("-")[1])
                        iter_dir = self.get_iteration_path(project_name, round_num)
                        dest = iter_dir / file.name
                        if not dest.exists():
                            shutil.copy2(file, dest)
                            stats["migrated"] += 1
                        else:
                            stats["skipped"] += 1
                    except (IndexError, ValueError):
                        pass

        # 迁移根目录下的分析文件
        repo_root = self.skill_root.parent.parent
        for analysis_file in repo_root.glob("*_analysis.json"):
            dest = ws / "baseline" / analysis_file.name
            if not dest.exists():
                shutil.move(str(analysis_file), str(dest))
                stats["migrated"] += 1
            else:
                stats["skipped"] += 1

        return stats

    def get_workspace_info(self, project_name: str) -> Dict[str, Any]:
        """
        获取工作空间信息

        Args:
            project_name: 项目名称

        Returns:
            工作空间信息字典
        """
        ws = self.get_project_workspace(project_name)

        # 统计各目录文件数
        baseline_files = list((ws / "baseline").glob("*"))
        iteration_dirs = list((ws / "iterations").glob("iteration_*"))
        report_files = list((ws / "reports").glob("*"))
        cache_files = list((ws / "cache").rglob("*"))

        # 计算总大小
        total_size = 0
        for f in ws.rglob("*"):
            if f.is_file():
                total_size += f.stat().st_size

        return {
            "project_name": project_name,
            "workspace_path": str(ws),
            "baseline_files": len(baseline_files),
            "iterations": len(iteration_dirs),
            "report_files": len(report_files),
            "cache_files": len([f for f in cache_files if f.is_file()]),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "has_word_pdf": (ws / "baseline" / "word.pdf").exists(),
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
    print(f"工作空间根目录: {ws_manager.workspace_root}")

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
