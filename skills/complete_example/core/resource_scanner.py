"""
ResourceScanner - 资源扫描器
🔧 硬编码：纯机械操作，扫描项目中的所有可用资源
"""

from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
import os


@dataclass
class ResourceInfo:
    """资源信息"""
    path: str               # 相对路径
    type: str              # figure/code/reference
    filename: str          # 文件名
    metadata: Dict[str, Any]  # 元数据


@dataclass
class ResourceReport:
    """资源扫描报告"""
    figures: List[ResourceInfo]
    code: List[ResourceInfo]
    references: List[ResourceInfo]
    summary: Dict[str, int]


class ResourceScanner:
    """🔧 硬编码：资源扫描器（纯机械操作）"""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)

    def scan_figures(self) -> List[ResourceInfo]:
        """
        扫描 figures/ 目录

        Returns:
            List[ResourceInfo]: 图片列表
        """
        figures_dir = self.project_path / "figures"
        if not figures_dir.exists():
            return []

        figures = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.pdf', '.eps'}

        for file_path in figures_dir.iterdir():
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in image_extensions:
                continue

            # 提取图片元数据
            metadata = self._extract_image_metadata(file_path)

            figures.append(ResourceInfo(
                path=str(file_path.relative_to(self.project_path)),
                type="figure",
                filename=file_path.name,
                metadata=metadata
            ))

        return figures

    def _extract_image_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取图片元数据"""
        metadata = {
            "filename": file_path.name,
            "extension": file_path.suffix,
            "size_bytes": file_path.stat().st_size
        }

        # 尝试使用 PIL 提取图片尺寸
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format
                metadata["mode"] = img.mode
        except Exception as e:
            metadata["pil_error"] = str(e)

        return metadata

    def scan_code(self) -> List[ResourceInfo]:
        """扫描 code/ 目录"""
        code_dir = self.project_path / "code"
        if not code_dir.exists():
            return []

        code_files = []
        code_extensions = {
            '.py': 'Python',
            '.m': 'MATLAB',
            '.r': 'R',
            '.cpp': 'C++',
            '.c': 'C',
            '.java': 'Java',
        }

        for file_path in code_dir.iterdir():
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            if suffix not in code_extensions:
                continue

            # 统计行数
            line_count = self._count_lines(file_path)

            code_files.append(ResourceInfo(
                path=str(file_path.relative_to(self.project_path)),
                type="code",
                filename=file_path.name,
                metadata={
                    "language": code_extensions[suffix],
                    "lines": line_count,
                    "extension": suffix
                }
            ))

        return code_files

    def _count_lines(self, file_path: Path) -> int:
        """统计文件行数"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def scan_references(self) -> List[ResourceInfo]:
        """扫描 references/ 目录"""
        refs_dir = self.project_path / "references"
        if not refs_dir.exists():
            return []

        references = []
        bib_files = list(refs_dir.glob("*.bib"))

        for bib_file in bib_files:
            # 解析 BibTeX
            entries = self._parse_bibtex(bib_file)

            for entry in entries:
                references.append(ResourceInfo(
                    path=f"references/{bib_file.name}",
                    type="reference",
                    filename=entry.get("key", "unknown"),
                    metadata={
                        "citekey": entry.get("key", ""),
                        "authors": entry.get("author", ""),
                        "year": entry.get("year", ""),
                        "title": entry.get("title", ""),
                        "journal": entry.get("journal", ""),
                        "bib_file": bib_file.name
                    }
                ))

        return references

    def _parse_bibtex(self, bib_file: Path) -> List[Dict[str, str]]:
        """解析 BibTeX 文件"""
        entries = []

        try:
            with open(bib_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单的 BibTeX 解析（提取 @article/@book 等条目）
            import re

            # 匹配条目
            pattern = r'@(\w+)\s*\{([^,]+),\s*\n([^@]+)\}'
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                entry_type = match.group(1)
                citekey = match.group(2)
                entry_content = match.group(3)

                # 提取字段
                entry = {"key": citekey, "type": entry_type}
                field_pattern = r'(\w+)\s*=\s*\{([^}]+)\}'
                field_matches = re.finditer(field_pattern, entry_content)

                for field_match in field_matches:
                    field_name = field_match.group(1)
                    field_value = field_match.group(2)
                    entry[field_name] = field_value

                entries.append(entry)

        except Exception as e:
            print(f"警告：解析 {bib_file} 时出错：{e}")

        return entries

    def scan_all(self) -> ResourceReport:
        """扫描所有资源"""
        figures = self.scan_figures()
        code = self.scan_code()
        refs = self.scan_references()

        return ResourceReport(
            figures=figures,
            code=code,
            references=refs,
            summary={
                "total_figures": len(figures),
                "total_code": len(code),
                "total_references": len(refs)
            }
        )
