from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from utils import load_yaml, skill_root


@dataclass(frozen=True)
class TemplateInfo:
    id: str
    file: str
    family: str
    # Optional: a renderer-supported family used for stable fallback when `family` is conceptual-only.
    # Keep backward-compatible: when missing, renderer falls back to `family`.
    render_family: Optional[str]
    use_when: str
    avoid: str


@dataclass(frozen=True)
class TemplateDB:
    version: int
    families: Dict[str, Dict[str, Any]]
    templates: Dict[str, TemplateInfo]


_DB_CACHE: Optional[TemplateDB] = None


def _require_str(obj: Dict[str, Any], key: str, where: str) -> str:
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{where}.{key} 必须是非空字符串")
    return v.strip()


def load_template_db(root: Optional[Path] = None) -> TemplateDB:
    """
    Load template database from references/models/templates.yaml.

    This is intentionally lightweight: validation is strict enough to catch typos,
    but we do not over-model the token schema (keep forward-compatible).
    """
    global _DB_CACHE
    if _DB_CACHE is not None:
        return _DB_CACHE

    r = root if root is not None else skill_root()
    p = r / "references" / "models" / "templates.yaml"
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"未找到模板库：{p}")

    data = load_yaml(p)
    if not isinstance(data, dict):
        raise ValueError("templates.yaml 顶层必须是 mapping")

    version = data.get("version", 1)
    if not isinstance(version, int) or version <= 0:
        raise ValueError("templates.yaml:version 必须是正整数")

    families = data.get("families", {})
    if not isinstance(families, dict):
        raise ValueError("templates.yaml:families 必须是 mapping")

    templates_raw = data.get("templates", [])
    if not isinstance(templates_raw, list):
        raise ValueError("templates.yaml:templates 必须是 list")

    templates: Dict[str, TemplateInfo] = {}
    for i, t in enumerate(templates_raw, start=1):
        if not isinstance(t, dict):
            raise ValueError(f"templates.yaml:templates[{i}] 必须是 mapping")
        tid = _require_str(t, "id", f"templates[{i}]")
        file = _require_str(t, "file", f"templates[{i}]")
        fam = _require_str(t, "family", f"templates[{i}]")
        render_family = t.get("render_family")
        if render_family is not None:
            if not isinstance(render_family, str) or not render_family.strip():
                raise ValueError(f"templates[{i}].render_family 必须是非空字符串或省略")
            render_family = render_family.strip()
        use_when = str(t.get("use_when", "") or "").strip()
        avoid = str(t.get("avoid", "") or "").strip()
        if tid in templates:
            raise ValueError(f"模板 id 重复：{tid}")
        templates[tid] = TemplateInfo(
            id=tid,
            file=file,
            family=fam,
            render_family=render_family,  # type: ignore[arg-type]
            use_when=use_when,
            avoid=avoid,
        )

    _DB_CACHE = TemplateDB(version=version, families=families, templates=templates)
    return _DB_CACHE


def get_template(template_ref: str, root: Optional[Path] = None) -> Optional[TemplateInfo]:
    ref = str(template_ref or "").strip()
    if not ref:
        return None
    db = load_template_db(root=root)
    return db.templates.get(ref)


def resolve_layout_template(
    layout_template: Optional[str],
    template_ref: Optional[str],
    root: Optional[Path] = None,
) -> Tuple[str, Optional[TemplateInfo]]:
    """
    Resolve effective layout template.

    Precedence:
    - If template_ref is set and found in templates.yaml, use its family as the effective template.
    - Else use layout_template (if non-empty).
    - Else fallback to "classic".

    Special:
    - If layout_template == "auto" and template_ref is missing/unknown, fallback to "classic".
    """
    lt = (str(layout_template or "").strip() or "").lower()
    ref = str(template_ref or "").strip()

    tmpl = get_template(ref, root=root) if ref else None
    if tmpl is not None:
        # Renderer currently supports a stable subset. If a template uses a conceptual-only family,
        # it may provide `render_family` for stable fallback.
        effective = (tmpl.render_family or tmpl.family or "").strip().lower()
        if effective not in {"classic", "three-column", "layered-pipeline"}:
            effective = "classic"
        return effective, tmpl

    if not lt or lt == "auto":
        return "classic", None
    return lt, None
