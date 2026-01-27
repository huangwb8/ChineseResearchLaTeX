#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能参数调整器

分析像素对比的差异热图，识别差异区域，
根据差异特征推断需要调整的 LaTeX 参数，
生成具体的修改建议。

使用方法:
    # 分析差异并生成建议
    python scripts/intelligent_adjust.py --project NSFC_Young --iteration 1

    # 指定基准和输出 PDF
    python scripts/intelligent_adjust.py --baseline word.pdf --output main.pdf

    # 生成 JSON 格式的调整建议
    python scripts/intelligent_adjust.py --project NSFC_Young --json
"""

import argparse
import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.workspace_manager import WorkspaceManager
except ImportError:
    WorkspaceManager = None


class DifferenceType(Enum):
    """差异类型枚举"""
    LINE_BREAK = "line_break"          # 换行位置差异
    VERTICAL_OFFSET = "vertical_offset"  # 垂直偏移
    HORIZONTAL_OFFSET = "horizontal_offset"  # 水平偏移
    COLOR_MISMATCH = "color_mismatch"  # 颜色不一致
    FONT_SIZE = "font_size"            # 字号差异
    SPACING = "spacing"                # 间距差异
    MARGIN = "margin"                  # 边距差异
    UNKNOWN = "unknown"                # 未知差异


@dataclass
class Adjustment:
    """参数调整建议"""
    parameter: str          # 参数名称
    current_value: Any      # 当前值
    suggested_value: Any    # 建议值
    confidence: float       # 置信度 (0-1)
    reason: str             # 调整原因
    latex_code: str         # LaTeX 代码修改


@dataclass
class DifferenceRegion:
    """差异区域"""
    type: DifferenceType
    location: str           # 位置描述（如 "top", "middle", "bottom"）
    magnitude: float        # 差异程度 (0-1)
    area_ratio: float       # 影响区域比例


class IntelligentAdjuster:
    """智能参数调整器"""

    def __init__(self, project_name: Optional[str] = None):
        """
        初始化调整器

        Args:
            project_name: 项目名称
        """
        self.project_name = project_name
        self.skill_root = Path(__file__).parent.parent

        # 工作空间管理器
        if WorkspaceManager:
            self.ws_manager = WorkspaceManager(self.skill_root)
        else:
            self.ws_manager = None

        # 加载配置
        self.config = self._load_config()

        # 差异类型与参数的映射关系
        self.difference_parameter_map = {
            DifferenceType.LINE_BREAK: ["font_size", "char_spacing", "word_spacing"],
            DifferenceType.VERTICAL_OFFSET: ["line_spacing", "paragraph_spacing", "baselinestretch"],
            DifferenceType.HORIZONTAL_OFFSET: ["margin_left", "margin_right", "indent"],
            DifferenceType.COLOR_MISMATCH: ["color_rgb"],
            DifferenceType.FONT_SIZE: ["font_size"],
            DifferenceType.SPACING: ["line_spacing", "paragraph_spacing"],
            DifferenceType.MARGIN: ["margin_left", "margin_right", "margin_top", "margin_bottom"],
        }

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config = {
            "adjustment_granularity": {
                "font_size_pt": 0.1,
                "line_spacing": 0.05,
                "margin_cm": 0.05,
                "color_rgb": 1,
            }
        }

        config_path = self.skill_root / "config.yaml"
        if config_path.exists():
            try:
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    full_config = yaml.safe_load(f)
                    if "iteration" in full_config and "adjustment_granularity" in full_config["iteration"]:
                        config["adjustment_granularity"].update(
                            full_config["iteration"]["adjustment_granularity"]
                        )
            except Exception:
                pass

        return config

    def analyze_pixel_differences(self, diff_mask, img_shape: Tuple[int, int]) -> List[DifferenceRegion]:
        """
        分析像素差异区域

        Args:
            diff_mask: 差异掩码（numpy 数组）
            img_shape: 图像尺寸 (height, width)

        Returns:
            差异区域列表
        """
        import numpy as np

        regions = []
        height, width = img_shape

        # 将图像分为上中下三个区域
        region_height = height // 3

        for i, location in enumerate(["top", "middle", "bottom"]):
            start_y = i * region_height
            end_y = (i + 1) * region_height if i < 2 else height

            region_mask = diff_mask[start_y:end_y, :]
            diff_ratio = np.sum(region_mask) / region_mask.size

            if diff_ratio > 0.01:  # 差异超过 1%
                # 分析差异特征
                diff_type = self._classify_difference(region_mask, diff_ratio)
                regions.append(DifferenceRegion(
                    type=diff_type,
                    location=location,
                    magnitude=diff_ratio,
                    area_ratio=diff_ratio
                ))

        return regions

    def _classify_difference(self, region_mask, diff_ratio: float) -> DifferenceType:
        """
        分类差异类型

        Args:
            region_mask: 区域差异掩码
            diff_ratio: 差异比例

        Returns:
            差异类型
        """
        import numpy as np

        # 分析差异分布
        row_sums = np.sum(region_mask, axis=1)
        col_sums = np.sum(region_mask, axis=0)

        # 计算差异的"条带性"
        row_variance = np.var(row_sums)
        col_variance = np.var(col_sums)

        if row_variance > col_variance * 2:
            # 水平条带状差异 -> 可能是换行位置不同
            return DifferenceType.LINE_BREAK
        elif col_variance > row_variance * 2:
            # 垂直条带状差异 -> 可能是边距差异
            return DifferenceType.MARGIN
        elif diff_ratio < 0.05:
            # 轻微差异 -> 可能是间距或字号微调
            return DifferenceType.SPACING
        else:
            return DifferenceType.UNKNOWN

    def analyze_style_differences(self, baseline_analysis: Dict,
                                  current_analysis: Dict) -> List[DifferenceRegion]:
        """
        分析样式参数差异

        Args:
            baseline_analysis: 基准 PDF 分析结果
            current_analysis: 当前 PDF 分析结果

        Returns:
            差异区域列表
        """
        regions = []

        # 比较行距
        baseline_spacing = baseline_analysis.get("line_spacing_pt", 0)
        current_spacing = current_analysis.get("line_spacing_pt", 0)

        if abs(baseline_spacing - current_spacing) > 0.5:
            regions.append(DifferenceRegion(
                type=DifferenceType.VERTICAL_OFFSET,
                location="全文",
                magnitude=abs(baseline_spacing - current_spacing) / max(baseline_spacing, 1),
                area_ratio=1.0
            ))

        # 比较边距
        baseline_margins = baseline_analysis.get("layout", {}).get("margins_cm", {})
        current_margins = current_analysis.get("layout", {}).get("margins_cm", {})

        for side in ["left", "right", "top", "bottom"]:
            base_val = baseline_margins.get(side, 0)
            curr_val = current_margins.get(side, 0)

            if base_val and curr_val and abs(base_val - curr_val) > 0.1:
                regions.append(DifferenceRegion(
                    type=DifferenceType.MARGIN,
                    location=f"边距_{side}",
                    magnitude=abs(base_val - curr_val),
                    area_ratio=0.1
                ))

        return regions

    def generate_adjustments(self, differences: List[DifferenceRegion],
                            config_content: str) -> List[Adjustment]:
        """
        根据差异生成参数调整建议

        Args:
            differences: 差异区域列表
            config_content: 当前 @config.tex 内容

        Returns:
            调整建议列表
        """
        adjustments = []
        granularity = self.config["adjustment_granularity"]

        for diff in differences:
            if diff.type == DifferenceType.LINE_BREAK:
                # 换行位置差异 -> 调整字号或字间距
                adj = self._suggest_font_size_adjustment(config_content, granularity)
                if adj:
                    adjustments.append(adj)

            elif diff.type == DifferenceType.VERTICAL_OFFSET:
                # 垂直偏移 -> 调整行距
                adj = self._suggest_line_spacing_adjustment(
                    config_content, granularity, diff.magnitude
                )
                if adj:
                    adjustments.append(adj)

            elif diff.type == DifferenceType.MARGIN:
                # 边距差异 -> 调整 geometry
                adj = self._suggest_margin_adjustment(
                    config_content, diff.location, granularity
                )
                if adj:
                    adjustments.append(adj)

            elif diff.type == DifferenceType.SPACING:
                # 间距差异 -> 调整段间距或行距
                adj = self._suggest_spacing_adjustment(config_content, granularity)
                if adj:
                    adjustments.append(adj)

        return adjustments

    def _suggest_font_size_adjustment(self, config_content: str,
                                     granularity: Dict) -> Optional[Adjustment]:
        """建议字号调整"""
        # 查找当前字号定义
        pattern = r'\\newcommand\{\\xiaosi\}\{\\fontsize\{([\d.]+)pt\}'
        match = re.search(pattern, config_content)

        if match:
            current_size = float(match.group(1))
            step = granularity.get("font_size_pt", 0.1)
            new_size = current_size - step  # 减小字号使每行容纳更多字

            return Adjustment(
                parameter="font_size_xiaosi",
                current_value=f"{current_size}pt",
                suggested_value=f"{new_size}pt",
                confidence=0.6,
                reason="换行位置差异，尝试减小字号",
                latex_code=f"\\newcommand{{\\xiaosi}}{{\\fontsize{{{new_size}pt}}"
            )

        return None

    def _suggest_line_spacing_adjustment(self, config_content: str,
                                        granularity: Dict,
                                        magnitude: float) -> Optional[Adjustment]:
        """建议行距调整"""
        # 查找当前行距
        pattern = r'\\renewcommand\{\\baselinestretch\}\{([\d.]+)\}'
        match = re.search(pattern, config_content)

        if match:
            current_spacing = float(match.group(1))
            step = granularity.get("line_spacing", 0.05)

            # 根据差异方向决定增减
            new_spacing = current_spacing - step if magnitude > 0 else current_spacing + step

            return Adjustment(
                parameter="baselinestretch",
                current_value=str(current_spacing),
                suggested_value=str(round(new_spacing, 2)),
                confidence=0.7,
                reason=f"垂直位置偏移（差异: {magnitude:.2%}）",
                latex_code=f"\\renewcommand{{\\baselinestretch}}{{{round(new_spacing, 2)}}}"
            )

        return None

    def _suggest_margin_adjustment(self, config_content: str,
                                  location: str,
                                  granularity: Dict) -> Optional[Adjustment]:
        """建议边距调整"""
        # 解析位置
        side = location.replace("边距_", "")

        # 查找 geometry 设置
        margin_key = {
            "left": "hmarginratio",
            "right": "hmarginratio",
            "top": "top",
            "bottom": "bottom"
        }.get(side, side)

        pattern = rf'{margin_key}\s*=\s*([\d.]+)\s*cm'
        match = re.search(pattern, config_content)

        if match:
            current_margin = float(match.group(1))
            step = granularity.get("margin_cm", 0.05)
            new_margin = current_margin + step

            return Adjustment(
                parameter=f"margin_{side}",
                current_value=f"{current_margin}cm",
                suggested_value=f"{round(new_margin, 2)}cm",
                confidence=0.8,
                reason=f"{side}边距差异",
                latex_code=f"{margin_key}={round(new_margin, 2)}cm"
            )

        return None

    def _suggest_spacing_adjustment(self, config_content: str,
                                   granularity: Dict) -> Optional[Adjustment]:
        """建议间距调整"""
        # 查找段前段后间距
        pattern = r'\\setlength\{\\parskip\}\{([\d.]+)(em|pt)\}'
        match = re.search(pattern, config_content)

        if match:
            current_spacing = float(match.group(1))
            unit = match.group(2)
            step = 0.1 if unit == "em" else 1.0
            new_spacing = current_spacing - step

            return Adjustment(
                parameter="parskip",
                current_value=f"{current_spacing}{unit}",
                suggested_value=f"{round(new_spacing, 2)}{unit}",
                confidence=0.5,
                reason="段间距调整",
                latex_code=f"\\setlength{{\\parskip}}{{{round(new_spacing, 2)}{unit}}}"
            )

        return None

    def load_and_analyze(self, iteration_num: Optional[int] = None) -> Dict[str, Any]:
        """
        加载并分析指定迭代的差异

        Args:
            iteration_num: 迭代编号（可选，默认使用最新）

        Returns:
            分析结果
        """
        if not self.ws_manager or not self.project_name:
            return {"error": "工作空间管理器未初始化"}

        ws = self.ws_manager.get_project_workspace(self.project_name)

        # 加载基准分析
        baseline_dir = ws / "baseline"
        baseline_analysis_files = list(baseline_dir.glob("*_analysis.json"))

        if not baseline_analysis_files:
            return {"error": "未找到基准分析文件"}

        with open(baseline_analysis_files[0], "r", encoding="utf-8") as f:
            baseline_analysis = json.load(f)

        # 加载项目配置
        repo_root = self.skill_root.parent.parent
        config_path = repo_root / "projects" / self.project_name / "extraTex" / "@config.tex"

        if config_path.exists():
            config_content = config_path.read_text(encoding="utf-8")
        else:
            config_content = ""

        # 生成调整建议（基于样式分析）
        differences = self.analyze_style_differences(baseline_analysis, {})
        adjustments = self.generate_adjustments(differences, config_content)

        return {
            "project_name": self.project_name,
            "baseline_analysis": str(baseline_analysis_files[0]),
            "differences": [asdict(d) for d in differences],
            "adjustments": [asdict(a) for a in adjustments],
        }

    def apply_adjustment(self, adjustment: Adjustment, config_path: Path) -> bool:
        """
        应用单个调整建议到配置文件

        Args:
            adjustment: 调整建议
            config_path: 配置文件路径

        Returns:
            是否成功
        """
        try:
            config_content = config_path.read_text(encoding="utf-8")

            # 根据参数类型应用不同的修改
            if adjustment.parameter == "font_size_xiaosi":
                # 修改字号
                pattern = r'(\\newcommand\{\\xiaosi\}\{\\fontsize\{)[\d.]+(pt\})'
                new_code = adjustment.latex_code
                match = re.search(pattern, config_content)
                if match:
                    config_content = re.sub(pattern, new_code, config_content)
                else:
                    return False

            elif adjustment.parameter == "baselinestretch":
                # 修改行距
                pattern = r'(\\renewcommand\{\\baselinestretch\}\{)[\d.]+(\})'
                replacement = f"\\1{adjustment.suggested_value}\\2"
                config_content = re.sub(pattern, replacement, config_content)

            elif adjustment.parameter.startswith("margin_"):
                # 修改边距
                pattern = rf'(\\geometry\{{.*?{adjustment.latex_code.split("=")[0].strip()}\s*=\s*)[\d.]+(\s*cm.*?\}})'
                replacement = rf"\1{adjustment.suggested_value}\2"
                config_content = re.sub(pattern, replacement, config_content, flags=re.DOTALL)

            elif adjustment.parameter == "parskip":
                # 修改段间距
                pattern = r'(\\setlength\{\\parskip\}\{)[\d.]+(em|pt)\})'
                replacement = rf"\1{adjustment.suggested_value}\2"
                config_content = re.sub(pattern, replacement, config_content)

            else:
                return False

            # 写回文件
            config_path.write_text(config_content, encoding="utf-8")
            return True

        except Exception as e:
            print(f"应用调整失败: {e}")
            return False

    def auto_adjust_from_pixel_diff(self, diff_ratio: float,
                                    config_path: Path,
                                    iteration: int) -> bool:
        """
        根据像素差异比例自动调整参数

        Args:
            diff_ratio: 当前差异比例
            config_path: 配置文件路径
            iteration: 当前迭代次数

        Returns:
            是否成功应用调整
        """
        if diff_ratio < 0.01:
            # 差异已足够小，无需调整
            return False

        config_content = config_path.read_text(encoding="utf-8")
        granularity = self.config["adjustment_granularity"]

        # 根据差异比例和迭代次数选择调整策略
        if diff_ratio > 0.05:
            # 大差异：使用较大调整粒度
            font_step = granularity["font_size_pt"] * 2
            spacing_step = granularity["line_spacing"] * 2
        else:
            # 小差异：使用精细调整粒度
            font_step = granularity["font_size_pt"]
            spacing_step = granularity["line_spacing"]

        adjustments = []

        # 策略1: 优先调整字号（影响换行）
        font_pattern = r'\\newcommand\{\\xiaosi\}\{\\fontsize\{([\d.]+)pt\}'
        font_match = re.search(font_pattern, config_content)
        if font_match:
            current_size = float(font_match.group(1))
            # 根据差异趋势决定调整方向
            # 这里使用历史趋势判断（如果有）
            new_size = current_size - font_step * 0.5  # 保守调整

            if new_size > 8:  # 最小字号限制
                adjustments.append(Adjustment(
                    parameter="font_size_xiaosi",
                    current_value=f"{current_size}pt",
                    suggested_value=f"{new_size:.1f}pt",
                    confidence=0.7,
                    reason=f"自动优化：差异比例 {diff_ratio:.2%}",
                    latex_code=f"\\newcommand{{\\xiaosi}}{{\\fontsize{{{new_size:.1f}pt}}"
                ))

        # 策略2: 调整行距
        spacing_pattern = r'\\renewcommand\{\\baselinestretch\}\{([\d.]+)\}'
        spacing_match = re.search(spacing_pattern, config_content)
        if spacing_match and len(adjustments) == 0:
            current_spacing = float(spacing_match.group(1))
            new_spacing = max(1.0, current_spacing - spacing_step * 0.3)

            adjustments.append(Adjustment(
                parameter="baselinestretch",
                current_value=str(current_spacing),
                suggested_value=f"{new_spacing:.2f}",
                confidence=0.6,
                reason=f"自动优化：差异比例 {diff_ratio:.2%}",
                latex_code=f"\\renewcommand{{\\baselinestretch}}{{{new_spacing:.2f}}}"
            ))

        # 应用调整（每次只应用一个调整，避免过度调整）
        if adjustments:
            best_adj = max(adjustments, key=lambda a: a.confidence)
            success = self.apply_adjustment(best_adj, config_path)
            if success:
                print(f"  ✅ 自动调整: {best_adj.parameter} {best_adj.current_value} → {best_adj.suggested_value}")
                return True

        return False


def main():
    parser = argparse.ArgumentParser(
        description="智能参数调整器",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--project", "-p", type=str,
                       help="项目名称（如 NSFC_Young）")
    parser.add_argument("--iteration", "-i", type=int,
                       help="分析指定迭代")
    parser.add_argument("--baseline", type=Path,
                       help="基准 PDF 路径")
    parser.add_argument("--output", type=Path,
                       help="输出 PDF 路径")
    parser.add_argument("--json", action="store_true",
                       help="JSON 格式输出")

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"智能参数调整器")
    print(f"{'='*60}")

    if args.project:
        adjuster = IntelligentAdjuster(args.project)
        result = adjuster.load_and_analyze(args.iteration)

        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            if "error" in result:
                print(f"❌ 错误: {result['error']}")
            else:
                print(f"项目: {result['project_name']}")
                print(f"基准分析: {result['baseline_analysis']}")

                print(f"\n📊 检测到的差异:")
                for diff in result["differences"]:
                    print(f"   - {diff['type']}: {diff['location']} (程度: {diff['magnitude']:.2%})")

                print(f"\n💡 调整建议:")
                for adj in result["adjustments"]:
                    print(f"\n   参数: {adj['parameter']}")
                    print(f"   当前值: {adj['current_value']}")
                    print(f"   建议值: {adj['suggested_value']}")
                    print(f"   置信度: {adj['confidence']:.0%}")
                    print(f"   原因: {adj['reason']}")
                    print(f"   代码: {adj['latex_code']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
