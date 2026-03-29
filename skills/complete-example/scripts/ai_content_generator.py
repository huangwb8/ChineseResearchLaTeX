"""
AIContentGenerator - AI 增强内容生成器
🧠 AI + 🤝 协作：生成连贯的叙述性文本，智能整合资源
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import re


class AIContentGenerator:
    """AI 驱动的智能内容生成器"""

    def __init__(self, llm_client, templates: dict, format_guard: 'FormatGuard', config: Optional[dict] = None):
        """
        Args:
            llm_client: LLM 客户端
            templates: Jinja2 模板字典
            format_guard: 格式保护器实例
            config: 完整配置（用于 prompts / generation / security 等；可选）
        """
        self.llm = llm_client
        self.templates = templates
        self.guard = format_guard
        self.config = config or {}

    def generate_section_content(
        self,
        resources: List['ResourceInfo'],
        section_theme: 'SectionTheme',
        existing_content: str,
        content_density: str = "moderate",
        narrative_hint: str = None,
        file_path: str = ""
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
            selected_resources,
            section_theme,
            existing_content,
            narrative_hint,
            file_path=file_path,
        )

        # ========== 阶段 4：协作 - 包装 LaTeX 代码 ==========
        formatted_content = self._wrap_with_latex_code(
            narrative, selected_resources, protected_zones, context=existing_content
        )

        # ========== 阶段 5：AI - 自我优化 ==========
        refined_content = self._refine_content(
            formatted_content, section_theme
        )

        # ========== 阶段 6：硬编码 - 最终验证 ==========
        self._validate_format_preservation(protected_zones, refined_content)

        return refined_content

    def generate_section_content_with_allocation(
        self,
        allocated_resources: List['ResourceInfo'],
        target_word_count: int,
        section_theme: 'SectionTheme',
        existing_content: str,
        narrative_hint: str = None,
        file_path: str = ""
    ) -> str:
        """
        🆕 使用预分配的资源生成内容（优化版）

        与 generate_section_content 的区别：
        - 不再使用 Top-K 选择，直接使用预分配的资源
        - 支持自定义目标字数（用于篇幅控制）

        Args:
            allocated_resources: 已分配给该章节的资源列表
            target_word_count: 目标字数
            section_theme: 章节主题
            existing_content: 现有内容
            narrative_hint: 用户叙事提示
            file_path: 文件路径

        Returns:
            str: 生成的内容
        """
        # ========== 阶段 1：硬编码 - 提取保护区域 ==========
        protected_zones = self.guard.extract_protected_zones(existing_content)

        # ========== 阶段 2：AI - 生成叙述性内容（使用预分配资源） ==========
        narrative = self._generate_narrative_with_target(
            resources=allocated_resources,
            theme=section_theme,
            context=existing_content,
            narrative_hint=narrative_hint,
            target_word_count=target_word_count,
            file_path=file_path,
        )

        # ========== 阶段 3：协作 - 包装 LaTeX 代码 ==========
        formatted_content = self._wrap_with_latex_code(
            narrative, allocated_resources, protected_zones, context=existing_content
        )

        # ========== 阶段 4：AI - 自我优化 ==========
        refined_content = self._refine_content(
            formatted_content, section_theme
        )

        # ========== 阶段 5：硬编码 - 最终验证 ==========
        self._validate_format_preservation(protected_zones, refined_content)

        return refined_content

    def _generate_narrative_with_target(
        self,
        resources: List['ResourceInfo'],
        theme: 'SectionTheme',
        context: str,
        narrative_hint: str = None,
        target_word_count: int = 300,
        file_path: str = ""
    ) -> str:
        """🆕 AI：生成指定字数的连贯叙述性文本"""

        prompts = (self.config.get("prompts") or {})
        tmpl = prompts.get("generate_narrative")

        # 推断文件类型
        file_type = "main" if (file_path and file_path.endswith("main.tex")) else "input"

        if tmpl:
            prompt = tmpl.format(
                theme=theme.theme,
                key_concepts=", ".join(theme.key_concepts),
                writing_style=theme.writing_style,
                target_audience=theme.target_audience,
                narrative_hint=narrative_hint or "（未提供，AI 根据章节主题自动推断）",
                context=context[:800],
                resources=self._format_resources_for_prompt(resources),
                target_length=str(target_word_count),  # 🆕 使用目标字数
                file_type=file_type,
            )
        else:
            # 兼容旧逻辑
            prompt = (
                "你是一位经验丰富的科研写作助手，专精于国家自然科学基金申请书的撰写。\n"
                "根据以下信息，生成一段连贯的示例内容。\n\n"
                f"主题：{theme.theme}\n"
                f"关键概念：{', '.join(theme.key_concepts)}\n"
                f"写作风格：{theme.writing_style}\n"
                f"目标读者：{theme.target_audience}\n"
                f"目标字数：约 {target_word_count} 字\n"  # 🆕 明确字数要求
                f"用户叙事提示：{narrative_hint or '（未提供）'}\n\n"
                f"可用资源：\n{self._format_resources_for_prompt(resources)}\n\n"
                "请在应插入 LaTeX 代码处使用双大括号占位符，例如：\n"
                "- 图片：{{{{PLACEHOLDER:figures/xxx.jpg}}}}\n"
                "- 文献：{{{{PLACEHOLDER:references:zhang2023deep}}}}\n"
                "- 表格：{{{{TABLE:临床特征对比表|complex}}}}\n"
                "- 公式：{{{{EQUATION:E=mc^2|eq:energy}}}}\n\n"
                "只返回生成的文本，不要解释。\n"
            )

        temp = 0.8
        llm_temp_cfg = (self.config.get("llm") or {}).get("temperature")
        if isinstance(llm_temp_cfg, dict):
            temp = float(llm_temp_cfg.get("generation", temp))

        return self.llm.complete(prompt, temperature=temp)

    def _generate_narrative(
        self,
        resources: List['ResourceInfo'],
        theme: 'SectionTheme',
        context: str,
        narrative_hint: str = None,
        file_path: str = ""
    ) -> str:
        """AI：生成连贯的叙述性文本"""

        prompts = (self.config.get("prompts") or {})
        tmpl = prompts.get("generate_narrative")

        # 推断文件类型（用于提示约束）
        file_type = "main" if (file_path and file_path.endswith("main.tex")) else "input"

        if tmpl:
            prompt = tmpl.format(
                theme=theme.theme,
                key_concepts=", ".join(theme.key_concepts),
                writing_style=theme.writing_style,
                target_audience=theme.target_audience,
                narrative_hint=narrative_hint or "（未提供，AI 根据章节主题自动推断）",
                context=context[:800],
                resources=self._format_resources_for_prompt(resources),
                target_length="200-400",
                file_type=file_type,
            )
        else:
            # 兼容旧逻辑：最小提示（但注意要让 AI 输出双大括号占位符）
            prompt = (
                "你是一位经验丰富的科研写作助手，专精于国家自然科学基金申请书的撰写。\n"
                "根据以下信息，生成一段连贯的示例内容。\n\n"
                f"主题：{theme.theme}\n"
                f"关键概念：{', '.join(theme.key_concepts)}\n"
                f"写作风格：{theme.writing_style}\n"
                f"目标读者：{theme.target_audience}\n\n"
                f"用户叙事提示：{narrative_hint or '（未提供）'}\n\n"
                "请在应插入 LaTeX 代码处使用双大括号占位符，例如：\n"
                "- 图片：{{{{PLACEHOLDER:figures/xxx.jpg}}}}\n"
                "- 文献：{{{{PLACEHOLDER:references:zhang2023deep}}}}\n"
                "- 表格：{{{{TABLE:临床特征对比表|complex}}}}\n"
                "- 公式：{{{{EQUATION:E=mc^2|eq:energy}}}}\n\n"
                "只返回生成的文本，不要解释。\n"
            )

        temp = 0.8
        llm_temp_cfg = (self.config.get("llm") or {}).get("temperature")
        if isinstance(llm_temp_cfg, dict):
            temp = float(llm_temp_cfg.get("generation", temp))

        return self.llm.complete(prompt, temperature=temp)

    def _format_resources_for_prompt(self, resources: List['ResourceInfo']) -> str:
        """格式化资源列表供 AI 使用"""
        lines = []
        for i, r in enumerate(resources, 1):
            lines.append(f"{i}. **{r.filename}** ({r.type})")
            # 明确告诉 AI 应该输出什么占位符 ID，避免“写对了资源但占位符写错”导致替换失败。
            lines.append(f"   - placeholder_id: {self._resource_placeholder_id(r)}")
            if r.metadata:
                for key, value in r.metadata.items():
                    lines.append(f"   - {key}: {value}")
        return "\n".join(lines)

    def _wrap_with_latex_code(
        self,
        narrative: str,
        resources: List['ResourceInfo'],
        protected_zones: List['ProtectedZone'],
        context: str = ""
    ) -> str:
        """🤝 协作点：AI 叙述 + 硬编码 LaTeX 包装"""

        from .placeholder_parser import iter_placeholders, replace_spans
        from .table_generator import TableGenerator
        from .formula_generator import FormulaGenerator

        # 🔧 硬编码：构建资源占位符 -> LaTeX 代码映射
        latex_code_map: Dict[str, str] = {}
        for resource in resources:
            placeholder_id = self._resource_placeholder_id(resource)
            if resource.type == "figure":
                latex_code_map[placeholder_id] = self._generate_figure_latex(resource)
            elif resource.type == "code":
                latex_code_map[placeholder_id] = self._generate_code_latex(resource)
            elif resource.type == "reference":
                latex_code_map[placeholder_id] = self._generate_reference_latex(resource)

        # 🔧 硬编码：先替换资源占位符（支持 references:citekey 这种“虚拟路径”）
        result = narrative
        replacements: list[tuple[int, int, str]] = []
        for ph in iter_placeholders(result):
            if ph.kind != "resource" or not ph.resource_id:
                continue
            rep = latex_code_map.get(ph.resource_id)
            if rep is not None:
                replacements.append((ph.start, ph.end, rep))
        result = replace_spans(result, replacements)

        # 🔧 硬编码：再替换表格/公式占位符
        table_gen = TableGenerator(self.llm, self.config, self.templates)
        formula_gen = FormulaGenerator(self.templates)

        forbidden_table = ((self.config.get("security") or {}).get("table_security") or {}).get("forbidden_commands") or []
        forbidden_formula = ((self.config.get("security") or {}).get("formula_security") or {}).get("forbidden_commands") or []

        replacements = []
        for ph in iter_placeholders(result):
            if ph.kind == "table" and ph.description and ph.complexity:
                latex = table_gen.generate(ph.description, ph.complexity, context=context)
                latex = self._sanitize_generated_block(latex, forbidden_table)
                replacements.append((ph.start, ph.end, latex))
            elif ph.kind == "inline_math" and ph.formula:
                latex = formula_gen.inline(ph.formula)
                latex = self._sanitize_generated_block(latex, forbidden_formula)
                replacements.append((ph.start, ph.end, latex))
            elif ph.kind == "display_math" and ph.formula:
                latex = formula_gen.display(ph.formula)
                latex = self._sanitize_generated_block(latex, forbidden_formula)
                replacements.append((ph.start, ph.end, latex))
            elif ph.kind == "equation" and ph.formula and ph.label is not None:
                latex = formula_gen.equation(ph.formula, ph.label)
                latex = self._sanitize_generated_block(latex, forbidden_formula)
                replacements.append((ph.start, ph.end, latex))
            elif ph.kind == "align" and ph.formula:
                latex = formula_gen.align(ph.formula)
                latex = self._sanitize_generated_block(latex, forbidden_formula)
                replacements.append((ph.start, ph.end, latex))
        result = replace_spans(result, replacements)

        # 🔧 硬编码：验证格式区域未被破坏
        for zone in protected_zones:
            if zone.content not in result:
                from .format_guard import FormatProtectionError
                raise FormatProtectionError(
                    f"保护区域被破坏：{zone.name}\n"
                    f"原内容：{zone.content[:50]}..."
                )

        return result

    def _sanitize_generated_block(self, latex: str, forbidden_commands: List[str]) -> str:
        """对生成的 LaTeX 片段做最小化安全过滤（不做全局清理）。"""
        if not forbidden_commands:
            return latex
        sanitized_lines = []
        for line in latex.splitlines():
            if any(cmd in line for cmd in forbidden_commands):
                sanitized_lines.append(f"% 🚨 已自动移除不安全命令：{line}")
            else:
                sanitized_lines.append(line)
        return "\n".join(sanitized_lines)

    def _resource_placeholder_id(self, resource: 'ResourceInfo') -> str:
        """
        资源占位符的唯一 ID。
        - figure/code: 使用相对路径（figures/... / code/...)
        - reference: 使用 references:<citekey>（避免同一 .bib 下多个条目冲突）
        """
        if resource.type == "reference":
            citekey = (resource.metadata or {}).get("citekey") or resource.filename
            return f"references:{citekey}"
        return resource.path

    def _generate_figure_latex(self, resource: 'ResourceInfo') -> str:
        """硬编码：生成图片 LaTeX 代码"""
        from .template_renderer import render_template
        template = self.templates.get("figure_insertion",
            r"""\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.8\textwidth]{{{path}}}
  \caption{{{caption}}}
  \label{{{label}}}
\end{figure}""")
        caption = resource.metadata.get("caption", "示例图片")
        # 从路径提取文件名作为标签
        label = resource.filename.replace('.', '_')
        return render_template(template, {"path": resource.path, "caption": caption, "label": label})

    def _generate_code_latex(self, resource: 'ResourceInfo') -> str:
        """硬编码：生成代码清单 LaTeX 代码"""
        # 读取代码片段
        code_snippet = self._read_code_snippet(resource.path, max_lines=20)
        lastline = max(1, len(code_snippet.splitlines()))

        from .template_renderer import render_template
        template = self.templates.get("code_listing",
            r"""\begin{lstlisting}[language={{lang}}, caption={{{caption}}}, firstline=1, lastline={{lastline}}]
{{code}}
\end{lstlisting}""")
        return render_template(template, {
            "lang": resource.metadata.get("language", "Python"),
            "code": code_snippet,
            "caption": f"示例代码：{resource.filename}",
            "lastline": lastline,
        })

    def _read_code_snippet(self, file_path: str, max_lines: int = 20) -> str:
        """读取代码片段"""
        try:
            # resource.path 是相对于 project_path 的路径
            base = getattr(self.guard, "project_path", Path("."))
            full_path = Path(base) / file_path
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
