#!/usr/bin/env python3
"""
runtime_utils.py - check-review-alignment 的确定性运行时工具

原则：
- 不调用任何 LLM API
- 只做路径解析 / 配置加载 / 依赖定位 / 文件发现等确定性工作
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def merge_dict(base: dict, override: dict) -> dict:
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = merge_dict(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_config(config_path: Path) -> Tuple[dict, List[str]]:
    """读取 config.yaml；缺依赖时降级到默认值。"""
    default_cfg: Dict[str, Any] = {
        "citation_commands": ["cite", "citep", "citet", "citealp", "citeauthor", "Cite", "Citet"],
        "pdf": {"enabled": True, "max_pages": 2},
        "render": {"use_skill": "systematic-literature-review", "overwrite": True},
        "ai": {
            "input_limits": {"max_abstract_chars": 2000, "max_pdf_excerpt_chars": 3000},
            "modification": {
                "auto_apply": False,
                "preserve_citations": True,
                "max_edits_per_sentence": 3,
                # 默认策略：只修复致命性错误（P0），P1 仅警告，P2 跳过
                "error_priority": [
                    {"type": "fake_citation", "action": "must_fix", "description": "missing in .bib or wrong bibkey"},
                    {"type": "wrong_citation", "action": "must_fix", "description": "bibkey does not match the claim"},
                    {"type": "contradictory_citation", "action": "must_fix", "description": "claim contradicts the paper"},
                    {"type": "weak_support", "action": "warn_only", "description": "paper only weakly supports the claim"},
                    {"type": "overclaim", "action": "warn_only", "description": "claim strength is overstated"},
                    {"type": "style_issue", "action": "skip", "description": "style / wording only"},
                ],
                "non_fatal_handling": "skip",
            },
            # 默认禁用段落优化：该技能只做“致命性引用错误修复”，避免文体改写
            "paragraph_optimization": {"enabled": False, "after_all_citations": False},
        },
    }
    warnings: List[str] = []

    if not config_path.exists():
        warnings.append("config.yaml 不存在，使用默认配置")
        return default_cfg, warnings

    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return merge_dict(default_cfg, loaded), warnings
        warnings.append("config.yaml 解析结果非 dict，使用默认配置")
    except ImportError:
        warnings.append("缺少 PyYAML，无法读取 config.yaml，使用默认配置")
    except Exception as e:
        warnings.append(f"读取 config.yaml 失败，使用默认配置: {e}")

    return default_cfg, warnings


def find_tex_and_bib(
    work_dir: Path, tex_arg: Optional[str], warnings: Optional[List[str]] = None
) -> Tuple[Path, Path]:
    """在 work_dir 内定位 review.tex 与对应的 .bib。"""
    tex_path: Optional[Path] = None
    bib_path: Optional[Path] = None

    if tex_arg:
        # 安全与可预期性：--tex 只允许文件名（不允许路径），避免路径遍历/误读其他目录文件。
        raw = Path(tex_arg)
        if raw.is_absolute() or raw.name != tex_arg:
            raise SystemExit("❌ 无效参数：--tex 只允许传入 tex 文件名（不支持路径）")

        name = raw.name
        if not name.lower().endswith(".tex"):
            if raw.suffix == "":
                name = f"{name}.tex"
            else:
                raise SystemExit("❌ 无效参数：--tex 必须是 .tex 文件名（不支持路径）")

        candidate = work_dir / name
        if candidate.exists():
            tex_path = candidate
    else:
        review_candidates = sorted(work_dir.glob("*_review.tex"))
        if review_candidates:
            if warnings is not None and len(review_candidates) > 1:
                names = ", ".join(p.name for p in review_candidates)
                warnings.append(f"work_dir 内存在多个 *_review.tex，默认选择第一个（按文件名排序）：{names}")
            tex_path = review_candidates[0]
        else:
            tex_candidates = sorted(work_dir.glob("*.tex"))
            if tex_candidates:
                if warnings is not None and len(tex_candidates) > 1:
                    names = ", ".join(p.name for p in tex_candidates)
                    warnings.append(f"work_dir 内存在多个 *.tex，默认选择第一个（按文件名排序）：{names}")
                tex_path = tex_candidates[0]

    if tex_path:
        # 常见命名：topic_review.tex -> topic_review.bib（同名）或 topic.bib（去掉 _review）
        candidates: List[Path] = []
        candidates.append(tex_path.with_suffix(".bib"))
        stem = tex_path.stem
        if stem.endswith("_review") and len(stem) > len("_review"):
            candidates.append((work_dir / f"{stem[:-len('_review')]}.bib"))

        for c in candidates:
            if c.exists():
                bib_path = c
                break

        if bib_path is None:
            for p in sorted(work_dir.glob("*.bib")):
                bib_path = p
                break

    if not tex_path or not bib_path:
        missing: List[str] = []
        if not tex_path:
            missing.append("tex")
        if not bib_path:
            missing.append("bib")
        raise FileNotFoundError(f"找不到所需文件: {', '.join(missing)} (work_dir={work_dir})")

    return tex_path, bib_path


def resolve_skill_root(skill_name: str) -> Optional[Path]:
    """尝试定位某个已安装的 skill 根目录。"""
    # 1) 显式指定（最强）
    env_key = f"{skill_name.upper().replace('-', '_')}_SKILL_DIR"
    if os.environ.get(env_key):
        p = Path(os.environ[env_key]).expanduser()
        if p.is_dir():
            return p

    # 2) 同仓库相邻目录（开发时）
    here = Path(__file__).resolve()
    skill_root = here.parents[1]  # {skill}/scripts/ -> {skill}/
    sibling = (skill_root.parent / skill_name).resolve()
    if sibling.is_dir():
        return sibling

    # 3) 常见安装目录
    home = Path.home()
    candidates = [
        home / ".codex" / "skills" / skill_name,
        home / ".claude" / "skills" / skill_name,
    ]

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        candidates.insert(0, Path(codex_home) / "skills" / skill_name)

    for c in candidates:
        if c.is_dir():
            return c

    return None


def require_dependency_skill(skill_name: str, reason: str) -> Path:
    """强制依赖检查：找不到则按约定提示并停止。"""
    root = resolve_skill_root(skill_name)
    if root is not None:
        return root
    # 计划要求的固定提示口径
    raise SystemExit(
        "❌ 缺少依赖：check-review-alignment 依赖 "
        f"{skill_name} skill 进行 {reason}。请先安装 {skill_name} skill。"
    )


def resolve_render_scripts(dep_skill_root: Path, dep_skill_name: str = "systematic-literature-review") -> Tuple[Path, Path]:
    """从依赖 skill 定位渲染脚本路径。"""
    compile_script = dep_skill_root / "scripts" / "compile_latex_with_bibtex.py"
    word_script = dep_skill_root / "scripts" / "convert_latex_to_word.py"
    if not compile_script.exists() or not word_script.exists():
        raise SystemExit(
            "❌ 缺少依赖：check-review-alignment 依赖 "
            f"{dep_skill_name} skill 进行 PDF/Word 渲染。请先安装 {dep_skill_name} skill。"
        )
    return compile_script, word_script


def python_executable() -> str:
    # 允许宿主用不同 python，但优先当前解释器
    return sys.executable or "python3"
