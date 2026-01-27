"""
CompleteExampleSkill - 主控制器
AI 增强版示例生成器主控制器
"""

import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import dataclasses


class CompleteExampleSkill:
    """AI 增强版示例生成器主控制器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.skill_root = Path(config.get("skill_root", "skills/complete_example"))
        self.runs_dir = self.skill_root / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 LLM 客户端
        self.llm_client = self._init_llm_client()

        # 加载模板
        self.templates = self._load_templates()

    def _init_llm_client(self):
        """初始化 LLM 客户端"""
        llm_config = self.config.get("llm", {})

        # 默认优先真实 LLM；在缺少依赖/密钥时自动降级到 Mock（便于本地验证与单元测试）。
        try:
            from .llm_client import LLMClient
            return LLMClient(llm_config)
        except Exception:
            class MockLLMClient:
                def complete(self, prompt: str, **kwargs) -> str:
                    # 保守 mock：尽量返回可被后续流程处理的结构
                    if kwargs.get("response_format") == "json":
                        return "{}"
                    return "（Mock LLM）\\n\\n\\subsubsection{示例标题}\\n\\subsubsubsection{示例子标题}\\n这里是示例正文。"

            return MockLLMClient()

    def _load_templates(self) -> Dict[str, str]:
        """加载 LaTeX 模板"""
        generation_config = self.config.get("generation", {})
        templates_config = generation_config.get("templates", {})

        # 如果配置中有模板，使用配置的模板
        if templates_config:
            return templates_config

        # 默认模板
        return {
            "figure_insertion": r"""\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.8\textwidth]{{{path}}}
  \caption{{{caption}}}
  \label{{{label}}}
\end{figure}}""",
            "code_listing": r"""\begin{lstlisting}[language={{lang}}, caption={{{caption}}}, firstline=1, lastline={{lastline}}]
{{code}}
\end{lstlisting}""",
            "reference_citation": r"\cite{{{citekey}}}",
        }

    def _create_run_directory(self) -> Path:
        """🆕 创建新的运行目录"""
        # 生成唯一运行 ID
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        run_dir = self.runs_dir / run_id

        # 创建子目录
        (run_dir / "backups").mkdir(parents=True, exist_ok=True)
        (run_dir / "logs").mkdir(parents=True, exist_ok=True)
        (run_dir / "analysis").mkdir(parents=True, exist_ok=True)
        (run_dir / "output" / "preview").mkdir(parents=True, exist_ok=True)
        (run_dir / "output" / "applied").mkdir(parents=True, exist_ok=True)
        (run_dir / "output" / "report").mkdir(parents=True, exist_ok=True)

        # 更新 latest 软链接
        latest_link = self.runs_dir / "latest"
        if latest_link.exists():
            latest_link.unlink()
        try:
            latest_link.symlink_to(run_id)
        except OSError:
            # Windows 可能需要管理员权限创建软链接
            pass

        # 写入元数据
        metadata = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "config": self.config
        }
        (run_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return run_dir

    def execute(self, project_name: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行完整的示例生成流程

        Args:
            project_name: 项目名称
            options: 选项 {
                content_density: "minimal" | "moderate" | "comprehensive",
                output_mode: "preview" | "apply" | "report",
                target_files: ["1.2.内容目标问题.tex", ...],
                narrative_hint: "用户自定义的叙事提示（可选）"
            }

        Returns:
            Dict: 执行结果报告
        """

        # ========== 阶段 0：初始化 ==========
        # 🆕 创建运行目录（所有输出都放在这里，不污染项目）
        run_dir = self._create_run_directory()

        # 假设项目在 projects/ 目录下
        project_path = Path("projects") / project_name

        report = {
            "project": project_name,
            "run_id": run_dir.name,  # 🆕 记录运行 ID
            "run_dir": str(run_dir),  # 🆕 记录运行目录
            "stages": {},
            "final_result": None
        }

        try:
            # ========== 阶段 1：资源扫描（硬编码） ==========
            report["stages"]["scan"] = self._stage_scan_resources(project_path)

            # ========== 阶段 2：语义分析（AI） ==========
            report["stages"]["analyze"] = self._stage_analyze_sections(
                project_path, options.get("target_files"), run_dir  # 🆕 传递 run_dir
            )

            # ========== 阶段 3：内容生成（AI + 硬编码） ==========
            report["stages"]["generate"] = self._stage_generate_content(
                project_path,
                report["stages"]["scan"]["resources"],
                report["stages"]["analyze"]["themes"],
                options.get("content_density", "moderate"),
                options.get("narrative_hint"),  # 传递用户提示
                run_dir  # 🆕 传递 run_dir
            )

            # ========== 阶段 4：应用变更（硬编码保护 + AI 解释） ==========
            if options.get("output_mode") == "apply":
                report["stages"]["apply"] = self._stage_apply_changes(
                    project_path,
                    report["stages"]["generate"]["contents"],
                    run_dir
                )

            # ========== 阶段 5：质量评估（AI） ==========
            report["stages"]["quality"] = self._stage_evaluate_quality(
                report["stages"]["generate"]["contents"]
            )

            # ========== 阶段 6：生成输出 ==========
            self._stage_generate_output(
                run_dir,
                report,
                options.get("output_mode", "preview")
            )

            report["final_result"] = "success"

        except Exception as e:
            report["final_result"] = "failed"
            report["error"] = str(e)

            # 记录错误到日志
            error_log = run_dir / "logs" / "error.log"
            error_log.write_text(str(e), encoding="utf-8")

        return report

    def _stage_scan_resources(self, project_path: Path) -> Dict:
        """阶段 1：扫描资源"""
        from .resource_scanner import ResourceScanner

        scanner = ResourceScanner(project_path)
        resources = scanner.scan_all()

        return {
            "status": "completed",
            "resources": resources,
            "summary": {
                "figures": len(resources.figures),
                "code": len(resources.code),
                "references": len(resources.references)
            }
        }

    def _stage_analyze_sections(
        self,
        project_path: Path,
        target_files: List[str] = None,
        run_dir: Path = None
    ) -> Dict:
        """阶段 2：分析章节主题"""
        from .semantic_analyzer import SemanticAnalyzer

        analyzer = SemanticAnalyzer(self.llm_client, prompts=self.config.get("prompts", {}))
        themes = {}

        # 默认目标文件
        if target_files is None:
            target_files = [
                "extraTex/1.2.内容目标问题.tex",
                "extraTex/1.4.特色与创新.tex",
                "extraTex/1.5.研究计划.tex"
            ]

        for file_path in target_files:
            full_path = project_path / file_path
            if not full_path.exists():
                continue

            content = full_path.read_text(encoding="utf-8")
            theme = analyzer.analyze_section_theme(content)
            themes[file_path] = theme

        # 🆕 保存分析结果到 runs/<run_id>/analysis/
        if run_dir:
            analysis_file = run_dir / "analysis" / "section_themes.json"
            analysis_file.parent.mkdir(parents=True, exist_ok=True)
            themes_dict = {
                k: {
                    "theme": v.theme,
                    "key_concepts": v.key_concepts,
                    "writing_style": v.writing_style
                }
                for k, v in themes.items()
            }
            analysis_file.write_text(
                json.dumps(themes_dict, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        return {
            "status": "completed",
            "themes": themes
        }

    def _stage_generate_content(
        self,
        project_path: Path,
        resources: 'ResourceReport',
        themes: Dict[str, 'SectionTheme'],
        density: str,
        narrative_hint: str = None,
        run_dir: Path = None
    ) -> Dict:
        """阶段 3：生成内容（使用智能资源分配器）"""
        from .ai_content_generator import AIContentGenerator
        from .format_guard import FormatGuard
        from .resource_allocator import ResourceAllocator, ResourcePool

        # ========== 🆕 阶段 3.1：智能资源分配 ==========
        # 创建资源池
        resource_pool = ResourcePool(
            figures=resources.figures,
            code=resources.code,
            references=resources.references
        )

        # 创建资源分配器（使用配置中的篇幅控制参数）
        allocator_config = self.config.get("page_control", {})
        allocator = ResourceAllocator(allocator_config)

        # 为每个章节分配资源
        allocation_plans, allocation_summary = allocator.allocate_resources_for_project(
            resource_pool=resource_pool,
            section_themes=themes
        )

        # 保存分配方案到 runs/<run_id>/analysis/
        if run_dir:
            allocation_file = run_dir / "analysis" / "resource_allocation.json"
            allocation_file.parent.mkdir(parents=True, exist_ok=True)
            allocation_data = {
                "summary": allocation_summary,
                "plans": [
                    {
                        "file_path": p.file_path,
                        "allocated_resources": [
                            {
                                "path": r.path,
                                "type": r.type,
                                "filename": r.filename
                            }
                            for r in p.allocated_resources
                        ],
                        "target_word_count": p.target_word_count,
                        "estimated_pages": p.estimated_pages
                    }
                    for p in allocation_plans
                ]
            }
            allocation_file.write_text(
                json.dumps(allocation_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        # ========== 阶段 3.2：根据分配方案生成内容 ==========
        generator = AIContentGenerator(
            self.llm_client,
            self.templates,
            FormatGuard(project_path, run_dir),
            config=self.config,
        )

        contents = {}

        # 根据 allocation_plans 逐个生成内容
        for plan in allocation_plans:
            file_path = plan.file_path
            theme = themes[file_path]

            full_path = project_path / file_path
            existing_content = full_path.read_text(encoding="utf-8")

            # 🆕 使用分配的资源而非全局 Top-K
            new_content = generator.generate_section_content_with_allocation(
                allocated_resources=plan.allocated_resources,
                target_word_count=plan.target_word_count,
                section_theme=theme,
                existing_content=existing_content,
                narrative_hint=narrative_hint,
                file_path=file_path,
            )

            contents[file_path] = {
                "old_content": existing_content,
                "new_content": new_content,
                "theme": theme,
                "allocation_plan": plan  # 🆕 记录分配方案
            }

        return {
            "status": "completed",
            "contents": contents
        }

    def _stage_apply_changes(
        self,
        project_path: Path,
        contents: Dict,
        run_dir: Path
    ) -> Dict:
        """阶段 4：应用变更"""
        from .format_guard import FormatGuard

        guard = FormatGuard(project_path, run_dir)
        results = {}

        for file_path, content_data in contents.items():
            try:
                full_path = project_path / file_path
                success = guard.safe_modify_file(
                    file_path=full_path,
                    new_content=content_data["new_content"],
                    ai_explanation=f"根据主题 '{content_data['theme'].theme}' 生成示例内容"
                )
                results[file_path] = {"status": "applied" if success else "failed"}
            except Exception as e:
                results[file_path] = {"status": "failed", "error": str(e)}

        return {
            "status": "completed",
            "results": results
        }

    def _stage_evaluate_quality(self, contents: Dict) -> Dict:
        """阶段 5：质量评估"""
        from .semantic_analyzer import SemanticAnalyzer

        analyzer = SemanticAnalyzer(self.llm_client, prompts=self.config.get("prompts", {}))
        evaluations = {}

        for file_path, content_data in contents.items():
            evaluation = analyzer.evaluate_content_quality(
                content_data["new_content"],
                content_data["theme"]
            )
            evaluations[file_path] = evaluation

        return {
            "status": "completed",
            "evaluations": evaluations
        }

    def _stage_generate_output(
        self,
        run_dir: Path,
        report: Dict,
        output_mode: str
    ):
        """阶段 6：生成输出"""
        def _json_default(obj):
            if dataclasses.is_dataclass(obj):
                return dataclasses.asdict(obj)
            if isinstance(obj, Path):
                return str(obj)
            # Fallback for odd container types
            if isinstance(obj, set):
                return list(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        # 保存完整报告
        report_file = run_dir / "output" / "report" / "report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8"
        )

        # 根据 output_mode 生成不同的输出
        if output_mode == "preview":
            # 生成预览文件
            self._generate_preview_output(run_dir, report)
        elif output_mode == "apply":
            # 生成应用输出
            self._generate_apply_output(run_dir, report)
        elif output_mode == "report":
            # 生成详细报告
            self._generate_report_output(run_dir, report)

    def _generate_preview_output(self, run_dir: Path, report: Dict):
        """生成预览输出"""
        preview_dir = run_dir / "output" / "preview"

        # 为每个文件生成预览
        for file_path, content_data in report["stages"]["generate"]["contents"].items():
            preview_file = preview_dir / f"{file_path.replace('/', '_')}.preview.tex"
            preview_file.parent.mkdir(parents=True, exist_ok=True)
            preview_file.write_text(
                content_data["new_content"],
                encoding="utf-8"
            )

    def _generate_apply_output(self, run_dir: Path, report: Dict):
        """生成应用输出"""
        apply_dir = run_dir / "output" / "applied"

        # 记录已应用的文件
        applied_files = []
        if "apply" in report["stages"]:
            for file_path, result in report["stages"]["apply"]["results"].items():
                if result["status"] == "applied":
                    applied_files.append(file_path)

        applied_log = apply_dir / "applied_files.txt"
        applied_log.write_text("\n".join(applied_files), encoding="utf-8")

    def _generate_report_output(self, run_dir: Path, report: Dict):
        """生成详细报告"""
        report_dir = run_dir / "output" / "report"

        # 生成 Markdown 格式的报告
        md_lines = [
            f"# Complete Example Skill 执行报告",
            f"",
            f"## 基本信息",
            f"- **项目**: {report['project']}",
            f"- **运行 ID**: {report['run_id']}",
            f"- **时间**: {run_dir.name.split('_')[0]}",
            f"",
            f"## 执行结果",
            f"- **状态**: {report['final_result']}",
            f"",
        ]

        # 添加各阶段信息
        for stage_name, stage_data in report.get("stages", {}).items():
            md_lines.append(f"## {stage_name.upper()} 阶段")
            md_lines.append(f"- **状态**: {stage_data.get('status', 'unknown')}")

            # 添加详细信息
            if "summary" in stage_data:
                md_lines.append("- **摘要**:")
                for k, v in stage_data["summary"].items():
                    md_lines.append(f"  - {k}: {v}")

            md_lines.append("")

        # 写入 Markdown 报告
        md_file = report_dir / "report.md"
        md_file.write_text("\n".join(md_lines), encoding="utf-8")
