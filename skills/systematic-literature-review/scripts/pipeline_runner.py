#!/usr/bin/env python3
"""
pipeline_runner.py - 相关性驱动的系统综述 Pipeline Runner

阶段：
  0_setup  →  1_search  →  2_dedupe  →  3_score  →  4_select  →  5_write  →  6_validate  →  7_export

目标：保持输出形态不变（LaTeX + BibTeX → PDF/Word），去除质量/证据硬阈值，只保留字数/参考数与章节/引用一致性检查。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import io

import yaml


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class PipelineState:
    version: str = "2.0"
    topic: str = ""
    domain: str = "general"
    started_at: str = ""
    current_stage: str = ""
    completed_stages: List[str] = field(default_factory=list)
    input_files: Dict[str, str] = field(default_factory=dict)
    output_files: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_json(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def from_json(cls, path: Path) -> "PipelineState":
        return cls(**json.loads(path.read_text(encoding="utf-8")))


# ============================================================================
# Runner
# ============================================================================

class PipelineRunner:
    # 工作条件骨架标题定义（与 validate_working_conditions.py 共享）
    # 这些定义是工作条件文件验证的单一真相来源
    WORKING_CONDITIONS_HEADINGS = {
        "search_plan": "Search Plan",
        "search_log": "Search Log",
        "dedup": "Dedup",
        "scoring_selection": "Relevance Scoring & Selection",
        "review_structure": "Review Structure",
        "data_extraction": "Data Extraction Table（数据抽取表）",
        "validation": "Validation",
    }

    WORKING_CONDITIONS_REQUIRED_H2_KEYS = [
        "search_plan",
        "search_log",
        "dedup",
        "scoring_selection",
        "review_structure",
        "data_extraction",
        "validation",
    ]

    WORKING_CONDITIONS_REQUIRED_H3_KEYS: list[str] = []  # 当前无必需 H3 章节

    WORKING_CONDITIONS_REQUIRED_KEYWORDS = [
        "Search Plan",
        "Search Log",
        "Dedup",
        "Relevance Scoring & Selection",
        "Review Structure",
        "Data Extraction",
        "Validation",
        "评分分布",  # 评分分布异常检测关键词
        "高分优先",
    ]

    STAGES = {
        "0_setup": "初始化与参数收集",
        "1_search": "文献检索",
        "2_dedupe": "去重",
        "3_score": "相关性评分与子主题分组",
        "4_select": "选文与生成 Bib",
        "4.5_word_budget": "生成综/述字数预算",
        "5_write": "写作准备（工作条件与正文骨架）",
        "6_validate": "校验（字数/引用/章节/引用一致性）",
        "7_export": "导出 PDF/Word",
    }

    def __init__(
        self,
        topic: str,
        domain: str,
        config_path: Path,
        work_dir: Path,
        review_level: Optional[str],
        output_stem: Optional[str],
    ):
        self.topic = topic
        self.domain = domain
        # 统一使用绝对路径：避免在子进程 cwd=self.work_dir 时把路径“拼两遍”，同时减少跨 run 污染风险。
        self.work_dir = work_dir.expanduser().resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        # 设置工作目录隔离范围：子进程默认只允许在该目录内读写（由各脚本从 env 读取并校验）。
        os.environ["SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT"] = str(self.work_dir)

        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.review_level = self._resolve_review_level(review_level)
        self.file_stem = self._sanitize_topic_for_filename(output_stem or topic)

        scoring_cfg = self.config.get("scoring", {}) if isinstance(self.config, dict) else {}
        word_range = (scoring_cfg.get("default_word_range") or {}).get(self.review_level, {}) if isinstance(scoring_cfg, dict) else {}
        ref_range = (scoring_cfg.get("default_ref_range") or {}).get(self.review_level, {}) if isinstance(scoring_cfg, dict) else {}
        self.target_words = {"min": int(word_range.get("min", 0) or 0), "max": int(word_range.get("max", 0) or 0)}
        self.target_refs = {"min": int(ref_range.get("min", 0) or 0), "max": int(ref_range.get("max", 0) or 0)}

        high_score = scoring_cfg.get("high_score_priority") or {}
        self.high_score_fraction_min = float(high_score.get("fraction_min", 0.6))
        self.high_score_fraction_max = float(high_score.get("fraction_max", 0.8))

        validation_cfg = self.config.get("validation", {}) if isinstance(self.config, dict) else {}
        words_cfg = validation_cfg.get("words", {}) if isinstance(validation_cfg, dict) else {}
        refs_cfg = validation_cfg.get("references", {}) if isinstance(validation_cfg, dict) else {}
        self.validation_words = {
            "min": int((words_cfg.get("min") or {}).get(self.review_level, 0) or 0),
            "max": int((words_cfg.get("max") or {}).get(self.review_level, 0) or 0),
        }
        self.validation_refs = {
            "min": int((refs_cfg.get("min") or {}).get(self.review_level, 0) or 0),
            "max": int((refs_cfg.get("max") or {}).get(self.review_level, 0) or 0),
        }

        layout = self.config.get("layout", {}) if isinstance(self.config, dict) else {}
        self.hidden_dir = self.work_dir / layout.get("hidden_dir_name", ".systematic-literature-review")
        self.artifacts_dir = self.hidden_dir / layout.get("artifacts_dir_name", "artifacts")
        self.reference_dir = self.hidden_dir / layout.get("reference_dir_name", "reference")
        self.data_extraction_table = self.reference_dir / layout.get("reference_data_extraction_name", "data_extraction_table.md")

        # 缓存策略（默认关闭，避免 run 目录 cache/api 文件爆炸）
        cache_cfg = self.config.get("cache", {}) if isinstance(self.config, dict) else {}
        api_cache_cfg = cache_cfg.get("api", {}) if isinstance(cache_cfg.get("api", {}), dict) else {}
        self.cache_enabled = bool(api_cache_cfg.get("enabled", False))
        self.cache_ttl_seconds = int(api_cache_cfg.get("ttl_seconds", 86400) or 86400)
        self.cache_dir: Optional[Path] = None
        if self.cache_enabled:
            self.cache_dir = self.hidden_dir / layout.get("cache_dir_name", "cache") / "api"

        for d in [self.hidden_dir, self.artifacts_dir, self.reference_dir]:
            d.mkdir(parents=True, exist_ok=True)
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            # 设置缓存目录环境变量（供 api_cache.py 使用）
            os.environ["SYSTEMATIC_LITERATURE_REVIEW_CACHE_DIR"] = str(self.cache_dir)

        word_budget_cfg = (self.config.get("word_budget") or {}) if isinstance(self.config, dict) else {}
        outputs_cfg = word_budget_cfg.get("outputs", {}) if isinstance(word_budget_cfg, dict) else {}
        self.word_budget_run_pattern = outputs_cfg.get("run_pattern", "word_budget_run{n}.csv")
        self.word_budget_final = outputs_cfg.get("final", "word_budget_final.csv")
        self.word_budget_non_cited = outputs_cfg.get("non_cited", "non_cited_budget.csv")


        output_cfg = self.config.get("output", {}) if isinstance(self.config, dict) else {}
        self.output_templates = output_cfg

        self.state = PipelineState(
            topic=self.topic,
            domain=self.domain,
            started_at=datetime.now().isoformat(),
            config=self.config,
        )
        self.state.metrics["review_level"] = self.review_level
        self.state.metrics["target_words"] = self.target_words
        self.state.metrics["target_refs"] = self.target_refs
        self.state.metrics["work_dir"] = str(self.work_dir)
        self.state.metrics["cache_enabled"] = bool(self.cache_enabled)

    # ---------------- internal helpers ---------------- #
    @staticmethod
    def _sanitize_topic_for_filename(raw: str) -> str:
        s = re.sub(r"[\\/\\:*?\"<>|]+", "", raw.strip())
        s = re.sub(r"\\s+", "-", s)
        return s[:80] or "topic"

    def _load_config(self, path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _resolve_review_level(self, override: Optional[str]) -> str:
        if override:
            return override
        review_cfg = self.config.get("review_levels", {}) if isinstance(self.config, dict) else {}
        return str(review_cfg.get("default", "premium"))

    def _state_file(self) -> Path:
        return self.hidden_dir / "pipeline_state.json"

    def save_state(self) -> None:
        self.state.to_json(self._state_file())

    def _run_script(self, script_name: str, args: List[str]) -> bool:
        script_path = Path(__file__).parent / script_name
        cmd = [sys.executable, str(script_path)] + args
        # 固定 cwd 到 work_dir：避免相对路径输出散落到启动目录，影响 resume 与产物隔离
        proc = subprocess.run(cmd, cwd=self.work_dir)
        if proc.returncode == 0:
            return True
        print(
            f"✗ 运行脚本失败（exit={proc.returncode}）: {' '.join(cmd)} (cwd={self.work_dir})",
            file=sys.stderr,
        )
        return False

    def _run_script_capture_output(self, script_name: str, args: List[str]) -> tuple[bool, str]:
        """运行脚本并捕获 stdout 输出，返回 (成功状态, 输出文本)"""
        script_path = Path(__file__).parent / script_name
        cmd = [sys.executable, str(script_path)] + args
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=self.work_dir)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            stdout = e.stdout or ""
            stderr = e.stderr or ""
            combined = stdout + ("\n" if stdout and stderr else "") + stderr
            print(
                f"✗ 运行脚本失败（exit={e.returncode}）: {' '.join(cmd)} (cwd={self.work_dir})",
                file=sys.stderr,
            )
            return False, combined

    def _output_path(self, key: str) -> Path:
        tpl = self.output_templates.get(key, f"{self.file_stem}_{key}.txt")
        return self.work_dir / tpl.format(topic=self.file_stem)

    def _write_working_conditions_skeleton(self, path: Path) -> None:
        if path.exists():
            return
        sections = [
            "# 工作条件",
            f"- 主题: {self.topic}",
            f"- 档位: {self.review_level}",
            f"- 目标字数: {self.target_words['min']}–{self.target_words['max']}（可覆盖）",
            f"- 目标参考文献: {self.target_refs['min']}–{self.target_refs['max']}（可覆盖）",
            f"- 最高原则: 不可偷懒/短视，需说明不确定性处理。",
            "",
            "## ⚠️ 内容分离原则（防止 AI 流程泄露）",
            "",
            "**重要**：本文件用于记录 AI 工作流程和方法学信息。",
            "综述正文（{主题}_review.tex）必须完全聚焦领域知识，不应出现任何以下内容：",
            "- ❌ '本综述基于 X 条初检文献、去重后 Y 条、最终保留 Z 篇'",
            "- ❌ '方法学上，本综述按照检索→去重→评分→选文→写作的管线执行'",
            "- ❌ 任何提及'检索'、'去重'、'相关性评分'、'选文'、'字数预算'等元操作的描述",
            "",
            "这些方法学信息应记录在本文件的相应章节（Search Log、Relevance Scoring & Selection 等），",
            "而**不是**放在综述正文中。目标是让读者感受不到这是 AI 生成的综述。",
            "",
            "---",
            "",
            "## Search Plan",
            "- 查询/来源/时间范围/语言",
            "## Search Log",
            "- 实际检索记录与结果量（包括初检文献数、去重后数量）",
            "## Dedup",
            "- 去重策略与 dedupe_map 路径",
            "## Relevance Scoring & Selection",
            "- 评分方法、高分优先比例、选文结果与理由",
            "- **评分分布（高/中/低分段文献数量）**",
            "- **⚠️ 评分分布异常警告（如适用）**：",
            "  - 如果所有文献评分均为 1.0（保底评分），说明评分机制失效",
            "  - 可能原因：中文主题导致脚本评分无法提取有效 token（v3.6 及更早版本）",
            "  - 建议：使用 AI 评分（v3.7+）或将主题转为英文",
            "- 评分文件路径：`.systematic-literature-review/artifacts/scored_papers_{主题}.jsonl`",
            "## Data Extraction Table（数据抽取表）",
            "- 数据抽取表路径：`.systematic-literature-review/reference/data_extraction_table.md`",
            "- 包含每篇文献的 Score、Subtopic、DOI、Year、Title、Venue、Design、Key findings、Limitations",
            "## Review Structure",
            "- 子主题列表与写作提纲",
            "## Validation",
            "- 字数/参考数/必需章节/引用一致性检查结果",
        ]
        path.write_text("\n".join(sections) + "\n", encoding="utf-8")

    # ---------------- stages ---------------- #
    def run_stage_0_setup(self) -> bool:
        wc = self._output_path("working_conditions")
        self.state.output_files["working_conditions"] = str(wc)
        self._write_working_conditions_skeleton(wc)
        self.state.completed_stages.append("0_setup")
        self.save_state()
        return True

    def run_stage_1_search(self) -> bool:
        print("\n[阶段1] 多查询文献检索")
        papers = Path(self.state.input_files.get("papers", "")) if self.state.input_files else Path()
        if papers.exists() and papers.is_file() and papers.suffix.lower() == ".jsonl":
            print(f"  已存在候选库: {papers}")
            self.state.completed_stages.append("1_search")
            self.save_state()
            return True
        if "papers" in (self.state.input_files or {}) and (
            papers == Path(".") or not papers.exists() or not papers.is_file() or papers.suffix.lower() != ".jsonl"
        ):
            # 状态恢复时的脏路径，清理后重新检索
            print(f"  ⚠️ 无效的 papers 路径已忽略: {papers}")
            self.state.input_files.pop("papers", None)
            self.save_state()

        search_cfg = self.config.get("search", {}) if isinstance(self.config, dict) else {}
        max_results_per_query = int(search_cfg.get("max_results_per_query", 50))
        max_total = int(search_cfg.get("max_total_results", 500))
        output_file = self.artifacts_dir / f"papers_{self.file_stem}.jsonl"
        search_log = self.artifacts_dir / f"search_log_{self.file_stem}.json"

        # 检查是否存在 AI 生成的查询文件
        queries_file = self.artifacts_dir / f"queries_{self.file_stem}.json"

        if queries_file.exists():
            # 使用 AI 生成的多查询检索
            print(f"  使用 AI 生成的查询: {queries_file}")
            cache_args: list[str] = []
            if self.cache_dir is not None:
                cache_args = ["--cache-dir", str(self.cache_dir)]
            ok = self._run_script(
                "multi_query_search.py",
                [
                    "--queries", str(queries_file),
                    "--output", str(output_file),
                    "--search-log", str(search_log),
                    "--max-results-per-query", str(max_results_per_query),
                    "--max-total", str(max_total),
                    *cache_args,
                ],
            )
        else:
            # 降级方案：单一查询检索
            print(f"  ⚠️ 未找到查询文件，使用单一查询检索（降级方案）")
            print(f"  提示：可以让 AI 生成多查询以提升检索覆盖面")
            cache_args: list[str] = []
            if self.cache_dir is not None:
                cache_args = ["--cache-dir", str(self.cache_dir)]
            ok = self._run_script(
                "openalex_search.py",
                [
                    "--query", self.topic,
                    "--output", str(output_file),
                    "--max-results", str(max_total),
                    *cache_args,
                ],
            )

        if ok and output_file.exists():
            self.state.input_files["papers"] = str(output_file)
            self.state.output_files["search_log"] = str(search_log) if search_log.exists() else ""
            self.state.completed_stages.append("1_search")
            self.save_state()
            return True

        print("  ✗ 检索失败：请手动生成 papers.jsonl 后重试。")
        return False

    def run_stage_2_dedupe(self) -> bool:
        print("\n[阶段2] 去重")
        papers = Path(self.state.input_files.get("papers", ""))
        if not papers.exists():
            print("  ✗ 缺少 papers.jsonl")
            return False
        deduped = self.artifacts_dir / f"papers_deduped_{self.file_stem}.jsonl"
        dedupe_map = Path(self.output_templates.get("dedupe_map", "dedupe_map_{topic}.json").format(topic=self.file_stem))
        dedupe_map = self.artifacts_dir / dedupe_map.name
        dedupe_cfg = self.config.get("dedupe", {}) if isinstance(self.config, dict) else {}
        args = [
            "--input",
            str(papers),
            "--output",
            str(deduped),
            "--map",
            str(dedupe_map),
            "--title-sim",
            str(dedupe_cfg.get("title_similarity_threshold", 0.92)),
            "--token-jaccard",
            str(dedupe_cfg.get("token_jaccard_threshold", 0.80)),
            "--year-window",
            str(dedupe_cfg.get("year_window", 1)),
        ]
        ok = self._run_script("dedupe_papers.py", args)
        if ok and deduped.exists():
            self.state.input_files["papers_deduped"] = str(deduped)
            self.state.output_files["dedupe_map"] = str(dedupe_map)
            self.state.completed_stages.append("2_dedupe")
            self.save_state()
            return True
        print("  ✗ 去重失败")
        return False

    def run_stage_3_score(self) -> bool:
        """
        [阶段3] AI 自主评分与子主题分组 + 数据抽取（一次完成）

        评分方法：
        - AI 直接评分（唯一方法）：使用 references/ai_scoring_prompt.md 进行语义理解评分

        AI 评分优势：
        - 语义理解：基于任务/方法/模态/应用价值四个维度综合评分
        - 多语言支持：中文/英文主题都能理解
        - 数据抽取：同步提取 design/key_findings/limitations 字段

        注意：此阶段需要通过 Skill 交互模式完成，Pipeline 不支持自动评分。
        """
        print("\n[阶段3] AI 自主评分与子主题分组 + 数据抽取")

        # 读取 AI 评分 Prompt 模板
        ai_prompt_path = Path(__file__).parent.parent / "references" / "ai_scoring_prompt.md"

        print(f"  AI 评分 Prompt: {ai_prompt_path}")
        print(f"  ⚠️  此阶段需要通过 Skill 交互模式完成")
        print(f"  ℹ️  请使用 Skill 的阶段3，AI 会根据 ai_scoring_prompt.md 自动评分")
        print(f"  ℹ️  评分完成后，请将结果保存为 scored_papers_{self.file_stem}.jsonl")
        print(f"  ℹ️  然后使用 --resume-from 4 继续后续阶段")
        print(
            f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║ ⚠️  工作目录隔离警告（防止跨 run 污染）                                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║ 本阶段评分只应读取以下文件：                                                  ║
║   - {self.artifacts_dir / f'papers_deduped_{self.file_stem}.jsonl'}           ║
║                                                                              ║
║ ⛔ 禁止读取：                                                                  ║
║   - 其他 run 目录的文件                                                       ║
║   - 本 work_dir 外的任意路径                                                  ║
║                                                                              ║
║ 评分结果必须保存到：                                                          ║
║   - {self.artifacts_dir / f'scored_papers_{self.file_stem}.jsonl'}            ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
        )

        # 检查是否已存在评分文件
        scored = self.artifacts_dir / f"scored_papers_{self.file_stem}.jsonl"
        if scored.exists():
            print(f"  ✓ 发现已存在的评分文件: {scored}")
            self.state.input_files["scored_papers"] = str(scored)
            self.state.completed_stages.append("3_score")
            self.save_state()
            return True

        print(f"  ✗ 未找到评分文件，请先完成 AI 评分")
        return False

    def run_stage_4_select(self) -> bool:
        print("\n[阶段4] 选文与生成 Bib")
        scored = Path(self.state.input_files.get("scored_papers", ""))
        if not scored.exists():
            print("  ✗ 缺少评分文件")
            return False
        selected = self.artifacts_dir / f"selected_papers_{self.file_stem}.jsonl"
        bib_path = self._output_path("references_bib")
        selection_yaml = self.artifacts_dir / f"selection_rationale_{self.file_stem}.yaml"
        args = [
            "--input",
            str(scored),
            "--output",
            str(selected),
            "--bib",
            str(bib_path),
            "--selection",
            str(selection_yaml),
            "--min-refs",
            str(self.target_refs["min"]),
            "--max-refs",
            str(self.target_refs["max"]),
            "--high-score-min",
            str(self.high_score_fraction_min),
            "--high-score-max",
            str(self.high_score_fraction_max),
        ]
        ok = self._run_script("select_references.py", args)
        if ok and selected.exists() and bib_path.exists():
            self.state.input_files["selected_papers"] = str(selected)
            self.state.output_files["references_bib"] = str(bib_path)
            self.state.output_files["selection_rationale"] = str(selection_yaml)
            self.state.metrics["reference_count"] = sum(1 for _ in open(selected, encoding="utf-8"))
            self.state.completed_stages.append("4_select")
            self.save_state()
            return True
        print("  ✗ 选文或生成 Bib 失败")
        return False

    def run_stage_4_5_word_budget(self) -> bool:
        print("\n[阶段4.5] 生成综/述字数预算")
        selected = Path(self.state.input_files.get("selected_papers", ""))
        if not selected.exists():
            print("  ✗ 缺少 selected_papers.jsonl")
            return False
        budget_run_paths = []
        for i in range(1, 4):
            budget_run_paths.append(self.artifacts_dir / self.word_budget_run_pattern.format(n=i))
        budget_final_path = self.artifacts_dir / self.word_budget_final
        budget_non_cited = self.artifacts_dir / self.word_budget_non_cited

        args = [
            "--selected",
            str(selected),
            "--config",
            str(self.config_path),
            "--output-dir",
            str(self.artifacts_dir),
        ]
        # 传递目标字数中点
        midpoint = 0
        if self.target_words["min"] and self.target_words["max"]:
            midpoint = (self.target_words["min"] + self.target_words["max"]) / 2
        if midpoint:
            args.extend(["--target-words", str(midpoint)])

        ok = self._run_script("plan_word_budget.py", args)
        if ok and budget_final_path.exists():
            self.state.output_files["word_budget_runs"] = [str(p) for p in budget_run_paths if p.exists()]
            self.state.output_files["word_budget_final"] = str(budget_final_path)
            if budget_non_cited.exists():
                self.state.output_files["word_budget_non_cited"] = str(budget_non_cited)
            self.state.completed_stages.append("4.5_word_budget")
            self.save_state()
            return True
        print("  ✗ 生成字数预算失败")
        return False

    def run_stage_5_write(self) -> bool:
        print("\n[阶段5] 写作准备")
        wc = self._output_path("working_conditions")
        review_tex = self._output_path("review_tex")
        references_bib = Path(self.state.output_files.get("references_bib", self._output_path("references_bib")))
        self.state.output_files["working_conditions"] = str(wc)
        self.state.output_files["review_tex"] = str(review_tex)
        self._write_working_conditions_skeleton(wc)

        # 记录字数预算
        if "word_budget_final" in self.state.output_files:
            print(f"  字数预算: {self.state.output_files['word_budget_final']}")
            self.state.output_files.setdefault("notes", {})
            if isinstance(self.state.output_files["notes"], dict):
                self.state.output_files["notes"]["word_budget"] = self.state.output_files["word_budget_final"]

        # 数据抽取表（写入隐藏目录，含 score/subtopic）
        selected = Path(self.state.input_files.get("selected_papers", ""))
        if selected.exists():
            # 选文后摘要补齐（默认 post_selection）：只对 selected_papers 做补齐，避免检索阶段对候选库全局补齐导致慢与 cache/api 膨胀
            search_cfg = self.config.get("search", {}) if isinstance(self.config, dict) else {}
            ae = (search_cfg.get("abstract_enrichment") or {}) if isinstance(search_cfg.get("abstract_enrichment"), dict) else {}
            ae_enabled = bool(ae.get("enabled", False))
            ae_stage = str(ae.get("stage", "search")).strip().lower()
            if ae_enabled and ae_stage == "post_selection":
                enriched = self.artifacts_dir / f"selected_papers_enriched_{self.file_stem}.jsonl"
                if enriched.exists():
                    selected = enriched
                    self.state.input_files["selected_papers"] = str(enriched)
                else:
                    timeout_seconds = int(ae.get("timeout_seconds", 5) or 5)
                    enrich_args = [
                        "--input", str(selected),
                        "--output", str(enriched),
                        "--topic", self.topic,
                        "--timeout", str(timeout_seconds),
                    ]
                    if self.cache_dir is not None:
                        enrich_args.extend(
                            ["--cache-dir", str(self.cache_dir), "--cache-ttl-seconds", str(self.cache_ttl_seconds)]
                        )
                    ok = self._run_script("multi_source_abstract.py", enrich_args)
                    if ok and enriched.exists():
                        selected = enriched
                        self.state.input_files["selected_papers"] = str(enriched)
                        self.state.output_files.setdefault("notes", {})
                        if isinstance(self.state.output_files["notes"], dict):
                            self.state.output_files["notes"]["selected_papers_enriched"] = str(enriched)
                        print(f"  ✓ selected_papers 摘要补齐完成: {enriched}")
                    else:
                        print("  ⚠️ selected_papers 摘要补齐失败（不阻断写作阶段）", file=sys.stderr)

            # Evidence cards：对写作阶段“证据包”做字段与长度压缩，降低上下文占用
            writing_cfg = self.config.get("writing", {}) if isinstance(self.config, dict) else {}
            ev_cfg = (writing_cfg.get("evidence_cards") or {}) if isinstance(writing_cfg.get("evidence_cards"), dict) else {}
            ev_enabled = bool(ev_cfg.get("enabled", True))
            if ev_enabled:
                cards_path = self.artifacts_dir / f"evidence_cards_{self.file_stem}.jsonl"
                if not cards_path.exists():
                    max_chars = int(ev_cfg.get("abstract_max_chars", 800) or 800)
                    ok = self._run_script(
                        "build_evidence_cards.py",
                        [
                            "--input", str(selected),
                            "--output", str(cards_path),
                            "--abstract-max-chars", str(max_chars),
                        ],
                    )
                    if ok and cards_path.exists():
                        self.state.output_files.setdefault("notes", {})
                        if isinstance(self.state.output_files["notes"], dict):
                            self.state.output_files["notes"]["evidence_cards"] = str(cards_path)
                        print(f"  ✓ evidence_cards: {cards_path}")
                    else:
                        print("  ⚠️ evidence_cards 生成失败（不阻断写作阶段）", file=sys.stderr)

            self._run_script(
                "update_working_conditions_data_extraction.py",
                [
                    "--md",
                    str(self.data_extraction_table),
                    "--papers",
                    str(selected),
                    "--max-rows",
                    "200000",
                ],
            )
            self.state.output_files["data_extraction_table"] = str(self.data_extraction_table)

        print("\n  请生成以下文件后继续：")
        print(f"    - {wc.name}（工作条件，包括评分/选文理由）")
        print(f"    - {review_tex.name}（综述正文 LaTeX，章节：摘要/引言/子主题/讨论/展望/结论）")
        print(f"    - {references_bib.name}（已由上一阶段生成）")
        print("\n  ⚠️ 子主题数量约束：除摘要/引言/讨论/展望/结论外，应有 3-7 个子主题 section")
        print("     如超过 7 个，请合并相似主题（如 CNN/Transformer → '深度学习模型架构'）")

        if review_tex.exists() and references_bib.exists() and wc.exists():
            self.state.completed_stages.append("5_write")
            self.save_state()
            return True

        print("  ✗ 尚未找到 review.tex 或 工作条件文件，请补全后重跑 --resume-from 5")
        self.save_state()
        return False

    def run_stage_6_validate(self) -> bool:
        print("\n[阶段6] 校验")
        wc = Path(self.state.output_files.get("working_conditions", ""))
        review_tex = Path(self.state.output_files.get("review_tex", ""))
        references_bib = Path(self.state.output_files.get("references_bib", ""))
        if not wc.exists() or not review_tex.exists() or not references_bib.exists():
            print("  ✗ 缺少工作条件/tex/bib")
            return False

        # 可选：校验字数预算
        budget_final = self.state.output_files.get("word_budget_final")
        selected = self.state.input_files.get("selected_papers")
        if budget_final and selected:
            try:
                self._run_script(
                    "validate_word_budget.py",
                    [
                        "--budget",
                        budget_final,
                        "--selected",
                        selected,
                        "--config",
                        str(self.config_path),
                    ],
                )
            except Exception:
                pass

        # 捕获验证脚本输出用于生成报告
        counts_ok, counts_output = self._run_script_capture_output(
            "validate_counts.py",
            [
                "--tex",
                str(review_tex),
                "--min-words",
                str(self.validation_words["min"]),
                "--max-words",
                str(self.validation_words["max"]),
                "--min-cites",
                str(self.validation_refs["min"]),
                "--max-cites",
                str(self.validation_refs["max"]),
            ],
        )

        tex_ok, tex_output = self._run_script_capture_output(
            "validate_review_tex.py",
            [
                "--tex",
                str(review_tex),
                "--bib",
                str(references_bib),
                "--min-refs",
                str(self.validation_refs["min"]),
                "--max-refs",
                str(self.validation_refs["max"]),
            ],
        )

        # 子主题数量验证（v3.4 新增）
        subtopic_ok, subtopic_output = self._run_script_capture_output(
            "validate_subtopic_count.py",
            [
                "--tex",
                str(review_tex),
                "--min-subtopics",
                "3",
                "--max-subtopics",
                "7",
            ],
        )
        print(subtopic_output)  # 显示验证结果
        if not subtopic_ok:
            print("  ⚠️ 子主题数量超出范围，建议合并相似主题", file=sys.stderr)

        # 生成验证报告
        validation_report_path = self._output_path("validation_report")
        counts_json_path: Optional[Path] = None
        try:
            # 将 validate_counts 的输出保存到 work_dir 内（避免 /tmp 导致的跨 run 污染与隔离冲突）
            counts_json_path = self.artifacts_dir / f"validate_counts_{self.file_stem}.json"
            counts_json_path.write_text(counts_output, encoding="utf-8")

            report_args = [
                "--counts-json",
                str(counts_json_path),
                "--review-tex-output",
                tex_output.strip(),
                "--output",
                str(validation_report_path),
                "--review-level",
                self.review_level,
                "--timestamp",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ]

            # 选文后摘要补齐属于默认关键质量门槛之一：在报告中显式给出摘要覆盖率，避免“无感引用缺摘要文献”
            selected_jsonl = str(self.state.input_files.get("selected_papers", "") or "").strip()
            if selected_jsonl:
                search_cfg = self.config.get("search", {}) if isinstance(self.config, dict) else {}
                ae = (search_cfg.get("abstract_enrichment") or {}) if isinstance(search_cfg.get("abstract_enrichment"), dict) else {}
                report_args.extend([
                    "--selected-jsonl",
                    selected_jsonl,
                    "--min-abstract-chars",
                    str(int(ae.get("min_abstract_chars", 80) or 80)),
                ])

            self._run_script("generate_validation_report.py", report_args)

            # 记录报告路径到 output_files
            self.state.output_files["validation_report"] = str(validation_report_path)
            print(f"  ✓ 验证报告: {validation_report_path}")

        except Exception as e:
            print(f"  ⚠️ 生成验证报告失败: {e}", file=sys.stderr)
        finally:
            # counts_json_path 保留在 artifacts_dir 便于复盘与追溯
            pass

        if counts_ok and tex_ok:
            self.state.completed_stages.append("6_validate")
            self.save_state()
            return True

        print("  ✗ 校验未通过")
        return False

    def run_stage_7_export(self) -> bool:
        print("\n[阶段7] 导出 PDF/Word")
        review_tex = Path(self.state.output_files.get("review_tex", ""))
        references_bib = Path(self.state.output_files.get("references_bib", ""))
        if not review_tex.exists() or not references_bib.exists():
            print("  ✗ 缺少 review.tex 或参考文献 bib")
            return False

        pdf_out = self._output_path("review_pdf")
        word_out = self._output_path("review_word")
        latex_cfg = self.config.get("latex", {}) if isinstance(self.config, dict) else {}
        template_override = latex_cfg.get("template_path_override") or latex_cfg.get("template_path")
        if template_override:
            print(f"  使用模板: {template_override}")
        print(f"  tex: {review_tex}")
        print(f"  bib: {references_bib}")
        print(f"  pdf 输出: {pdf_out}")
        print(f"  word 输出: {word_out}")

        pdf_ok = self._run_script("compile_latex_with_bibtex.py", [str(review_tex), str(pdf_out)])
        word_ok = self._run_script("convert_latex_to_word.py", [str(review_tex), str(references_bib), str(word_out)])

        if pdf_ok and word_ok and pdf_out.exists() and word_out.exists():
            self.state.output_files["review_pdf"] = str(pdf_out)
            self.state.output_files["review_word"] = str(word_out)
            self.state.completed_stages.append("7_export")
            self.save_state()
            print("  ✓ 导出完成")
            return True

        print("  ✗ 导出失败")
        return False

    # ---------------- orchestrator ---------------- #
    def run(self, resume_from: Optional[int]) -> bool:
        print("=" * 70)
        print("相关性驱动系统综述 Pipeline Runner")
        print("=" * 70)
        print(f"主题: {self.topic}")
        print(f"档位: {self.review_level}")
        print(f"输出前缀: {self.file_stem}")
        print(f"工作目录: {self.work_dir}")

        # 自动恢复
        state_file = self._state_file()
        if state_file.exists() and resume_from is None:
            try:
                loaded = PipelineState.from_json(state_file)
                self.state = loaded
                print(f"✓ 已从 {state_file} 恢复状态（已完成: {', '.join(self.state.completed_stages) or '无'}）")
            except Exception as e:  # noqa: BLE001
                print(f"⚠️ 恢复状态失败: {e}")

        stages = [
            ("0_setup", self.run_stage_0_setup),
            ("1_search", self.run_stage_1_search),
            ("2_dedupe", self.run_stage_2_dedupe),
            ("3_score", self.run_stage_3_score),
            ("4_select", self.run_stage_4_select),
            ("4.5_word_budget", self.run_stage_4_5_word_budget),
            ("5_write", self.run_stage_5_write),
            ("6_validate", self.run_stage_6_validate),
            ("7_export", self.run_stage_7_export),
        ]

        start_idx = resume_from if resume_from is not None else 0
        if resume_from is None and self.state.completed_stages:
            try:
                last = self.state.completed_stages[-1]
                stage_names = [s[0] for s in stages]
                if last in stage_names:
                    start_idx = stage_names.index(last) + 1
            except Exception:
                start_idx = 0
        for i, (name, fn) in enumerate(stages):
            if i < start_idx:
                print(f"⊙ 跳过已完成阶段: {name}")
                continue
            print(f"\n▶ 执行阶段: {name} - {self.STAGES.get(name, name)}")
            self.state.current_stage = name
            stage_start = datetime.now().isoformat()
            ok = False
            try:
                ok = fn()
            except KeyboardInterrupt:
                print(f"\n⚠️ 用户中断于 {name}")
                self.state.current_stage = name
                self.save_state()
                return False
            except Exception as e:  # noqa: BLE001
                print(f"✗ 阶段 {name} 发生异常: {e}")
                self.state.current_stage = name
                self.save_state()
                return False
            stage_end = datetime.now().isoformat()
            self.state.metrics.setdefault("timing", {})[name] = {"start": stage_start, "end": stage_end}
            if not ok:
                print(f"✗ 阶段 {name} 未完成")
                self.save_state()
                return False
        return True


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description="Run relevance-driven systematic literature review pipeline")
    parser.add_argument("--topic", required=False, help="主题")
    parser.add_argument("--domain", default="general", help="领域（可选）")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent.parent / "config.yaml")
    parser.add_argument("--work-dir", type=Path, required=False, help="工作目录（必须显式指定）")
    parser.add_argument("--review-level", choices=["premium", "standard", "basic"], help="档位（可选）")
    parser.add_argument("--output-stem", help="文件名前缀（可选）")
    parser.add_argument("--resume", type=Path, help="从已有 work_dir 恢复（自动读取其中的 pipeline_state.json）")
    parser.add_argument("--resume-from", type=int, help="从阶段编号开始执行（0-based）")
    args = parser.parse_args()

    work_dir = args.work_dir
    if args.resume:
        work_dir = args.resume if args.resume.is_dir() else args.resume.parent
    if work_dir is None:
        raise ValueError("请显式传入 --work-dir <任务子目录> 或使用 --resume")
    work_dir = Path(work_dir).expanduser().resolve()

    topic = args.topic
    if args.resume and not topic:
        topic = Path(work_dir).name
    if not topic:
        raise ValueError("缺少 --topic")

    # 防御性提示：避免出现 {topic}/{topic} 的异常嵌套目录（通常来自外部编排器重复拼接）
    try:
        wd = Path(work_dir)
        if wd.name and wd.parent.name and wd.name == wd.parent.name:
            print(f"⚠️ 检测到疑似重复嵌套目录: {wd}（建议改为父目录: {wd.parent}）", file=sys.stderr)
    except Exception:
        pass

    runner = PipelineRunner(
        topic=topic,
        domain=args.domain,
        config_path=args.config,
        work_dir=work_dir,
        review_level=args.review_level,
        output_stem=args.output_stem,
    )
    ok = runner.run(resume_from=args.resume_from)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
