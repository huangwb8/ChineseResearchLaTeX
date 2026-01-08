#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
进度反馈工具
- 支持 rich.progress（如果可用）
- 回退到简单文本输出
"""

from __future__ import annotations

import sys
import time
from typing import Any, Callable, Iterable, List, Optional

# 尝试导入 rich
try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ProgressReporter:
    """
    进度报告器

    如果 rich 可用，显示美观的进度条
    否则，显示简单的文本进度
    """

    def __init__(self, description: str = "处理中", total: Optional[int] = None, enabled: bool = True):
        """
        初始化进度报告器

        Args:
            description: 任务描述
            total: 总数量（None 表示不确定）
            enabled: 是否启用进度显示
        """
        self.description = description
        self.total = total
        self.enabled = enabled
        self.current = 0
        self.start_time = time.time()

        if RICH_AVAILABLE and enabled:
            self.console = Console()
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn() if total else TextColumn(""),
                console=self.console,
            )
            self.task = self.progress.add_task(description, total=total)
            self.progress.start()
            self._use_rich = True
        else:
            self._use_rich = False
            if enabled:
                self._print_simple_progress()

    def update(self, advance: int = 1, description: Optional[str] = None) -> None:
        """
        更新进度

        Args:
            advance: 前进的步数
            description: 新的描述（可选）
        """
        if not self.enabled:
            return

        self.current += advance

        if self._use_rich:
            if description:
                self.progress.update(self.task, description=description)
            self.progress.update(self.task, advance=advance)
        else:
            if description:
                self.description = description
            self._print_simple_progress()

    def set_total(self, total: int) -> None:
        """设置总数量"""
        self.total = total
        if self._use_rich:
            self.progress.update(self.task, total=total)

    def finish(self, message: Optional[str] = None) -> None:
        """
        完成进度

        Args:
            message: 完成消息（可选）
        """
        if not self.enabled:
            return

        elapsed = time.time() - self.start_time

        if self._use_rich:
            if message:
                self.progress.update(self.task, description=message)
            self.progress.stop()
        else:
            if message:
                print(f"\r{message} ({elapsed:.1f}s)", file=sys.stderr)
            else:
                print(f"\r{self.description} 完成 ({elapsed:.1f}s)", file=sys.stderr)

    def _print_simple_progress(self) -> None:
        """打印简单文本进度"""
        if self.total:
            percent = min(100, self.current * 100 // self.total)
            bar_len = 40
            filled = bar_len * self.current // self.total
            bar = "█" * filled + "░" * (bar_len - filled)
            print(
                f"\r{self.description}: [{bar}] {percent}% ({self.current}/{self.total})",
                file=sys.stderr,
                end="",
                flush=True,
            )
        else:
            elapsed = time.time() - self.start_time
            print(
                f"\r{self.description}: {self.current} 项 ({elapsed:.1f}s)",
                file=sys.stderr,
                end="",
                flush=True,
            )


class TaskGroup:
    """
    任务组管理器

    支持多个并行任务的进度显示
    """

    def __init__(self, enabled: bool = True):
        """
        初始化任务组

        Args:
            enabled: 是否启用进度显示
        """
        self.enabled = enabled
        self.tasks: List[ProgressReporter] = []
        self.start_time = time.time()

        if RICH_AVAILABLE and enabled:
            self.console = Console()
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console,
                refresh_per_second=10,
            )
            self.progress.start()
            self._use_rich = True
        else:
            self._use_rich = False

    def add_task(self, description: str, total: Optional[int] = None) -> "TaskHandle":
        """
        添加任务

        Args:
            description: 任务描述
            total: 总数量

        Returns:
            TaskHandle 对象
        """
        if self._use_rich:
            task_id = self.progress.add_task(description, total=total)
            handle = TaskHandle(self, task_id, description, total)
        else:
            reporter = ProgressReporter(description, total, self.enabled)
            handle = TaskHandle(self, None, description, total, reporter)

        self.tasks.append(handle)
        return handle

    def finish_all(self) -> None:
        """完成所有任务"""
        if self._use_rich:
            self.progress.stop()
        else:
            for task in self.tasks:
                if task.reporter:
                    task.reporter.finish()

    def get_elapsed(self) -> float:
        """获取已用时间"""
        return time.time() - self.start_time


class TaskHandle:
    """任务句柄"""

    def __init__(
        self,
        group: TaskGroup,
        task_id: Optional[int],
        description: str,
        total: Optional[int],
        reporter: Optional[ProgressReporter] = None,
    ):
        self.group = group
        self.task_id = task_id
        self.description = description
        self.total = total
        self.reporter = reporter
        self.current = 0

    def update(self, advance: int = 1, description: Optional[str] = None) -> None:
        """更新任务进度"""
        self.current += advance

        if self.group._use_rich:
            if description:
                self.group.progress.update(self.task_id, description=description)
            self.group.progress.update(self.task_id, advance=advance)
        elif self.reporter:
            self.reporter.update(advance, description)

    def finish(self, message: Optional[str] = None) -> None:
        """完成任务"""
        if self.group._use_rich:
            if message:
                self.group.progress.update(self.task_id, description=message)
        elif self.reporter:
            self.reporter.finish(message)


def iterate_with_progress(
    items: Iterable[Any],
    description: str = "处理中",
    enabled: bool = True,
) -> Iterable[Any]:
    """
    带进度显示的迭代器

    Args:
        items: 要迭代的项目
        description: 描述
        enabled: 是否启用进度显示

    Yields:
        每个项目

    Examples:
        >>> for item in iterate_with_progress(items, "处理文件"):
        ...     process(item)
    """
    if not enabled:
        yield from items
        return

    # 尝试获取长度
    try:
        total = len(items)  # type: ignore[arg-type]
    except TypeError:
        total = None

    reporter = ProgressReporter(description, total, enabled)

    try:
        for item in items:
            yield item
            reporter.update(1)
    finally:
        reporter.finish()


# 便捷函数
def progress(description: str = "处理中", total: Optional[int] = None, enabled: bool = True) -> ProgressReporter:
    """创建进度报告器（便捷函数）"""
    return ProgressReporter(description, total, enabled)


def task_group(enabled: bool = True) -> TaskGroup:
    """创建任务组（便捷函数）"""
    return TaskGroup(enabled)
