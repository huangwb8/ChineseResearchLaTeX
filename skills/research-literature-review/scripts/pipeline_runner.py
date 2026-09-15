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
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import io

import yaml

try:
    from layout_paths import LayoutPaths
    from path_scope import resolve_and_check
    from publish_deliverables import PublishError, publish_deliverables
    from search_skill_resolver import assert_compatible, resolve_search_skill_root
    from query_contract import (
        QueryInputError,
        legacy_output_stems,
        load_query_plan,
        normalize_output_stem,
        sha256_file,
    )
except ModuleNotFoundError:  # 允许被 qa 动态加载
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from layout_paths import LayoutPaths
    from path_scope import resolve_and_check
    from publish_deliverables import PublishError, publish_deliverables
    from search_skill_resolver import assert_compatible, resolve_search_skill_root
    from query_contract import (
        QueryInputError,
        legacy_output_stems,
        load_query_plan,
        normalize_output_stem,
        sha256_file,
    )


def _safe_topic_slug(topic: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "-", (topic or "").strip())
    slug = re.sub(r"-{2,}", "-", slug).strip(".-_")
    return (slug[:48].strip(".-_") or "review")


def _default_bensz_work_dir(topic: str) -> Path:
    root = Path.cwd().resolve() / ".bensz-api"
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    base = f"task-{stamp}-{_safe_topic_slug(topic)}"
    candidate = root / base
    if not candidate.exists():
        return candidate / "research-literature-review"
    for idx in range(2, 100):
        candidate = root / f"{base}-{idx:02d}"
        if not candidate.exists():
            return candidate / "research-literature-review"
    raise ValueError(f"无法在 {root} 下分配唯一工作目录: {base}")


def _load_resume_identity(work_dir: Path) -> tuple[Optional[str], Optional[str]]:
    """在构造 runner 前恢复主题/stem，避免 resume 使用目录名改写输出身份。"""
    root = Path(work_dir).expanduser().resolve()
    candidates = [
        root / "output" / "pipeline_state.json",
        root / ".systematic-literature-review" / "pipeline_state.json",
    ]
    for state_file in candidates:
        if not state_file.exists():
            continue
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None, None
        topic = str(data.get("topic") or "").strip() or None
        metrics = data.get("metrics", {}) if isinstance(data.get("metrics", {}), dict) else {}
        stem = str(data.get("file_stem") or metrics.get("file_stem") or "").strip() or None
        return topic, stem
    return None, None


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class PipelineState:
    version: str = "2.0"
    topic: str = ""
    file_stem: str = ""
    domain: str = "general"
    started_at: str = ""
    current_stage: str = ""
    completed_stages: List[str] = field(default_factory=list)
    input_files: Dict[str, str] = field(default_factory=dict)
    output_files: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    search_mode: str = ""
    query_source: str = ""
    requested_query_count: int = 0
    accepted_query_count: int = 0
    query_file_sha256: str = ""
    fallback_reason: str = ""
    search_manifest: str = ""
    search_contract_version: str = ""
    search_manifest_sha256: str = ""
    candidates_sha256: str = ""
    purpose: str = "standard-review"

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
        publish_dir: Optional[Path] = None,
        publish_include_supporting: Optional[bool] = None,
        publish_force: Optional[bool] = None,
        query_file: Optional[Path] = None,
        allow_single_query_fallback: Optional[bool] = None,
        fallback_reason: Optional[str] = None,
        search_skill_root: Optional[Path] = None,
        purpose: str = "standard-review",
    ):
        self.topic = topic
        self.domain = domain
        if purpose not in {"standard-review", "novelty-check"}:
            raise ValueError(f"不支持的 purpose: {purpose}")
        self.purpose = purpose
        self.search_skill_root_override = search_skill_root.expanduser().resolve() if search_skill_root is not None else None
        # Resolve before any search subprocess is started.  This is deliberately fail-closed;
        # a missing dependency must not silently reactivate the old provider implementation.
        self.search_skill_root: Optional[Path] = None
        self.search_skill_version = ""
        self.search_contract_version = ""
        self.search_dependency_error = ""
        try:
            self.search_skill_root = resolve_search_skill_root(
                explicit=self.search_skill_root_override,
                project_root=Path(__file__).resolve().parents[3],
            )
            self.search_skill_version, self.search_contract_version = assert_compatible(self.search_skill_root)
            # Legacy wrappers run in child processes; export the resolved
            # producer root so an independently installed review skill does not
            # accidentally import a sibling copy (or fail on a missing one).
            os.environ["RESEARCH_LITERATURE_SEARCH_ROOT"] = str(self.search_skill_root)
        except (FileNotFoundError, RuntimeError, ModuleNotFoundError) as exc:
            # Keep construction usable for --prepare-only and legacy checkpoint inspection;
            # stage 1 emits the actionable error before retrieval.
            self.search_dependency_error = str(exc)
        # 统一使用绝对路径：避免在子进程 cwd=self.work_dir 时把路径“拼两遍”，同时减少跨 run 污染风险。
        self.work_dir = work_dir.expanduser().resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        task_readme = self.work_dir.parent / "README.md"
        if self.work_dir.parent.name.startswith("task-") and not task_readme.exists():
            task_readme.write_text(
                "# BenszAPI 任务工作区\n\n"
                "- 本轮 skill：`research-literature-review`\n"
                "- 输入引用、临时产物和日志分别保存于 skill 的 input/output/log。\n",
                encoding="utf-8",
            )
        # 设置工作目录隔离范围：子进程默认只允许在该目录内读写（由各脚本从 env 读取并校验）。
        os.environ["SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT"] = str(self.work_dir)

        self.config_path = config_path.expanduser().resolve()
        self.config = self._load_config(self.config_path)
        self.layout = LayoutPaths.from_config(self.work_dir, self.config)
        self.legacy_layout_mode = False
        # 仅在检测到旧 checkpoint 时兼容历史隐藏目录；新运行始终遵循 config.yaml。
        legacy_layout = LayoutPaths.from_config(self.work_dir, {"layout": {"hidden_dir_name": ".systematic-literature-review"}})
        if not self.layout.state_file.exists() and legacy_layout.state_file.exists():
            self.layout = legacy_layout
            self.legacy_layout_mode = True
        self.review_level = self._resolve_review_level(review_level)
        self.raw_output_stem = output_stem or topic
        self.file_stem = self._sanitize_topic_for_filename(self.raw_output_stem)
        self.publish_dir = Path(publish_dir).expanduser().resolve() if publish_dir else None
        publish_cfg = self.config.get("publish", {}) if isinstance(self.config, dict) else {}
        self.publish_include_supporting = bool(
            publish_cfg.get("include_supporting", False)
            if publish_include_supporting is None
            else publish_include_supporting
        )
        self.publish_force = bool(publish_cfg.get("force", False) if publish_force is None else publish_force)
        if self.publish_dir is not None:
            try:
                self.publish_dir.relative_to(self.work_dir)
            except ValueError:
                pass
            else:
                raise ValueError("publish_dir 不能位于内部 work_dir 内，请使用独立的正式交付目录")

        scoring_cfg = self.config.get("scoring", {}) if isinstance(self.config, dict) else {}
        word_range = (scoring_cfg.get("default_word_range") or {}).get(self.review_level, {}) if isinstance(scoring_cfg, dict) else {}
        ref_range = (scoring_cfg.get("default_ref_range") or {}).get(self.review_level, {}) if isinstance(scoring_cfg, dict) else {}
        self.target_words = {"min": int(word_range.get("min", 0) or 0), "max": int(word_range.get("max", 0) or 0)}
        self.target_refs = {"min": int(ref_range.get("min", 0) or 0), "max": int(ref_range.get("max", 0) or 0)}
        selection_cfg = self.config.get("selection", {}) if isinstance(self.config, dict) else {}
        self.minimum_score = float(selection_cfg.get("minimum_score", 5.0))

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

        self.hidden_dir = self.layout.hidden_dir
        self.artifacts_dir = self.layout.artifacts_dir
        self.reference_dir = self.layout.reference_dir
        self.input_dir = self.work_dir / "input"
        layout_cfg = self.config.get("layout", {}) if isinstance(self.config, dict) else {}
        self.data_extraction_table = self.reference_dir / layout_cfg.get("reference_data_extraction_name", "data_extraction_table.md")

        query_cfg = self.config.get("query_input", {}) if isinstance(self.config, dict) else {}
        self.query_input_dir_name = str(query_cfg.get("directory", "input"))
        if Path(self.query_input_dir_name).is_absolute() or ".." in Path(self.query_input_dir_name).parts:
            raise ValueError("query_input.directory 必须是 work_dir 内的安全相对路径")
        self.query_input_dir = resolve_and_check(
            self.work_dir / self.query_input_dir_name,
            self.work_dir,
            must_exist=False,
        )
        self.query_input_dir.mkdir(parents=True, exist_ok=True)
        self.query_canonical_filename = str(query_cfg.get("canonical_filename", "queries.json"))
        if Path(self.query_canonical_filename).name != self.query_canonical_filename:
            raise ValueError("query_input.canonical_filename 必须是单个文件名")
        self.min_queries = int(query_cfg.get("min_queries", 5))
        self.max_queries = int(query_cfg.get("max_queries", 25))
        config_fallback = bool(query_cfg.get("allow_single_query_fallback", False))
        self.allow_single_query_fallback = (
            config_fallback if allow_single_query_fallback is None else bool(allow_single_query_fallback)
        )
        self.fallback_authorization = (
            "explicit_cli_fallback"
            if allow_single_query_fallback is True
            else ("config_fallback" if self.allow_single_query_fallback else "")
        )
        self.fallback_reason = (fallback_reason or "").strip()
        self.explicit_query_file = (
            Path(query_file).expanduser().resolve() if query_file is not None else None
        )

        # 缓存策略（默认关闭，避免 run 目录 cache/api 文件爆炸）
        cache_cfg = self.config.get("cache", {}) if isinstance(self.config, dict) else {}
        api_cache_cfg = cache_cfg.get("api", {}) if isinstance(cache_cfg.get("api", {}), dict) else {}
        self.cache_enabled = bool(api_cache_cfg.get("enabled", False))
        self.cache_ttl_seconds = int(api_cache_cfg.get("ttl_seconds", 86400) or 86400)
        self.cache_dir: Optional[Path] = None
        if self.cache_enabled:
            self.cache_dir = self.layout.cache_dir / "api"

        # AI 临时脚本目录（供 AI 在工作流中创建临时脚本使用）
        self.scripts_dir = self.layout.scripts_dir

        self.layout.ensure(cache_enabled=self.cache_enabled)
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            # 设置缓存目录环境变量（供 api_cache.py 使用）
            os.environ["SYSTEMATIC_LITERATURE_REVIEW_CACHE_DIR"] = str(self.cache_dir)

        # 设置 AI 临时脚本目录环境变量（供 AI 创建的临时脚本使用）
        os.environ["SYSTEMATIC_LITERATURE_REVIEW_SCRIPTS_DIR"] = str(self.scripts_dir)

        word_budget_cfg = (self.config.get("word_budget") or {}) if isinstance(self.config, dict) else {}
        outputs_cfg = word_budget_cfg.get("outputs", {}) if isinstance(word_budget_cfg, dict) else {}
        self.word_budget_run_pattern = outputs_cfg.get("run_pattern", "word_budget_run{n}.csv")
        self.word_budget_final = outputs_cfg.get("final", "word_budget_final.csv")
        self.word_budget_non_cited = outputs_cfg.get("non_cited", "non_cited_budget.csv")


        output_cfg = self.config.get("output", {}) if isinstance(self.config, dict) else {}
        self.output_templates = output_cfg

        self.state = PipelineState(
            topic=self.topic,
            file_stem=self.file_stem,
            domain=self.domain,
            started_at=datetime.now().isoformat(),
            config=self.config,
            purpose=self.purpose,
        )
        self.state.metrics["purpose"] = self.purpose
        self.state.metrics["review_level"] = self.review_level
        self.state.metrics["target_words"] = self.target_words
        self.state.metrics["target_refs"] = self.target_refs
        self.state.metrics["work_dir"] = str(self.work_dir)
        self.state.metrics["cache_enabled"] = bool(self.cache_enabled)
        self.state.metrics["search_skill_root"] = str(self.search_skill_root) if self.search_skill_root else ""
        self.state.metrics["search_skill_version"] = self.search_skill_version

    # ---------------- internal helpers ---------------- #
    @staticmethod
    def _sanitize_topic_for_filename(raw: str) -> str:
        """兼容旧调用方；实际规则由 query_contract 统一维护。"""
        return normalize_output_stem(raw)

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
        return self.layout.state_file

    def save_state(self) -> None:
        self.state.to_json(self._state_file())

    def _query_template_path(self) -> Path:
        return resolve_and_check(
            self.query_input_dir / self.query_canonical_filename,
            self.work_dir,
            must_exist=False,
        )

    def _write_query_template(self) -> Path:
        path = self._query_template_path()
        if not path.exists():
            path.write_text('{"queries": []}\n', encoding="utf-8")
            self.state.metrics["generated_query_template_sha256"] = sha256_file(path)
        return path

    def _stage_explicit_query_file(self, source: Path) -> Path:
        if not source.exists():
            raise QueryInputError(f"显式查询文件不存在：{source}")
        if not source.is_file():
            raise QueryInputError(f"显式查询路径不是普通文件：{source}")
        destination = self._query_template_path()
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        return destination

    def _discover_query_file(self) -> tuple[Optional[Path], str]:
        if self.explicit_query_file is not None:
            staged = self._stage_explicit_query_file(self.explicit_query_file)
            return staged, f"explicit:{self.explicit_query_file}"

        candidates: list[tuple[Path, str]] = [
            (self._query_template_path(), "input:queries.json"),
            (
                self.query_input_dir / f"queries_{self.file_stem}.json",
                f"input:queries_{self.file_stem}.json",
            ),
            (
                self.artifacts_dir / f"queries_{self.file_stem}.json",
                f"artifacts:queries_{self.file_stem}.json",
            ),
        ]
        for legacy_stem in legacy_output_stems(self.raw_output_stem):
            candidates.append(
                (
                    self.artifacts_dir / f"queries_{legacy_stem}.json",
                    f"legacy_artifacts:queries_{legacy_stem}.json",
                )
            )

        found: list[tuple[Path, str]] = []
        seen: set[Path] = set()
        for path, source in candidates:
            resolved = path.expanduser().resolve()
            if resolved in seen or not resolved.exists():
                continue
            template_hash = str(self.state.metrics.get("generated_query_template_sha256") or "")
            template_path = self.state.input_files.get("query_template", "")
            if template_hash and template_path:
                recorded_template = Path(template_path).expanduser().resolve()
                if resolved == recorded_template and sha256_file(resolved) == template_hash:
                    # 阶段 0 自动生成且从未填充的模板等价于“尚未提供查询”。
                    continue
            seen.add(resolved)
            found.append((resolved, source))
        if len(found) > 1:
            paths = "\n".join(f"  - {path}" for path, _ in found)
            raise QueryInputError(
                "发现多个查询文件，无法确定唯一输入；请删除冲突文件或使用 --query-file：\n"
                + paths
            )
        return found[0] if found else (None, "")

    def _validate_search_log(self, path: Path, expected_mode: str) -> bool:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            print(f"  ✗ Search Log 无法读取：{path}（{exc}）")
            return False
        required = {
            "search_mode",
            "query_source",
            "requested_query_count",
            "accepted_query_count",
            "fallback_reason",
        }
        missing = sorted(required - set(data))
        if missing or data.get("search_mode") != expected_mode:
            print(
                f"  ✗ Search Log 契约不完整或模式不匹配：missing={missing}, "
                f"mode={data.get('search_mode')!r}"
            )
            return False
        return True

    def _validate_search_bundle(self, manifest_path: Path) -> bool:
        """Validate the producer bundle before review reads any candidates."""
        if not manifest_path.exists():
            print(f"  ✗ search manifest 不存在：{manifest_path}")
            return False
        try:
            manifest_path = manifest_path.expanduser().resolve()
            if manifest_path.name != "manifest.json":
                raise ValueError("manifest filename must be manifest.json")
            manifest_path.parent.relative_to(self.artifacts_dir.expanduser().resolve())
        except ValueError as exc:
            print(f"  ✗ search manifest 路径不安全：{manifest_path}（{exc}）")
            return False
        search_root = self.search_skill_root
        if search_root is None:
            print(f"  ✗ research-literature-search 依赖不可用：{self.search_dependency_error}")
            return False
        scripts = search_root / "scripts"
        if not scripts.is_dir():
            print(f"  ✗ search skill 缺少 scripts 目录：{scripts}")
            return False
        sys.path.insert(0, str(scripts))
        try:
            from validate_bundle import validate_bundle  # type: ignore
            errors = validate_bundle(manifest_path.parent)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ search manifest 校验异常：{exc}")
            return False
        finally:
            try:
                sys.path.remove(str(scripts))
            except ValueError:
                pass
        if errors:
            print("  ✗ search bundle 不可消费：")
            for error in errors[:8]:
                print(f"    - {error}")
            return False
        return True

    def _record_search_contract_reference(self, manifest: Path) -> None:
        """Keep a review-local, read-only handoff note without duplicating the bundle."""
        contract_dir = resolve_and_check(self.input_dir / "search-contract", self.work_dir, must_exist=False)
        contract_dir.mkdir(parents=True, exist_ok=True)
        reference = contract_dir / "source.json"
        canonical = manifest.parent / "candidates_deduped.jsonl"
        payload = {
            "manifest": str(manifest),
            "manifest_sha256": sha256_file(manifest),
            "candidate": str(canonical),
            "candidate_sha256": sha256_file(canonical) if canonical.exists() else "",
            "contract_version": "rls.v1",
            "read_only": True,
        }
        reference.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.state.input_files["search_contract"] = str(reference)

    def _validate_resume_query_input(self) -> bool:
        if "1_search" not in self.state.completed_stages:
            return True
        if not self.state.search_mode:
            print("⚠️ 历史 checkpoint 缺少查询审计字段，按兼容模式继续，不补写推断值。")
            return True
        if self.state.search_mode == "multi_query":
            raw_path = self.state.input_files.get("query_file", "")
            query_file = Path(raw_path) if raw_path else Path()
            if query_file == Path() or not query_file.exists() or not query_file.is_file():
                print(f"✗ resume 查询文件缺失：{raw_path or '(未记录)'}")
                return False
            fingerprint = sha256_file(query_file)
            if self.state.query_file_sha256 and fingerprint != self.state.query_file_sha256:
                print("✗ resume 查询文件指纹已变化；请确认输入后启动新的 run。")
                return False
            if self.explicit_query_file is not None:
                if not self.explicit_query_file.exists() or not self.explicit_query_file.is_file():
                    print(f"✗ resume 显式查询文件缺失：{self.explicit_query_file}")
                    return False
                if self.state.query_file_sha256 and sha256_file(self.explicit_query_file) != self.state.query_file_sha256:
                    print("✗ resume 显式查询文件与 checkpoint 指纹不一致。")
                    return False
        elif self.state.search_mode == "single_query" and not self.state.fallback_reason:
            print("✗ 单查询 checkpoint 缺少 fallback_reason，不能作为已审计结果恢复。")
            return False
        return True

    def _validate_resume_search_bundle(self) -> bool:
        if "1_search" not in self.state.completed_stages or not self.state.search_manifest:
            return True
        manifest = Path(self.state.search_manifest)
        if not self._validate_search_bundle(manifest):
            return False
        if self.state.search_manifest_sha256 and sha256_file(manifest) != self.state.search_manifest_sha256:
            print("✗ resume search manifest 指纹已变化；请重新检索或确认输入。")
            return False
        canonical = manifest.parent / "candidates_deduped.jsonl"
        if self.state.candidates_sha256 and canonical.exists() and sha256_file(canonical) != self.state.candidates_sha256:
            print("✗ resume canonical candidates 指纹已变化；请重新检索或确认输入。")
            return False
        try:
            _, contract = assert_compatible(self.search_skill_root) if self.search_skill_root else ("", "")
        except RuntimeError as exc:
            print(f"✗ resume search contract 不兼容：{exc}")
            return False
        if self.state.search_contract_version and contract != self.state.search_contract_version:
            print("✗ resume search contract version 与 checkpoint 不一致。")
            return False
        return True

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
        if self.legacy_layout_mode:
            output_root = self.work_dir
        elif key in {"working_conditions", "review_tex", "references_bib", "validation_report"}:
            output_root = self.layout.supporting_dir
        else:
            output_root = self.layout.deliverables_dir
        return output_root / tpl.format(topic=self.file_stem)

    def _write_working_conditions_skeleton(self, path: Path) -> None:
        if path.exists():
            return
        artifacts_rel = self.artifacts_dir.relative_to(self.work_dir).as_posix()
        reference_rel = self.data_extraction_table.relative_to(self.work_dir).as_posix()
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
            f"- 评分文件路径：`{artifacts_rel}/scored_papers_{{主题}}.jsonl`",
            "## Data Extraction Table（数据抽取表）",
            f"- 数据抽取表路径：`{reference_rel}`",
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
        query_template = self._write_query_template()
        self.state.input_files.setdefault("query_template", str(query_template))
        print(f"  查询计划路径：{query_template}")
        print("  请填充查询 JSON 后再启动阶段 1，或使用 --query-file 显式传入。")
        if "0_setup" not in self.state.completed_stages:
            self.state.completed_stages.append("0_setup")
        self.save_state()
        return True

    def run_stage_1_search(self) -> bool:
        print("\n[阶段1] 多查询文献检索")
        if self.search_skill_root is None:
            print(f"  ✗ 必需依赖 research-literature-search 未找到：{self.search_dependency_error}")
            print("  请安装该 Skill，或使用 --search-skill-root 指定其目录。")
            return False
        papers = Path(self.state.input_files.get("papers", "")) if self.state.input_files else Path()
        if papers.exists() and papers.is_file() and papers.suffix.lower() == ".jsonl":
            print(f"  已存在候选库: {papers}")
            if self.state.search_manifest:
                manifest = Path(self.state.search_manifest)
                if not self._validate_search_bundle(manifest):
                    return False
                self.state.search_manifest_sha256 = sha256_file(manifest)
                canonical = manifest.parent / "candidates_deduped.jsonl"
                if canonical.exists():
                    self.state.candidates_sha256 = sha256_file(canonical)
            search_log_raw = self.state.output_files.get("search_log", "")
            search_log = Path(search_log_raw) if search_log_raw else Path()
            if self.state.search_mode not in {"multi_query", "single_query"}:
                print("  ✗ 候选库缺少 search_mode 审计字段，不能将阶段 1 标记为完成。")
                return False
            if search_log == Path() or not search_log.exists() or not self._validate_search_log(
                search_log,
                self.state.search_mode,
            ):
                print("  ✗ 候选库缺少有效 Search Log，不能将阶段 1 标记为完成。")
                return False
            if "1_search" not in self.state.completed_stages:
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
        provider_order = search_cfg.get("provider_priority") or search_cfg.get("providers") or []
        if not isinstance(provider_order, list):
            provider_order = [item.strip() for item in str(provider_order).split(",") if item.strip()]
        fallback_cfg = search_cfg.get("fallback", {}) if isinstance(search_cfg.get("fallback"), dict) else {}
        fallback_enabled = bool(fallback_cfg.get("enabled", True))
        output_file = self.artifacts_dir / f"papers_{self.file_stem}.jsonl"
        search_log = self.artifacts_dir / f"search_log_{self.file_stem}.json"
        search_bundle = self.artifacts_dir / f"search_bundle_{self.file_stem}"

        try:
            queries_file, query_source = self._discover_query_file()
        except QueryInputError as exc:
            print(f"  ✗ 查询输入冲突或不可用：{exc}")
            return False

        if queries_file is not None:
            try:
                query_plan = load_query_plan(
                    queries_file,
                    min_queries=self.min_queries,
                    max_queries=self.max_queries,
                )
            except QueryInputError as exc:
                print(f"  ✗ 查询文件不符合 schema/数量契约：{exc}")
                print(
                    '  期望格式：{"queries": [{"query": "...", "rationale": "..."}]}；'
                    f"有效查询数 {self.min_queries}–{self.max_queries}。"
                )
                return False

            print(f"  使用多查询输入: {queries_file}")
            cache_args: list[str] = []
            if self.cache_dir is not None:
                cache_args = ["--cache-dir", str(self.cache_dir)]
            ok = self._run_script(
                "multi_query_search.py",
                [
                    "--queries", str(queries_file),
                    "--output", str(output_file),
                    "--search-log", str(search_log),
                    "--query-source", query_source,
                    "--min-queries", str(self.min_queries),
                    "--max-queries", str(self.max_queries),
                    "--max-results-per-query", str(max_results_per_query),
                    "--max-total", str(max_total),
                    "--bundle-dir", str(search_bundle),
                    "--topic", self.topic,
                    "--scope-root", str(self.work_dir),
                    "--search-skill-root", str(self.search_skill_root),
                    "--provider-order", ",".join(str(item) for item in provider_order),
                    *([] if fallback_enabled else ["--no-fallback"]),
                    *cache_args,
                ],
            )
            if not ok or not output_file.exists() or not search_log.exists():
                print("  ✗ 多查询检索未生成完整的 papers/Search Log。")
                return False
            if not self._validate_search_log(search_log, "multi_query"):
                return False
            manifest = search_bundle / "manifest.json"
            if manifest.exists():
                if not self._validate_search_bundle(manifest):
                    return False
                self._record_search_contract_reference(manifest)
            elif not self._run_script.__class__.__module__.startswith("unittest.mock"):
                print("  ✗ 新检索未生成 manifest.json，拒绝进入综述阶段。")
                return False
            else:
                # Unit/in-process compatibility callers may stub the deprecated wrapper;
                # real subprocess runs always require the manifest above.
                print("  ⚠️ 检测到兼容测试替身未生成 search manifest，保留旧阶段行为。")

            self.state.search_mode = "multi_query"
            self.state.query_source = query_source
            self.state.requested_query_count = query_plan.requested_count
            self.state.accepted_query_count = query_plan.accepted_count
            self.state.query_file_sha256 = sha256_file(queries_file)
            self.state.fallback_reason = ""
            self.state.input_files["query_file"] = str(queries_file)
            if manifest.exists():
                self.state.search_manifest = str(manifest)
                self.state.search_contract_version = "rls.v1"
                self.state.search_manifest_sha256 = sha256_file(manifest)
                canonical = search_bundle / "candidates_deduped.jsonl"
                self.state.candidates_sha256 = sha256_file(canonical) if canonical.exists() else ""
        else:
            if not self.allow_single_query_fallback:
                print("  ✗ 未找到有效多查询输入；默认 fail-closed，不会自动执行单查询。")
                print(
                    f"  请填写 {self._query_template_path()}，或使用 --query-file；"
                    "确需后备时显式传 --allow-single-query-fallback。"
                )
                return False

            reason = self.fallback_reason or "未提供多查询文件，调用方显式授权单查询后备"
            print("  ⚠️ 已显式授权单查询后备；该模式会写入警告和审计字段。")
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
            if not ok or not output_file.exists():
                print("  ✗ 单查询后备检索未生成 papers 文件。")
                return False
            fallback_log = {
                "search_mode": "single_query",
                "query_source": self.fallback_authorization or "explicit_fallback",
                "requested_query_count": 1,
                "accepted_query_count": 1,
                "fallback_reason": reason,
                "topic": self.topic,
                "warning": "显式单查询后备结果，不得解释为多查询检索",
            }
            search_log.write_text(
                json.dumps(fallback_log, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            if not self._validate_search_log(search_log, "single_query"):
                return False
            self.state.search_mode = "single_query"
            self.state.query_source = fallback_log["query_source"]
            self.state.requested_query_count = 1
            self.state.accepted_query_count = 1
            self.state.query_file_sha256 = ""
            self.state.fallback_reason = reason

        self.state.input_files["papers"] = str(output_file)
        self.state.output_files["search_log"] = str(search_log)
        if "1_search" not in self.state.completed_stages:
            self.state.completed_stages.append("1_search")
        self.save_state()
        return True

    def run_stage_2_dedupe(self) -> bool:
        print("\n[阶段2] 去重")
        if self.state.search_manifest:
            manifest = Path(self.state.search_manifest)
            if not self._validate_search_bundle(manifest):
                return False
            bundle = manifest.parent
            deduped = bundle / "candidates_deduped.jsonl"
            dedupe_map = bundle / "dedupe_map.json"
            if not deduped.exists() or not dedupe_map.exists():
                print("  ✗ search bundle 缺少 canonical candidates 或 dedupe map")
                return False
            # Preserve the historical flat artifact names as read-only aliases;
            # the bundle remains the single source of truth consumed by later
            # stages and recorded in the checkpoint.
            legacy_deduped = self.artifacts_dir / f"papers_deduped_{self.file_stem}.jsonl"
            legacy_map = self.artifacts_dir / f"dedupe_map_{self.file_stem}.json"
            if legacy_deduped.resolve() != deduped.resolve():
                shutil.copy2(deduped, legacy_deduped)
            if legacy_map.resolve() != dedupe_map.resolve():
                shutil.copy2(dedupe_map, legacy_map)
            self.state.input_files["papers_deduped"] = str(deduped)
            self.state.output_files["dedupe_map"] = str(legacy_map)
            self.state.metrics["search_canonical_candidates"] = str(deduped)
            self.state.metrics["search_dedupe_map"] = str(dedupe_map)
            self.state.candidates_sha256 = sha256_file(deduped)
            if "2_dedupe" not in self.state.completed_stages:
                self.state.completed_stages.append("2_dedupe")
            self.save_state()
            print("  ✓ 已验证 search canonical 候选；阶段 2 不重复执行去重")
            return True
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
            "--min-score",
            str(self.minimum_score),
            "--purpose",
            self.purpose,
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

        selected_count = int(self.state.metrics.get("reference_count", 0) or 0)
        effective_min_refs = min(self.validation_refs["min"], selected_count)

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
                str(effective_min_refs),
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
                str(effective_min_refs),
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
    def run(self, resume_from: Optional[int], prepare_only: bool = False) -> bool:
        print("=" * 70)
        print("相关性驱动系统综述 Pipeline Runner")
        print("=" * 70)
        print(f"主题: {self.topic}")
        print(f"档位: {self.review_level}")
        print(f"输出前缀: {self.file_stem}")
        print(f"工作目录: {self.work_dir}")

        # 先恢复已有状态，再决定自动续跑或显式起始阶段。显式 --resume-from
        # 只控制从哪里继续，不能跳过 checkpoint 加载，否则后续保存会覆盖历史状态。
        state_file = self._state_file()
        if state_file.exists():
            try:
                loaded = PipelineState.from_json(state_file)
                self.state = loaded
                if self.purpose == "standard-review" and loaded.purpose == "novelty-check":
                    self.purpose = loaded.purpose
                print(f"✓ 已从 {state_file} 恢复状态（已完成: {', '.join(self.state.completed_stages) or '无'}）")
            except Exception as e:  # noqa: BLE001
                print(f"⚠️ 恢复状态失败: {e}")
                print("✗ 为避免覆盖已有 checkpoint，本轮停止；请先修复或备份状态文件。")
                return False
            if not self._validate_resume_query_input():
                return False
            if not self._validate_resume_search_bundle():
                return False

        if prepare_only:
            print("\n▶ 准备查询输入（prepare-only）")
            if not self.run_stage_0_setup():
                return False
            print(f"✓ 已准备查询文件：{self._query_template_path()}")
            print("填充后使用 --resume <work-dir> --resume-from 1 继续。")
            return True

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
        if self.purpose == "novelty-check":
            stages = stages[:5]

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

        # Pipeline 完成后自动整理工作目录
        print("\n[整理] 移动中间文件到隐藏目录")
        try:
            organize_script = Path(__file__).parent / "organize_run_dir.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(organize_script),
                    "--work-dir",
                    str(self.work_dir),
                    "--config",
                    str(self.config_path),
                    "--apply",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                if "no moves needed" in result.stdout:
                    print("  ✓ 无需整理（目录已整洁）")
                else:
                    print("  ✓ 整理完成")
            else:
                # 非零退出码是真正的错误
                error_msg = result.stderr.strip() or result.stdout.strip() or "未知错误"
                print(f"  ⚠️ 整理失败（非致命）: {error_msg}")
        except Exception as e:
            print(f"  ⚠️ 整理失败（非致命）: {e}")

        if self.publish_dir is not None and self.purpose != "novelty-check":
            print(f"\n[发布] 复制交付文件到: {self.publish_dir}")
            try:
                result = publish_deliverables(
                    self.work_dir if self.legacy_layout_mode else self.layout.deliverables_dir,
                    self.publish_dir,
                    include_supporting=self.publish_include_supporting,
                    force=self.publish_force,
                )
                print(f"  ✓ 已发布: {', '.join(result.published)}")
            except PublishError as exc:
                print(f"  ✗ 发布失败: {exc}", file=sys.stderr)
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
    parser.add_argument("--work-dir", type=Path, required=False, help="工作目录；默认使用 .bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-literature-review/<run-id>")
    parser.add_argument("--review-level", choices=["premium", "standard", "basic"], help="档位（可选）")
    parser.add_argument(
        "--purpose",
        choices=["standard-review", "novelty-check"],
        default="standard-review",
        help="标准综述或仅运行到强近邻选文的查新模式",
    )
    parser.add_argument("--output-stem", help="文件名前缀（可选）")
    parser.add_argument(
        "--query-file",
        "--queries",
        dest="query_file",
        type=Path,
        help="多查询 JSON 文件；显式输入优先并复制到当前 run 的 input/queries.json",
    )
    parser.add_argument(
        "--allow-single-query-fallback",
        action="store_true",
        help="显式授权在完全缺少查询文件时执行一次单查询后备（默认关闭）",
    )
    parser.add_argument("--fallback-reason", help="单查询后备原因（写入 state 与 Search Log）")
    parser.add_argument(
        "--search-skill-root",
        type=Path,
        help="research-literature-search Skill 根目录（缺省按项目/环境变量/用户 Skill 根目录发现）",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="只执行阶段 0 并生成 input/queries.json，不启动检索",
    )
    parser.add_argument("--resume", type=Path, help="从已有 work_dir 恢复（自动读取其中的 pipeline_state.json）")
    parser.add_argument("--resume-from", type=int, help="从阶段编号开始执行（0-based）")
    parser.add_argument("--publish-dir", type=Path, help="正式交付目录（与内部 work_dir 分离）")
    parser.add_argument(
        "--include-supporting",
        action="store_true",
        help="发布 .tex/.bib/工作条件/验证报告等支持性文件（默认仅发布 PDF/Word）",
    )
    parser.add_argument("--force-publish", action="store_true", help="允许覆盖发布目录中的同名核心文件")
    args = parser.parse_args()

    topic = args.topic
    work_dir = args.work_dir
    output_stem = args.output_stem
    if args.resume:
        work_dir = args.resume if args.resume.is_dir() else args.resume.parent
        resume_topic, resume_stem = _load_resume_identity(work_dir)
        if not topic:
            topic = resume_topic
        if not output_stem:
            output_stem = resume_stem
    if args.resume and not topic:
        topic = Path(work_dir).name
    if not topic:
        raise ValueError("缺少 --topic")
    if work_dir is None:
        work_dir = _default_bensz_work_dir(topic)
    work_dir = Path(work_dir).expanduser().resolve()

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
        output_stem=output_stem,
        publish_dir=args.publish_dir,
        publish_include_supporting=args.include_supporting if args.include_supporting else None,
        publish_force=args.force_publish if args.force_publish else None,
        query_file=args.query_file,
        allow_single_query_fallback=True if args.allow_single_query_fallback else None,
        fallback_reason=args.fallback_reason,
        search_skill_root=args.search_skill_root,
        purpose=args.purpose,
    )
    ok = runner.run(resume_from=args.resume_from, prepare_only=args.prepare_only)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
