"""
File Utils - 文件操作工具
提供安全的文件读写和备份功能
"""

from pathlib import Path
import shutil
from typing import Optional


def read_file_safe(file_path: Path, encoding: str = 'utf-8') -> Optional[str]:
    """
    安全读取文件

    Args:
        file_path: 文件路径
        encoding: 文件编码

    Returns:
        Optional[str]: 文件内容，如果读取失败则返回 None
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return None

        return path.read_text(encoding=encoding)
    except Exception as e:
        print(f"读取文件失败：{file_path}，错误：{e}")
        return None


def write_file_safe(
    file_path: Path,
    content: str,
    encoding: str = 'utf-8',
    backup: bool = True
) -> bool:
    """
    安全写入文件

    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 文件编码
        backup: 是否在写入前备份

    Returns:
        bool: 是否成功
    """
    try:
        path = Path(file_path)

        # 备份原文件
        if backup and path.exists():
            backup_file(path)

        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        path.write_text(content, encoding=encoding)

        return True

    except Exception as e:
        print(f"写入文件失败：{file_path}，错误：{e}")
        return False


def backup_file(
    file_path: Path,
    backup_dir: Optional[Path] = None,
    suffix: str = '.backup'
) -> Optional[Path]:
    """
    备份文件

    Args:
        file_path: 文件路径
        backup_dir: 备份目录（如果为 None，则在原文件同目录下创建备份）
        suffix: 备份文件后缀

    Returns:
        Optional[Path]: 备份文件路径，如果失败则返回 None
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return None

        # 确定备份文件路径
        if backup_dir is None:
            backup_path = path.with_suffix(path.suffix + suffix)
        else:
            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{path.name}{suffix}"

        # 复制文件
        shutil.copy2(path, backup_path)

        return backup_path

    except Exception as e:
        print(f"备份文件失败：{file_path}，错误：{e}")
        return None


def create_directory(
    dir_path: Path,
    parents: bool = True,
    exist_ok: bool = True
) -> bool:
    """
    创建目录

    Args:
        dir_path: 目录路径
        parents: 是否创建父目录
        exist_ok: 如果目录已存在是否报错

    Returns:
        bool: 是否成功
    """
    try:
        path = Path(dir_path)
        path.mkdir(parents=parents, exist_ok=exist_ok)
        return True
    except Exception as e:
        print(f"创建目录失败：{dir_path}，错误：{e}")
        return False


def ensure_extension(file_path: Path, extension: str) -> Path:
    """
    确保文件有指定的扩展名

    Args:
        file_path: 文件路径
        extension: 扩展名（如 '.tex'）

    Returns:
        Path: 带正确扩展名的文件路径
    """
    path = Path(file_path)

    if not extension.startswith('.'):
        extension = '.' + extension

    if path.suffix != extension:
        return path.with_suffix(extension)

    return path


def get_relative_path(file_path: Path, base_path: Path) -> Path:
    """
    获取相对路径

    Args:
        file_path: 文件路径
        base_path: 基准路径

    Returns:
        Path: 相对路径
    """
    try:
        return Path(file_path).relative_to(Path(base_path))
    except ValueError:
        # 如果无法计算相对路径，返回绝对路径
        return Path(file_path).resolve()


def count_lines(file_path: Path) -> int:
    """
    统计文件行数

    Args:
        file_path: 文件路径

    Returns:
        int: 行数
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def get_file_size(file_path: Path) -> int:
    """
    获取文件大小（字节）

    Args:
        file_path: 文件路径

    Returns:
        int: 文件大小（字节）
    """
    try:
        return Path(file_path).stat().st_size
    except Exception:
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 字节数

    Returns:
        str: 格式化的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
