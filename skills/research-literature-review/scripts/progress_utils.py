#!/usr/bin/env python3
"""
progress_utils.py - 进度条和实时反馈工具

P1-4: 添加进度条和实时反馈 - 提升用户体验

功能：
  - 统一的进度条接口（基于 tqdm）
  - 实时日志反馈
  - 上下文管理器支持
  - 支持嵌套进度条

使用示例：
    from scripts.progress_utils import ProgressManager, track_progress

    # 方式1: 使用上下文管理器
    with ProgressManager(desc="处理论文", total=len(papers)) as pbar:
        for paper in papers:
            # 处理论文
            process_paper(paper)
            pbar.update(1)

    # 方式2: 使用装饰器
    @track_progress("质量评价")
    def assess_quality(papers):
        for paper in papers:
            yield assess_paper(paper)

    # 方式3: 简单迭代
    for paper in progress_iterate(papers, desc="评估论文"):
        process_paper(paper)
"""

import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator, Iterable, List, Optional

# 尝试导入 tqdm
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    logging.warning("tqdm 未安装，进度条功能将被禁用。安装: pip install tqdm")


logger = logging.getLogger(__name__)


# ============================================================================
# 进度管理器
# ============================================================================

class ProgressManager:
    """进度管理器"""

    def __init__(self, desc: str = "处理中", total: Optional[int] = None,
                 unit: str = "it", disable: bool = False):
        """
        初始化进度管理器

        Args:
            desc: 描述文本
            total: 总项目数
            unit: 单位名称
            disable: 是否禁用进度条
        """
        self.desc = desc
        self.total = total
        self.unit = unit
        self.disable = disable or not TQDM_AVAILABLE
        self.pbar: Optional[tqdm] = None
        self.start_time: Optional[float] = None

    def __enter__(self):
        """进入上下文"""
        if not self.disable:
            self.pbar = tqdm(
                total=self.total,
                desc=self.desc,
                unit=self.unit,
                disable=False
            )
            self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.pbar:
            self.pbar.close()

            # 打印总结
            elapsed = time.time() - self.start_time if self.start_time else 0
            logger.info(f"{self.desc} 完成，用时 {elapsed:.1f} 秒")

    def update(self, n: int = 1):
        """更新进度"""
        if self.pbar:
            self.pbar.update(n)

    def set_description(self, desc: str):
        """设置描述文本"""
        if self.pbar:
            self.pbar.set_description(desc)

    def set_postfix(self, **kwargs):
        """设置后缀信息"""
        if self.pbar:
            self.pbar.set_postfix(**kwargs)

    def write(self, msg: str):
        """在进度条下方输出消息"""
        if self.pbar:
            self.pbar.write(msg)


# ============================================================================
# 进度迭代器
# ============================================================================

def progress_iterate(iterable: Iterable,
                    desc: str = "处理中",
                    unit: str = "it",
                    total: Optional[int] = None) -> Generator:
    """
    带进度条的迭代器

    Args:
        iterable: 可迭代对象
        desc: 描述文本
        unit: 单位名称
        total: 总项目数

    Yields:
        迭代元素

    使用示例:
        for paper in progress_iterate(papers, desc="评估论文"):
            process_paper(paper)
    """
    if not TQDM_AVAILABLE:
        # 降级到普通迭代
        for item in iterable:
            yield item
        return

    if total is None:
        try:
            total = len(iterable)
        except TypeError:
            total = None

    with tqdm(total=total, desc=desc, unit=unit) as pbar:
        for item in iterable:
            yield item
            pbar.update(1)


# ============================================================================
# 装饰器
# ============================================================================

def track_progress(desc: str = "处理中", unit: str = "it"):
    """
    跟踪函数执行进度的装饰器

    Args:
        desc: 描述文本
        unit: 单位名称

    使用示例:
        @track_progress("评估论文质量")
        def assess_papers(papers):
            results = []
            for paper in papers:
                results.append(assess_paper(paper))
            return results
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 检查第一个参数是否为可迭代对象
            if args and hasattr(args[0], '__iter__'):
                iterable = args[0]
                try:
                    total = len(iterable)
                except TypeError:
                    total = None

                if TQDM_AVAILABLE:
                    with tqdm(total=total, desc=desc, unit=unit) as pbar:
                        # 创建生成器
                        def gen():
                            for item in iterable:
                                yield item
                                pbar.update(1)

                        # 调用原函数
                        new_args = (gen(),) + args[1:]
                        return func(*new_args, **kwargs)
                else:
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# 批处理进度工具
# ============================================================================

class BatchProgress:
    """批处理进度工具"""

    def __init__(self, items: List[Any], batch_size: int,
                 desc: str = "批处理"):
        """
        初始化批处理进度

        Args:
            items: 待处理项目列表
            batch_size: 批次大小
            desc: 描述文本
        """
        self.items = items
        self.batch_size = batch_size
        self.desc = desc
        self.total_batches = (len(items) + batch_size - 1) // batch_size

    def __iter__(self) -> Generator[tuple[int, List[Any]], None, None]:
        """迭代批次"""
        if not TQDM_AVAILABLE:
            for i in range(0, len(self.items), self.batch_size):
                batch = self.items[i:i + self.batch_size]
                yield i // self.batch_size, batch
            return

        with tqdm(total=self.total_batches, desc=self.desc, unit="batch") as pbar:
            for i in range(0, len(self.items), self.batch_size):
                batch = self.items[i:i + self.batch_size]
                batch_num = i // self.batch_size
                pbar.set_postfix(batch=f"{batch_num + 1}/{self.total_batches}")
                yield batch_num, batch
                pbar.update(1)


# ============================================================================
# 实时反馈工具
# ============================================================================

class LiveFeedback:
    """实时反馈工具（打印到标准输出，不干扰进度条）"""

    def __init__(self):
        self.last_message = ""

    def print(self, message: str, overwrite: bool = False):
        """
        打印消息

        Args:
            message: 消息内容
            overwrite: 是否覆盖上一条消息
        """
        if overwrite:
            # 清除上一条消息
            sys.stdout.write('\r' + ' ' * len(self.last_message) + '\r')
            sys.stdout.write(f'\r{message}')
            sys.stdout.flush()
            self.last_message = message
        else:
            print(message)

    def clear(self):
        """清除当前行"""
        if self.last_message:
            sys.stdout.write('\r' + ' ' * len(self.last_message) + '\r')
            sys.stdout.flush()
            self.last_message = ""


# ============================================================================
# 嵌套进度条工具
# ============================================================================

@contextmanager
def nested_progress(outer_desc: str, inner_desc: str,
                   outer_total: int, inner_total_per_item: int = None):
    """
    嵌套进度条上下文管理器

    Args:
        outer_desc: 外层进度条描述
        inner_desc: 内层进度条描述
        outer_total: 外层总项目数
        inner_total_per_item: 每个外层项目的内层项目数

    使用示例:
        with nested_progress("处理文件", "处理行", 10, 100) as (outer_pbar, inner_pbar):
            for file in files:
                for line in file:
                    process_line(line)
                    inner_pbar.update(1)
                outer_pbar.update(1)
    """
    if not TQDM_AVAILABLE:
        # 降级：返回空的上下文管理器
        yield None, None
        return

    from tqdm import tqdm

    with tqdm(total=outer_total, desc=outer_desc, unit="file", position=0) as outer_pbar:
        inner_total = inner_total_per_item
        with tqdm(total=inner_total, desc=inner_desc, unit="item",
                 position=1, leave=False) as inner_pbar:
            try:
                yield outer_pbar, inner_pbar
            finally:
                pass


# ============================================================================
# 集成辅助函数
# ============================================================================

def print_status(message: str, level: str = "info"):
    """
    打印状态消息（与进度条兼容）

    Args:
        message: 消息内容
        level: 日志级别
    """
    if TQDM_AVAILABLE:
        tqdm.write(message)
    else:
        print(message)


def log_progress(current: int, total: int,
                desc: str = "处理中",
                interval: int = 10):
    """
    定期记录进度（不使用 tqdm）

    Args:
        current: 当前项目数
        total: 总项目数
        desc: 描述文本
        interval: 打印间隔（每 N 个项目打印一次）
    """
    if current % interval == 0 or current == total:
        pct = current / total * 100 if total > 0 else 0
        print_status(f"{desc}: {current}/{total} ({pct:.1f}%)")


# ============================================================================
# 示例用法
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='进度条工具示例')
    parser.add_argument('--demo', choices=['simple', 'nested', 'batch'],
                       default='simple', help='演示模式')

    args = parser.parse_args()

    if args.demo == 'simple':
        print("简单进度条演示:")
        for i in progress_iterate(range(100), desc="处理项目"):
            time.sleep(0.02)

    elif args.demo == 'nested':
        print("嵌套进度条演示:")
        files = [list(range(10)) for _ in range(5)]

        with nested_progress("处理文件", "处理行", len(files), 10) as (outer_pbar, inner_pbar):
            if outer_pbar and inner_pbar:
                for file in files:
                    for line in file:
                        time.sleep(0.01)
                        inner_pbar.update(1)
                    outer_pbar.update(1)
                    inner_pbar.reset()

    elif args.demo == 'batch':
        print("批处理进度演示:")
        items = list(range(100))

        for batch_num, batch in BatchProgress(items, batch_size=10, desc="批处理"):
            time.sleep(0.1)
            print_status(f"处理批次 {batch_num + 1}: {len(batch)} 项目")
