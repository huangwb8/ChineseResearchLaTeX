#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收敛检测器

综合判断迭代优化是否达到停止条件，
输出详细的收敛报告，记录每轮迭代的指标变化。

使用方法:
    # 检查单次迭代结果
    python scripts/convergence_detector.py --project NSFC_Young --iteration 3

    # 检查是否应该停止迭代
    python scripts/convergence_detector.py --project NSFC_Young --check-stop

    # 生成收敛报告
    python scripts/convergence_detector.py --project NSFC_Young --report
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scripts.core.workspace_manager import WorkspaceManager
except ImportError:
    WorkspaceManager = None


class StopReason(Enum):
    """停止原因枚举"""
    CONVERGED = "converged"              # 达到收敛阈值
    NO_IMPROVEMENT = "no_improvement"    # 连续无改善
    MAX_ITERATIONS = "max_iterations"    # 达到最大迭代次数
    COMPILATION_FAILED = "compilation_failed"  # 编译失败
    CONTINUE = "continue"                # 继续迭代


class ConvergenceDetector:
    """收敛检测器"""

    def __init__(self, project_name: str, config: Optional[Dict] = None):
        """
        初始化检测器

        Args:
            project_name: 项目名称
            config: 配置参数（可选）
        """
        self.project_name = project_name
        self.skill_root = Path(__file__).parent.parent

        # 工作空间管理器
        if WorkspaceManager:
            self.ws_manager = WorkspaceManager(self.skill_root)
        else:
            self.ws_manager = None

        # 默认配置
        self.config = {
            "max_iterations": 30,
            "convergence_threshold": 0.01,
            "no_improvement_limit": 5,
            "compilation_required": True,
        }

        if config:
            self.config.update(config)

        # 加载配置文件
        self._load_config()

    def _load_config(self):
        """从配置文件加载设置"""
        config_path = self.skill_root / "config.yaml"

        if config_path.exists():
            try:
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    full_config = yaml.safe_load(f)
                    if "iteration" in full_config:
                        self.config.update(full_config["iteration"])
            except Exception:
                pass

    def load_iteration_metrics(self, iteration_num: int) -> Optional[Dict[str, Any]]:
        """
        加载指定迭代的指标数据

        Args:
            iteration_num: 迭代编号

        Returns:
            指标数据
        """
        if not self.ws_manager:
            return None

        iter_dir = self.ws_manager.get_iteration_path(self.project_name, iteration_num)
        metrics_file = iter_dir / "metrics.json"

        if metrics_file.exists():
            with open(metrics_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return None

    def load_all_iterations(self) -> List[Dict[str, Any]]:
        """
        加载所有迭代的指标数据

        Returns:
            指标数据列表
        """
        iterations = []

        if not self.ws_manager:
            return iterations

        ws = self.ws_manager.get_project_workspace(self.project_name)
        iterations_dir = ws / "iterations"

        if not iterations_dir.exists():
            return iterations

        # 按编号排序
        iter_dirs = sorted(iterations_dir.glob("iteration_*"))

        for iter_dir in iter_dirs:
            metrics_file = iter_dir / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r", encoding="utf-8") as f:
                    iterations.append(json.load(f))

        return iterations

    def check_convergence(self, current_ratio: float) -> Tuple[bool, str]:
        """
        检查是否达到收敛阈值

        Args:
            current_ratio: 当前像素差异比例

        Returns:
            (是否收敛, 说明)
        """
        threshold = self.config.get("convergence_threshold", 0.03)

        if current_ratio < threshold:
            return True, f"像素差异比例 {current_ratio:.4f} < 阈值 {threshold}"

        return False, f"像素差异比例 {current_ratio:.4f} >= 阈值 {threshold}"

    def check_no_improvement(self, iterations: List[Dict]) -> Tuple[bool, int]:
        """
        检查是否连续无改善

        Args:
            iterations: 迭代历史

        Returns:
            (是否应该停止, 无改善轮数)
        """
        limit = self.config.get("no_improvement_limit", 3)

        if len(iterations) < 2:
            return False, 0

        # 提取历史 changed_ratio
        ratios = []
        for it in iterations:
            if "changed_ratio" in it:
                ratios.append(it["changed_ratio"])

        if len(ratios) < 2:
            return False, 0

        # 检查最近几轮是否有改善
        no_improvement_count = 0
        best_ratio = ratios[0]

        for i, ratio in enumerate(ratios[1:], 1):
            if ratio < best_ratio - 0.001:  # 有明显改善
                best_ratio = ratio
                no_improvement_count = 0
            else:
                no_improvement_count += 1

        return no_improvement_count >= limit, no_improvement_count

    def check_max_iterations(self, current_iteration: int) -> Tuple[bool, str]:
        """
        检查是否达到最大迭代次数

        Args:
            current_iteration: 当前迭代次数

        Returns:
            (是否应该停止, 说明)
        """
        max_iter = self.config.get("max_iterations", 10)

        if current_iteration >= max_iter:
            return True, f"已达到最大迭代次数 {max_iter}"

        return False, f"当前迭代 {current_iteration}/{max_iter}"

    def should_stop(self, current_metrics: Optional[Dict] = None) -> Tuple[StopReason, str]:
        """
        综合判断是否应该停止迭代

        Args:
            current_metrics: 当前指标（可选）

        Returns:
            (停止原因, 详细说明)
        """
        # 加载所有迭代历史
        iterations = self.load_all_iterations()
        current_iteration = len(iterations)

        # 如果提供了当前指标，加入列表
        if current_metrics:
            iterations.append(current_metrics)
            current_iteration += 1

        # 检查 1：编译状态
        if current_metrics and current_metrics.get("compilation_failed"):
            return StopReason.COMPILATION_FAILED, "编译失败，立即停止"

        # 检查 2：收敛阈值
        if iterations:
            latest = iterations[-1]
            if "changed_ratio" in latest:
                converged, msg = self.check_convergence(latest["changed_ratio"])
                if converged:
                    return StopReason.CONVERGED, msg

        # 检查 3：连续无改善
        should_stop, no_imp_count = self.check_no_improvement(iterations)
        if should_stop:
            return StopReason.NO_IMPROVEMENT, f"连续 {no_imp_count} 轮无改善"

        # 检查 4：最大迭代次数
        max_reached, msg = self.check_max_iterations(current_iteration)
        if max_reached:
            return StopReason.MAX_ITERATIONS, msg

        return StopReason.CONTINUE, f"继续迭代（第 {current_iteration + 1} 轮）"

    def get_best_iteration(self) -> Optional[Dict[str, Any]]:
        """
        获取最佳迭代结果

        Returns:
            最佳迭代的指标数据
        """
        iterations = self.load_all_iterations()

        if not iterations:
            return None

        # 按 changed_ratio 排序，找最小值
        best = min(
            [it for it in iterations if "changed_ratio" in it],
            key=lambda x: x["changed_ratio"],
            default=None
        )

        return best

    def generate_report(self) -> Dict[str, Any]:
        """
        生成收敛报告

        Returns:
            报告数据
        """
        iterations = self.load_all_iterations()

        report = {
            "project_name": self.project_name,
            "generated_at": datetime.now().isoformat(),
            "total_iterations": len(iterations),
            "config": self.config,
            "iterations": [],
            "summary": {},
            "recommendation": ""
        }

        if not iterations:
            report["recommendation"] = "没有迭代历史，请先运行优化"
            return report

        # 迭代历史
        for it in iterations:
            report["iterations"].append({
                "iteration": it.get("iteration", 0),
                "changed_ratio": it.get("changed_ratio", None),
                "timestamp": it.get("timestamp", None),
            })

        # 提取所有 changed_ratio
        ratios = [it["changed_ratio"] for it in iterations if "changed_ratio" in it]

        if ratios:
            report["summary"] = {
                "initial_ratio": ratios[0],
                "final_ratio": ratios[-1],
                "best_ratio": min(ratios),
                "worst_ratio": max(ratios),
                "improvement": ratios[0] - ratios[-1],
                "improvement_percent": (ratios[0] - ratios[-1]) / ratios[0] * 100 if ratios[0] > 0 else 0,
            }

            # 生成建议
            stop_reason, msg = self.should_stop()

            if stop_reason == StopReason.CONVERGED:
                report["recommendation"] = f"✅ 优化已收敛: {msg}"
            elif stop_reason == StopReason.NO_IMPROVEMENT:
                report["recommendation"] = f"⚠️ 建议停止: {msg}。最佳结果在迭代 {self._find_best_iteration_num(ratios)}"
            elif stop_reason == StopReason.MAX_ITERATIONS:
                report["recommendation"] = f"⚠️ 已达上限: {msg}"
            else:
                report["recommendation"] = f"💡 可以继续优化，当前最佳差异比例: {min(ratios):.4f}"

        return report

    def _find_best_iteration_num(self, ratios: List[float]) -> int:
        """找到最佳迭代编号"""
        if not ratios:
            return 0
        return ratios.index(min(ratios)) + 1

    def print_report(self):
        """打印收敛报告"""
        report = self.generate_report()

        print(f"\n{'='*60}")
        print(f"收敛检测报告")
        print(f"{'='*60}")
        print(f"项目: {report['project_name']}")
        print(f"迭代次数: {report['total_iterations']}")

        if report["summary"]:
            s = report["summary"]
            print(f"\n📊 指标摘要:")
            print(f"   初始差异: {s['initial_ratio']:.4f}")
            print(f"   最终差异: {s['final_ratio']:.4f}")
            print(f"   最佳差异: {s['best_ratio']:.4f}")
            print(f"   改善幅度: {s['improvement']:.4f} ({s['improvement_percent']:.1f}%)")

        if report["iterations"]:
            print(f"\n📈 迭代历史:")
            for it in report["iterations"]:
                ratio = it.get("changed_ratio", "N/A")
                if isinstance(ratio, float):
                    print(f"   第 {it['iteration']} 轮: {ratio:.4f}")
                else:
                    print(f"   第 {it['iteration']} 轮: {ratio}")

        print(f"\n💬 建议: {report['recommendation']}")
        print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="收敛检测器",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--project", "-p", type=str, required=True,
                       help="项目名称（如 NSFC_Young）")
    parser.add_argument("--iteration", "-i", type=int,
                       help="检查指定迭代的指标")
    parser.add_argument("--check-stop", action="store_true",
                       help="检查是否应该停止迭代")
    parser.add_argument("--report", "-r", action="store_true",
                       help="生成收敛报告")
    parser.add_argument("--json", action="store_true",
                       help="以 JSON 格式输出")

    args = parser.parse_args()

    # 创建检测器
    detector = ConvergenceDetector(args.project)

    if args.iteration:
        # 查看指定迭代
        metrics = detector.load_iteration_metrics(args.iteration)
        if metrics:
            if args.json:
                print(json.dumps(metrics, indent=2, ensure_ascii=False))
            else:
                print(f"迭代 {args.iteration} 指标:")
                for key, value in metrics.items():
                    print(f"  {key}: {value}")
        else:
            print(f"未找到迭代 {args.iteration} 的数据")

    elif args.check_stop:
        # 检查是否停止
        reason, msg = detector.should_stop()
        if args.json:
            print(json.dumps({
                "should_stop": reason != StopReason.CONTINUE,
                "reason": reason.value,
                "message": msg
            }, indent=2, ensure_ascii=False))
        else:
            if reason == StopReason.CONTINUE:
                print(f"✅ 可以继续: {msg}")
            else:
                print(f"⏹️ 建议停止: {msg}")
                print(f"   原因: {reason.value}")

    elif args.report:
        # 生成报告
        if args.json:
            report = detector.generate_report()
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            detector.print_report()

    else:
        # 默认显示报告
        detector.print_report()


if __name__ == "__main__":
    main()
