"""
AIContentGenerator - AI 增强内容生成器
🧠 AI + 🤝 协作：生成连贯的叙述性文本，智能整合资源
"""

from typing import List, Dict, Any
from pathlib import Path
import re


class AIContentGenerator:
    """AI 驱动的智能内容生成器"""

    def __init__(self, llm_client, templates: dict, format_guard: 'FormatGuard'):
        """
        Args:
            llm_client: LLM 客户端
            templates: Jinja2 模板字典
            format_guard: 格式保护器实例
        """
        self.llm = llm_client
        self.templates = templates
        self.guard = format_guard

    def generate_section_content(
        self,
        resources: List['ResourceInfo'],
        section_theme: 'SectionTheme',
        existing_content: str,
        content_density: str = "moderate",
        narrative_hint: str = None
    ) -> str:
        """
        为章节生成 AI 增强的示例内容

        Args:
            resources: 可用资源列表
            section_theme: 章节主题（AI 分析结果）
            existing_content: 现有内容
            content_density: 内容密度
            narrative_hint: 用户自定义的叙事提示（可选）

        Returns:
            str: 生成的内容（保留格式定义）

        工作流程：
        1. 🔧 硬编码：提取受保护的格式区域
        2. 🧠 AI：分析资源相关性并选择
        3. 🧠 AI：生成连贯的叙述性内容（支持用户提示）
        4. 🤝 协作：AI 内容 + 硬编码模板包装
        5. 🧠 AI：自我检查和优化
        """

        # ========== 阶段 1：硬编码 - 提取保护区域 ==========
        protected_zones = self.guard.extract_protected_zones(existing_content)

        # ========== 阶段 2：AI - 智能资源选择 ==========
        from .semantic_analyzer import SemanticAnalyzer
        analyzer = SemanticAnalyzer(self.llm)

        relevance_scores = {}
        for resource in resources:
            relevance = analyzer.reason_resource_relevance(resource, section_theme)
            relevance_scores[resource.path] = relevance.relevance_score

        # 根据密度级别选择资源数量
        k_map = {"minimal": 2, "moderate": 4, "comprehensive": 6}
        k = k_map.get(content_density, 4)

        # 硬编码：Top-K 选择
        selected_resources = sorted(
            resources,
            key=lambda r: relevance_scores.get(r.path, 0),
            reverse=True
        )[:k]

        # ========== 阶段 3：AI - 生成叙述性内容 ==========
        narrative = self._generate_narrative(
            selected_resources, section_theme, existing_content, narrative_hint
        )

        # ========== 阶段 4：协作 - 包装 LaTeX 代码 ==========
        formatted_content = self._wrap_with_latex_code(
            narrative, selected_resources, protected_zones
        )

        # ========== 阶段 5：AI - 自我优化 ==========
        refined_content = self._refine_content(
            formatted_content, section_theme
        )

        # ========== 阶段 6：硬编码 - 最终验证 ==========
        self._validate_format_preservation(protected_zones, refined_content)

        return refined_content

    def _generate_narrative(
        self,
        resources: List['ResourceInfo'],
        theme: 'SectionTheme',
        context: str,
        narrative_hint: str = None
    ) -> str:
        """AI：生成连贯的叙述性文本"""

        # 构建 AI Prompt
        prompt = f"""
你是一位经验丰富的科研写作助手，专精于国家自然科学基金申请书的撰写。
根据以下信息，生成一段连贯的示例内容。

## 章节信息
- 主题：{theme.theme}
- 关键概念：{', '.join(theme.key_concepts)}
- 写作风格：{theme.writing_style}
- 目标读者：{theme.target_audience}

## 用户叙事提示
{narrative_hint or "（未提供，AI 根据章节主题自动推断）"}

## 上下文片段（前 500 字）
{context[:500]}

## 可用资源
{self._format_resources_for_prompt(resources)}

## 生成要求
1. 生成 200-400 字的示例段落
2. 自然地引用资源，不要生硬堆砌
3. 使用正式的学术写作风格
4. **重要**：根据【用户叙事提示】调整内容方向和风格
5. **允许编造**：这是示例场景，可以根据提示编造合理的研究内容、数据和结论
6. 包含以下结构：
   - 【引入句】开篇点题，引出本段内容
   - 【资源整合】有机整合图片、文献、代码等资源
   - 【说明句】对资源进行简要说明
   - 【总结句】收束本段，承上启下

7. 在应该插入 LaTeX 代码的地方用 {{PLACEHOLDER:资源路径}} 标记
   - 图片：{{PLACEHOLDER:figures/xxx.jpg}}
   - 文献：{{PLACEHOLDER:references:citekey}}

## 输出格式示例
本研究采用实验与理论相结合的方法。如图 1 所示，
{{PLACEHOLDER:figures/zzmx-115.jpg}} 展示了实验装置的整体结构。
根据文献 {{PLACEHOLDER:references:zhang2023deep}} 的研究，
我们在此基础上进行了改进，提出了新的实验方案。

只返回生成的文本，不要其他解释。
"""

        return self.llm.complete(prompt, temperature=0.8)

    def _format_resources_for_prompt(self, resources: List['ResourceInfo']) -> str:
        """格式化资源列表供 AI 使用"""
        lines = []
        for i, r in enumerate(resources, 1):
            lines.append(f"{i}. **{r.filename}** ({r.type})")
            if r.metadata:
                for key, value in r.metadata.items():
                    lines.append(f"   - {key}: {value}")
        return "\n".join(lines)

    def _wrap_with_latex_code(
        self,
        narrative: str,
        resources: List['ResourceInfo'],
        protected_zones: List['ProtectedZone']
    ) -> str:
        """🤝 协作点：AI 叙述 + 硬编码 LaTeX 包装"""

        # 🔧 硬编码：构建 LaTeX 代码映射
        latex_code_map = {}
        for resource in resources:
            if resource.type == "figure":
                latex_code_map[resource.path] = self._generate_figure_latex(resource)
            elif resource.type == "code":
                latex_code_map[resource.path] = self._generate_code_latex(resource)
            elif resource.type == "reference":
                latex_code_map[resource.path] = self._generate_reference_latex(resource)

        # 🔧 硬编码：安全的占位符替换
        result = narrative
        for resource_path, latex_code in latex_code_map.items():
            placeholder = f"{{{{PLACEHOLDER:{resource_path}}}}}"
            result = result.replace(placeholder, latex_code)

        # 🔧 硬编码：验证格式区域未被破坏
        for zone in protected_zones:
            if zone.content not in result:
                from .format_guard import FormatProtectionError
                raise FormatProtectionError(
                    f"保护区域被破坏：{zone.name}\n"
                    f"原内容：{zone.content[:50]}..."
                )

        return result

    def _generate_figure_latex(self, resource: 'ResourceInfo') -> str:
        """硬编码：生成图片 LaTeX 代码"""
        template = self.templates.get("figure_insertion",
            r"""\begin{figure}[htbp]\centering\includegraphics[width=0.8\textwidth]{{{path}}}\caption{{{caption}}}\end{figure}}""")
        caption = resource.metadata.get("caption", "示例图片")
        # 从路径提取文件名作为标签
        label = resource.filename.replace('.', '_')
        return template.format(
            path=resource.path,
            caption=caption,
            label=label
        )

    def _generate_code_latex(self, resource: 'ResourceInfo') -> str:
        """硬编码：生成代码清单 LaTeX 代码"""
        # 读取代码片段
        code_snippet = self._read_code_snippet(resource.path, max_lines=20)

        template = self.templates.get("code_listing",
            r"""\begin{lstlisting}[language={lang}, caption={caption}]
{code}
\end{lstlisting}}""")
        return template.format(
            lang=resource.metadata.get("language", "Python"),
            code=code_snippet,
            caption=f"示例代码：{resource.filename}"
        )

    def _read_code_snippet(self, file_path: str, max_lines: int = 20) -> str:
        """读取代码片段"""
        try:
            # 这里需要确定项目根目录
            # 暂时假设是相对于当前工作目录
            full_path = Path(file_path)
            if not full_path.exists():
                return f"% 文件不存在：{file_path}"

            lines = full_path.read_text(encoding='utf-8').split('\n')
            return '\n'.join(lines[:max_lines])
        except Exception as e:
            return f"% 读取失败：{e}"

    def _generate_reference_latex(self, resource: 'ResourceInfo') -> str:
        """硬编码：生成文献引用 LaTeX 代码"""
        citekey = resource.metadata.get("citekey", "unknown")
        return f"\\cite{{{citekey}}}"

    def _refine_content(
        self,
        content: str,
        theme: 'SectionTheme'
    ) -> str:
        """🧠 AI：自我检查和优化生成的内容"""

        prompt = f"""
你是一位严谨的学术写作评审专家。请检查以下生成的 LaTeX 内容。

## 章节主题
{theme.theme}

## 待检查内容
{content[:2000]}

## 检查项
1. 叙述是否连贯自然？
2. 资源引用是否合理？是否生硬？
3. 是否符合学术写作风格？
4. 有无语法或逻辑问题？
5. LaTeX 代码是否可能破坏格式？

## 输出要求
- 如果发现明显问题，返回优化后的完整内容
- 如果没有重大问题，返回 "OK"
- 如果有轻微问题但不影响整体，返回 "OK" 并在注释中指出

只返回结果，不要解释。
"""

        response = self.llm.complete(prompt, temperature=0.5)

        if response.strip() == "OK":
            return content
        else:
            # AI 返回了优化后的内容
            return response

    def _validate_format_preservation(
        self,
        protected_zones: List['ProtectedZone'],
        new_content: str
    ):
        """硬编码：验证格式区域未被破坏"""
        for zone in protected_zones:
            if zone.content not in new_content:
                from .format_guard import FormatProtectionError
                raise FormatProtectionError(
                    f"格式保护验证失败：{zone.name}\n"
                    f"保护内容：{zone.content[:50]}..."
                )
