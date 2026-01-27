#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Word PDF 基准生成工具

自动检测模板目录中的 .doc/.docx 文件，
使用 LibreOffice 或 Microsoft Word 转换为 PDF。

使用方法:
    # 基本用法（自动检测模板文件）
    python scripts/generate_baseline.py --project NSFC_Young

    # 指定输入文件
    python scripts/generate_baseline.py --input template/word.docx --output projects/NSFC_Young/.make_latex_model/baselines/word.pdf

    # 使用特定转换器
    python scripts/generate_baseline.py --project NSFC_Young --converter libreoffice
"""

import argparse
import subprocess
import sys
import platform
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# 添加父目录到路径以导入 scripts.core 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scripts.core.workspace_manager import WorkspaceManager
except ImportError:
    WorkspaceManager = None


class BaselineGenerator:
    """Word PDF 基准生成器"""

    def __init__(self, project_name: Optional[str] = None):
        """
        初始化生成器

        Args:
            project_name: 项目名称
        """
        self.project_name = project_name
        self.skill_root = Path(__file__).parent.parent
        self.repo_root = self.skill_root.parent.parent

        # 工作空间管理器
        if WorkspaceManager:
            self.ws_manager = WorkspaceManager(self.skill_root)
        else:
            self.ws_manager = None

        # 检测可用的转换器
        self.available_converters = self._detect_converters()

    def _detect_converters(self) -> List[str]:
        """检测可用的转换器"""
        converters = []

        # 检测 Microsoft Word（macOS）
        if platform.system() == "Darwin":
            word_path = Path("/Applications/Microsoft Word.app")
            if word_path.exists():
                converters.append("word")

        # 检测 LibreOffice
        libreoffice_names = ["soffice", "libreoffice"]
        for name in libreoffice_names:
            try:
                result = subprocess.run(
                    [name, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    converters.append("libreoffice")
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        # QuickLook（macOS，低质量）
        if platform.system() == "Darwin":
            converters.append("quicklook")

        return converters

    def find_word_template(self, project_path: Path) -> Optional[Path]:
        """
        查找项目中的 Word 模板文件

        Args:
            project_path: 项目路径

        Returns:
            Word 模板文件路径
        """
        template_dir = project_path / "template"

        if not template_dir.exists():
            return None

        # 优先查找 .docx，其次 .doc
        patterns = ["*.docx", "*.doc"]

        for pattern in patterns:
            files = list(template_dir.glob(pattern))
            if files:
                # 优先选择“看起来最新”的年份文件（避免硬编码具体年份）
                import re

                def _extract_year(path: Path) -> int:
                    m = re.findall(r"(20\\d{2})", path.name)
                    return int(m[-1]) if m else -1

                files_sorted = sorted(files, key=_extract_year, reverse=True)
                return files_sorted[0]

        return None

    def convert_with_word(self, input_path: Path, output_path: Path) -> bool:
        """
        使用 Microsoft Word 转换（macOS）

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        if platform.system() != "Darwin":
            return False

        # 使用 AppleScript 调用 Word
        script = f'''
        tell application "Microsoft Word"
            open "{input_path}"
            set theDoc to active document
            save as theDoc file name "{output_path}" file format format PDF
            close theDoc saving no
        end tell
        '''

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=120
            )
            return result.returncode == 0 and output_path.exists()
        except (subprocess.TimeoutExpired, Exception):
            return False

    def convert_with_libreoffice(self, input_path: Path, output_dir: Path) -> bool:
        """
        使用 LibreOffice 转换

        Args:
            input_path: 输入文件路径
            output_dir: 输出目录

        Returns:
            是否成功
        """
        libreoffice_cmd = "soffice"

        # 在 macOS 上可能需要完整路径
        if platform.system() == "Darwin":
            macos_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
            if Path(macos_path).exists():
                libreoffice_cmd = macos_path

        try:
            result = subprocess.run(
                [
                    libreoffice_cmd,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(output_dir),
                    str(input_path)
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            # 检查输出文件是否存在
            expected_output = output_dir / (input_path.stem + ".pdf")
            return expected_output.exists()

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False

    def convert_with_quicklook(self, input_path: Path, output_path: Path) -> bool:
        """
        使用 QuickLook 生成缩略图（低质量，仅用于参考）

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        if platform.system() != "Darwin":
            return False

        # QuickLook 生成的是 PNG，不是 PDF
        png_output = output_path.with_suffix(".png")

        try:
            result = subprocess.run(
                [
                    "qlmanage",
                    "-t",
                    "-s", "2000",  # 尺寸
                    "-o", str(output_path.parent),
                    str(input_path)
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            # QuickLook 输出文件名格式为 filename.doc.png
            expected_output = output_path.parent / f"{input_path.name}.png"
            if expected_output.exists():
                # 重命名为目标文件名
                shutil.move(str(expected_output), str(png_output))
                return True

            return False

        except (subprocess.TimeoutExpired, Exception):
            return False

    def convert(self, input_path: Path, output_path: Path,
               converter: Optional[str] = None) -> Dict[str, Any]:
        """
        转换 Word 文件为 PDF

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            converter: 指定转换器（可选）

        Returns:
            转换结果
        """
        result = {
            "success": False,
            "converter": None,
            "input_path": str(input_path),
            "output_path": str(output_path),
            "quality": "unknown",
            "timestamp": datetime.now().isoformat(),
            "error": None
        }

        # 确定使用的转换器
        if converter:
            converters_to_try = [converter] if converter in self.available_converters else []
        else:
            # 按优先级尝试
            converters_to_try = [c for c in ["word", "libreoffice", "quicklook"]
                                if c in self.available_converters]

        if not converters_to_try:
            result["error"] = "没有可用的转换器"
            return result

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 尝试各转换器
        for conv in converters_to_try:
            print(f"  尝试使用 {conv}...")

            success = False
            if conv == "word":
                success = self.convert_with_word(input_path, output_path)
                quality = "high"
            elif conv == "libreoffice":
                success = self.convert_with_libreoffice(input_path, output_path.parent)
                # LibreOffice 输出文件名可能不同，需要重命名
                expected = output_path.parent / (input_path.stem + ".pdf")
                if expected.exists() and expected != output_path:
                    shutil.move(str(expected), str(output_path))
                    success = output_path.exists()
                quality = "medium"
            elif conv == "quicklook":
                success = self.convert_with_quicklook(input_path, output_path)
                quality = "low"

            if success:
                result["success"] = True
                result["converter"] = conv
                result["quality"] = quality
                break

        if not result["success"]:
            result["error"] = "所有转换器都失败了"

        return result

    def verify_pdf_quality(self, pdf_path: Path) -> Dict[str, Any]:
        """
        验证 PDF 质量

        Args:
            pdf_path: PDF 文件路径

        Returns:
            验证结果
        """
        result = {
            "valid": False,
            "file_size_kb": 0,
            "page_count": 0,
            "page_size": None,
            "has_text": False,
            "warnings": []
        }

        if not pdf_path.exists():
            result["warnings"].append("PDF 文件不存在")
            return result

        # 文件大小
        result["file_size_kb"] = round(pdf_path.stat().st_size / 1024, 2)

        if result["file_size_kb"] < 10:
            result["warnings"].append("PDF 文件过小，可能损坏")
            return result

        # 使用 PyMuPDF 分析
        try:
            import fitz
            doc = fitz.open(pdf_path)

            result["page_count"] = len(doc)

            if len(doc) > 0:
                page = doc[0]
                rect = page.rect
                result["page_size"] = {
                    "width_cm": round(rect.width * 0.0352778, 2),
                    "height_cm": round(rect.height * 0.0352778, 2)
                }

                # 检查是否有文本
                text = page.get_text()
                result["has_text"] = len(text.strip()) > 0

            doc.close()
            result["valid"] = True

        except ImportError:
            result["warnings"].append("PyMuPDF 未安装，跳过详细验证")
            result["valid"] = True  # 假设有效
        except Exception as e:
            result["warnings"].append(f"PDF 分析失败: {e}")

        return result

    def generate(self, project_path: Path, output_dir: Optional[Path] = None,
                converter: Optional[str] = None) -> Dict[str, Any]:
        """
        生成 Word PDF 基准

        Args:
            project_path: 项目路径
            output_dir: 输出目录（可选，默认使用工作空间）
            converter: 指定转换器（可选）

        Returns:
            生成结果
        """
        result = {
            "success": False,
            "word_template": None,
            "pdf_path": None,
            "quality_report": None,
            "error": None
        }

        # 查找 Word 模板
        word_template = self.find_word_template(project_path)
        if not word_template:
            result["error"] = f"未找到 Word 模板: {project_path}/template/"
            return result

        result["word_template"] = str(word_template)
        print(f"📄 Word 模板: {word_template.name}")

        # 确定输出目录
        if output_dir is None:
            if self.ws_manager and self.project_name:
                output_dir = self.ws_manager.get_baseline_path(self.project_name)
            else:
                output_dir = project_path / "artifacts" / "baseline"

        output_path = output_dir / "word.pdf"

        # 转换
        print(f"\n🔄 正在转换为 PDF...")
        convert_result = self.convert(word_template, output_path, converter)

        if not convert_result["success"]:
            result["error"] = convert_result["error"]
            return result

        result["pdf_path"] = str(output_path)
        print(f"✅ PDF 已生成: {output_path}")
        print(f"   转换器: {convert_result['converter']}")
        print(f"   质量等级: {convert_result['quality']}")

        # 验证 PDF 质量
        print(f"\n🔍 验证 PDF 质量...")
        quality_report = self.verify_pdf_quality(output_path)
        result["quality_report"] = quality_report

        if quality_report["warnings"]:
            for warning in quality_report["warnings"]:
                print(f"   ⚠️  {warning}")

        print(f"   文件大小: {quality_report['file_size_kb']} KB")
        print(f"   页数: {quality_report['page_count']}")
        if quality_report["page_size"]:
            ps = quality_report["page_size"]
            print(f"   页面尺寸: {ps['width_cm']} x {ps['height_cm']} cm")

        # 保存质量报告
        report_path = output_dir / "quality_report.json"
        full_report = {
            **convert_result,
            "quality_verification": quality_report
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(full_report, f, indent=2, ensure_ascii=False)

        result["success"] = True
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Word PDF 基准生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--project", "-p", type=str,
                       help="项目名称（如 NSFC_Young）")
    parser.add_argument("--input", "-i", type=Path,
                       help="输入 Word 文件路径")
    parser.add_argument("--output", "-o", type=Path,
                       help="输出 PDF 文件路径")
    parser.add_argument("--converter", "-c",
                       choices=["word", "libreoffice", "quicklook"],
                       help="指定转换器")
    parser.add_argument("--list-converters", action="store_true",
                       help="列出可用的转换器")

    args = parser.parse_args()

    # 创建生成器
    generator = BaselineGenerator(args.project)

    # 列出可用转换器
    if args.list_converters:
        print("可用的转换器:")
        for conv in generator.available_converters:
            quality = {"word": "高", "libreoffice": "中", "quicklook": "低"}.get(conv, "未知")
            print(f"  - {conv} (质量: {quality})")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"Word PDF 基准生成工具")
    print(f"{'='*60}")

    # 检查参数
    if args.input:
        # 直接转换模式
        if not args.input.exists():
            print(f"❌ 错误: 输入文件不存在: {args.input}")
            sys.exit(1)

        output_path = args.output or args.input.with_suffix(".pdf")

        result = generator.convert(args.input, output_path, args.converter)

        if result["success"]:
            print(f"\n✅ 转换成功: {output_path}")
        else:
            print(f"\n❌ 转换失败: {result['error']}")
            sys.exit(1)

    elif args.project:
        # 项目模式
        skill_root = Path(__file__).parent.parent
        if not WorkspaceManager:
            print("❌ 错误: WorkspaceManager 不可用，无法安全解析项目路径")
            sys.exit(1)

        try:
            ws_root = WorkspaceManager(skill_root).get_project_workspace(args.project)
        except Exception as e:
            print(f"❌ 错误: 项目路径解析失败: {e}")
            sys.exit(1)

        project_path = ws_root.parent

        print(f"项目: {args.project}")
        print(f"路径: {project_path}")

        result = generator.generate(project_path, converter=args.converter)

        if result["success"]:
            print(f"\n{'='*60}")
            print(f"✅ 基准生成完成")
            print(f"{'='*60}")
        else:
            print(f"\n❌ 生成失败: {result['error']}")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
