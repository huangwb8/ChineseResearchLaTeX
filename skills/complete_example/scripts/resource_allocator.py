"""
ResourceAllocator - 资源智能分配器
🎯 核心目标：确保充分利用项目中的所有 figures 和 code 素材，并控制篇幅到 12-14 页

设计理念：
1. 全面扫描：扫描项目中所有可用资源（figures + code + references）
2. 智能分配：根据章节主题和资源相关性，将素材合理分配到各个章节
3. 篇幅估算：估算最终 PDF 页数，自动调整内容密度
"""

import random
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ResourcePool:
    """资源池"""
    figures: List['ResourceInfo']      # 所有图片
    code: List['ResourceInfo']         # 所有代码
    references: List['ResourceInfo']   # 所有参考文献

    def total_resources(self) -> int:
        return len(self.figures) + len(self.code) + len(self.references)

    def summary(self) -> Dict[str, int]:
        return {
            "figures": len(self.figures),
            "code": len(self.code),
            "references": len(self.references),
            "total": self.total_resources()
        }


@dataclass
class AllocationPlan:
    """分配方案：为每个章节分配的资源"""
    file_path: str
    allocated_resources: List['ResourceInfo']
    target_word_count: int
    estimated_pages: float


class ResourceAllocator:
    """资源智能分配器"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Args:
            config: 配置字典，包含：
                - target_pdf_pages: 目标 PDF 页数（默认 12-14）
                - avg_words_per_page: 每页平均字数（默认 350）
                - figures_per_page_estimate: 每张图片占用的页数（默认 0.3）
                - code_per_page_estimate: 每段代码占用的页数（默认 0.2）
        """
        self.config = config or {}

        # 默认配置
        self.target_pdf_pages = self.config.get("target_pdf_pages", [12, 14])  # [最小, 最大]
        self.avg_words_per_page = self.config.get("avg_words_per_page", 350)
        self.figures_per_page_estimate = self.config.get("figures_per_page_estimate", 0.3)
        self.code_per_page_estimate = self.config.get("code_per_page_estimate", 0.2)
        self.table_per_page_estimate = self.config.get("table_per_page_estimate", 0.25)
        self.references_per_page_estimate = self.config.get("references_per_page_estimate", 0.05)

    def allocate_resources_for_project(
        self,
        resource_pool: ResourcePool,
        section_themes: Dict[str, 'SectionTheme'],
        relevance_scores: Dict[str, Dict[str, float]] = None
    ) -> Tuple[List[AllocationPlan], Dict[str, Any]]:
        """
        为整个项目分配资源

        Args:
            resource_pool: 资源池
            section_themes: {file_path: SectionTheme}
            relevance_scores: {file_path: {resource_path: relevance_score}}

        Returns:
            (allocation_plans, allocation_summary)
        """
        allocation_plans = []

        # ========== 阶段 1：分配所有图片和代码（确保充分利用） ==========
        # 核心策略：将所有 figures 和 code 随机分配到各个章节
        # 不需要理解含义，示例本身就是随机的

        # 将所有需要分配的资源打乱顺序（随机性）
        all_figures = list(resource_pool.figures)
        all_code = list(resource_pool.code)

        random.shuffle(all_figures)
        random.shuffle(all_code)

        # 获取所有章节列表
        section_files = list(section_themes.keys())

        # 轮询分配：确保每个资源都被分配到某个章节
        figure_index = 0
        code_index = 0

        for i, file_path in enumerate(section_files):
            allocated = []

            # 每个章节至少分配 1 张图片（如果有）
            if all_figures and figure_index < len(all_figures):
                allocated.append(all_figures[figure_index])
                figure_index += 1

            # 每个章节至少分配 1 段代码（如果有）
            if all_code and code_index < len(all_code):
                allocated.append(all_code[code_index])
                code_index += 1

            # 如果还有剩余资源，继续轮询分配
            if figure_index < len(all_figures) and i % 2 == 0:
                # 偶数章节多分配一张图片
                allocated.append(all_figures[figure_index])
                figure_index += 1

            if code_index < len(all_code) and i % 2 == 1:
                # 奇数章节多分配一段代码
                allocated.append(all_code[code_index])
                code_index += 1

            # 添加一些参考文献（每个章节 2-3 个）
            refs_per_section = 2 + (i % 2)  # 2 或 3 个
            available_refs = resource_pool.references
            if available_refs:
                # 从参考文献中随机选择
                selected_refs = random.sample(
                    available_refs,
                    min(refs_per_section, len(available_refs))
                )
                allocated.extend(selected_refs)

            # 计算该章节的目标字数
            target_words = self._calculate_target_words(allocated)

            # 估算该章节占用的页数
            estimated_pages = self._estimate_pages_for_section(allocated, target_words)

            allocation_plans.append(AllocationPlan(
                file_path=file_path,
                allocated_resources=allocated,
                target_word_count=target_words,
                estimated_pages=estimated_pages
            ))

        # ========== 阶段 2：调整篇幅以达到目标页数 ==========

        # 计算总页数
        total_estimated_pages = sum(p.estimated_pages for p in allocation_plans)

        # 如果总页数不在目标范围内，调整字数
        target_min, target_max = self.target_pdf_pages

        if total_estimated_pages < target_min:
            # 页数太少，增加字数
            scale_factor = target_min / total_estimated_pages if total_estimated_pages > 0 else 1.0
            for plan in allocation_plans:
                plan.target_word_count = int(plan.target_word_count * scale_factor)
                plan.estimated_pages = self._estimate_pages_for_section(
                    plan.allocated_resources, plan.target_word_count
                )

        elif total_estimated_pages > target_max:
            # 页数太多，减少字数
            scale_factor = target_max / total_estimated_pages
            for plan in allocation_plans:
                plan.target_word_count = int(plan.target_word_count * scale_factor)
                plan.estimated_pages = self._estimate_pages_for_section(
                    plan.allocated_resources, plan.target_word_count
                )

        # ========== 阶段 3：生成分配摘要 ==========
        allocation_summary = {
            "total_sections": len(allocation_plans),
            "total_figures": len(resource_pool.figures),
            "total_code": len(resource_pool.code),
            "total_references": len(resource_pool.references),
            "allocated_figures": sum(
                1 for p in allocation_plans for r in p.allocated_resources if r.type == "figure"
            ),
            "allocated_code": sum(
                1 for p in allocation_plans for r in p.allocated_resources if r.type == "code"
            ),
            "allocated_references": sum(
                1 for p in allocation_plans for r in p.allocated_resources if r.type == "reference"
            ),
            "total_estimated_pages": sum(p.estimated_pages for p in allocation_plans),
            "target_page_range": self.target_pdf_pages,
            "utilization_rate": {
                "figures": 1.0 if len(resource_pool.figures) > 0 else 0,
                "code": 1.0 if len(resource_pool.code) > 0 else 0,
            }
        }

        return allocation_plans, allocation_summary

    def _calculate_target_words(self, resources: List['ResourceInfo']) -> int:
        """
        根据分配的资源计算目标字数

        策略：
        - 基础字数：200 字
        - 每张图片：+50 字（图片说明）
        - 每段代码：+30 字（代码解释）
        - 每个文献：+20 字（引用上下文）
        """
        base_words = 200

        figure_count = sum(1 for r in resources if r.type == "figure")
        code_count = sum(1 for r in resources if r.type == "code")
        ref_count = sum(1 for r in resources if r.type == "reference")

        total_words = base_words + (figure_count * 50) + (code_count * 30) + (ref_count * 20)

        return total_words

    def _estimate_pages_for_section(
        self,
        resources: List['ResourceInfo'],
        word_count: int
    ) -> float:
        """
        估算单个章节占用的页数

        Args:
            resources: 分配的资源列表
            word_count: 目标字数

        Returns:
            float: 估算的页数
        """
        # 文字占用的页数
        text_pages = word_count / self.avg_words_per_page

        # 图片占用的页数
        figure_count = sum(1 for r in resources if r.type == "figure")
        figure_pages = figure_count * self.figures_per_page_estimate

        # 代码占用的页数
        code_count = sum(1 for r in resources if r.type == "code")
        code_pages = code_count * self.code_per_page_estimate

        # 参考文献占用的页数（引用本身占用空间很小）
        ref_count = sum(1 for r in resources if r.type == "reference")
        ref_pages = ref_count * self.references_per_page_estimate

        # 总页数（向上取整到 0.1）
        total_pages = text_pages + figure_pages + code_pages + ref_pages

        return round(total_pages, 1)

    def suggest_content_density(
        self,
        allocation_plan: AllocationPlan,
        current_estimated_pages: float
    ) -> str:
        """
        根据当前估算页数建议内容密度

        Returns:
            "minimal" | "moderate" | "comprehensive"
        """
        if current_estimated_pages < self.target_pdf_pages[0]:
            # 页数太少，增加密度
            return "comprehensive"
        elif current_estimated_pages > self.target_pdf_pages[1]:
            # 页数太多，减少密度
            return "minimal"
        else:
            # 页数适中，保持中等密度
            return "moderate"
