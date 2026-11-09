#!/usr/bin/env python3
"""发布完整综述文稿；仅复制声明文件及 TeX 显式引用的本地资源。"""
from __future__ import annotations

import fnmatch
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from compile_latex_with_bibtex import bind_bundled_bst, find_bst_file


class PublishError(RuntimeError):
    """文稿不完整、依赖越界或存在覆盖风险。"""


@dataclass(frozen=True)
class PublishResult:
    published: list[str]


CORE_PATTERNS = ("*_review.pdf", "*_review.docx")
SUPPORTING_PATTERNS = ("*_review.tex", "*_参考文献.bib", "*_工作条件.md", "*_验证报告.md")
RESOURCE_SUFFIXES = {".tex", ".bib", ".bst", ".sty", ".cls", ".png", ".jpg", ".jpeg", ".pdf", ".eps"}
BUNDLED_RESOURCES = Path(__file__).resolve().parents[1] / "references/latex-template"


def _allowed(name: str, include_supporting: bool) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in CORE_PATTERNS + (SUPPORTING_PATTERNS if include_supporting else ()))


def _safe_file(path: Path, root: Path) -> Path:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise PublishError(f"资源越界：{path.name}") from exc
    if ".." in relative.parts or any((root / Path(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
        raise PublishError(f"不接受越界或符号链接资源：{relative}")
    if not path.is_file() or path.stat().st_size == 0:
        raise PublishError(f"缺少或为空的交付资源：{relative}")
    return path


def collect_tex_resources(tex_file: Path, root: Path) -> dict[str, Path]:
    """收集静态相对依赖；动态宏路径须先具体化，不猜测路径。"""
    files: dict[str, Path] = {}
    pending = [tex_file]
    graphics_dirs = [root]

    def add(raw: str, suffixes: tuple[str, ...], *, graphic=False, style=False):
        raw = raw.strip()
        rel = Path(raw)
        if style:
            # 内置样式只读引用宿主机；绝对路径仅允许指向 Skill 自带的 BST。
            bst_path = rel if rel.suffix == ".bst" else Path(raw + ".bst")
            if bst_path.is_absolute():
                if bst_path.parent != BUNDLED_RESOURCES or bst_path.is_symlink():
                    raise PublishError("外部 BST 仅允许引用当前 Skill 内置样式")
                _safe_file(bst_path, BUNDLED_RESOURCES)
                return
        if not raw or rel.is_absolute() or ".." in rel.parts or any(c in raw for c in "\\#$~{}"):
            raise PublishError(f"依赖必须使用静态相对路径：{raw}")
        choices = [directory / raw for directory in (graphics_dirs if graphic else [root])]
        candidates = [p if p.suffix else p.with_suffix(suffix) for p in choices for suffix in (suffixes if not p.suffix else ("",))]
        found = next((p for p in candidates if p.is_file() or p.is_symlink()), None)
        if found is None and style:
            bst_name = raw if rel.suffix == ".bst" else raw + ".bst"
            found = find_bst_file(bst_name, [BUNDLED_RESOURCES], root)
            if found is None:
                raise PublishError(f"缺少 TeX 依赖：{raw}")
            _safe_file(found, found.parent)
            return  # 系统样式由 TeX 发行版提供，不复制到成品。
        elif found is not None:
            _safe_file(found, root)
            destination = found.relative_to(root).as_posix()
        else:
            raise PublishError(f"缺少 TeX 依赖：{raw}")
        if found.suffix.lower() not in RESOURCE_SUFFIXES:
            raise PublishError(f"不支持的文稿资源类型：{raw}")
        if destination not in files:
            files[destination] = found
            if found.suffix in {".tex", ".sty", ".cls"}:
                pending.append(found)

    _safe_file(tex_file, root)
    files[tex_file.relative_to(root).as_posix()] = tex_file
    visited = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        tex = re.sub(r"(?<!\\)%[^\n]*", "", bind_bundled_bst(path.read_text(encoding="utf-8")))
        for group in re.findall(r"\\graphicspath\s*\{((?:\s*\{[^{}]*\}\s*)+)\}", tex):
            for raw in re.findall(r"\{([^{}]+)\}", group):
                rel = Path(raw)
                if rel.is_absolute() or ".." in rel.parts or "\\" in raw:
                    raise PublishError("graphicspath 必须在支持文件目录内")
                graphics_dirs.append(root / rel)
        for match in re.finditer(r"\\(input|include|includegraphics\*?|bibliography|bibliographystyle)\s*(?:\[[^\]]*\]\s*)?\{([^{}]+)\}", tex):
            command, raw = match.groups()
            if command in {"input", "include"}:
                add(raw, (".tex",))
            elif command.startswith("includegraphics"):
                add(raw, (".pdf", ".png", ".jpg", ".jpeg", ".eps"), graphic=True)
            elif command == "bibliography":
                for name in raw.split(","):
                    add(name, (".bib",))
            else:
                add(raw, (".bst",), style=True)
        # 本地自定义样式随稿带走；系统 TeX 包仍由发行版提供。
        for command, raw in re.findall(r"\\(usepackage|RequirePackage|documentclass|LoadClass)\s*(?:\[[^\]]*\]\s*)?\{([^{}]+)\}", tex):
            for name in raw.split(","):
                suffix = ".sty" if command in {"usepackage", "RequirePackage"} else ".cls"
                if (root / (name.strip() + suffix)).exists():
                    add(name, (suffix,))
    return files


def publish_deliverables(source_dir: Path, publish_dir: Path, *, include_supporting: bool = False, force: bool = False) -> PublishResult:
    # Python 调用保留轻量默认；标准 runner 通过配置开启完整文稿包。
    if Path(source_dir).is_symlink() or Path(publish_dir).is_symlink():
        raise PublishError("源目录与发布目录不能是符号链接")
    source = Path(source_dir).expanduser().resolve()
    target = Path(publish_dir).expanduser().resolve()
    if not source.is_dir():
        raise PublishError("交付源目录不存在")
    if target == source or source in target.parents or target in source.parents:
        raise PublishError("发布目录与交付源必须相互独立")
    candidates: dict[str, Path] = {}
    core = [p for p in source.iterdir() if _allowed(p.name, False)]
    stems = {p.name.rsplit("_review.", 1)[0] for p in core}
    if not stems:
        raise PublishError("没有 PDF/Word 交付物")
    for stem in sorted(stems):
        for suffix in ("pdf", "docx"):
            path = source / f"{stem}_review.{suffix}"
            candidates[path.name] = _safe_file(path, source)
    support = source / "supporting"
    if support.is_symlink() or (support.exists() and not support.is_dir()):
        raise PublishError("supporting 必须是非符号链接目录")
    # 显式 legacy resume 的源文件仍在交付源根部，不迁移历史文件。
    support_root = support if support.is_dir() else source
    if include_supporting:
        for stem in sorted(stems):
            for suffix in ("review.tex", "参考文献.bib", "工作条件.md", "验证报告.md"):
                path = support_root / f"{stem}_{suffix}"
                candidates[path.name] = _safe_file(path, support_root)
            for name, path in collect_tex_resources(support_root / f"{stem}_review.tex", support_root).items():
                if name in candidates and candidates[name] != path:
                    raise PublishError(f"交付资源重名：{name}")
                candidates[name] = path
    # 主目录只允许交付物；supporting 内草稿不发布，只有实际依赖进入集合。
    allowed_roots = {Path(name).parts[0] for name in candidates}
    unexpected = [p.name for p in source.iterdir() if p.name != "supporting" and p.name not in allowed_roots
                  and not (source == support_root and _allowed(p.name, True))]
    if unexpected:
        raise PublishError("交付源含非交付材料：" + ", ".join(sorted(unexpected)))
    if target.exists() and not target.is_dir():
        raise PublishError("发布目标不是目录")
    if target.exists():
        for path in target.rglob("*"):
            name = path.relative_to(target).as_posix()
            if path.is_symlink() or (path.is_file() and name not in candidates):
                raise PublishError(f"发布目录含未授权文件：{name}")
    for name in candidates:
        destination = target / name
        if destination.exists() and (not destination.is_file() or not force):
            raise PublishError(f"发布目标已存在，拒绝覆盖：{name}")
        if any(p.exists() and not p.is_dir() for p in destination.parents if p != target.parent):
            raise PublishError(f"发布路径被文件占用：{name}")
        temporary = destination.with_name(f".{destination.name}.tmp")
        if temporary.exists() or temporary.is_symlink():
            raise PublishError(f"临时发布文件已存在：{temporary.name}")
    # 全部静态检查完成后才写入；单文件原子替换，不声明多文件事务保证。
    target.mkdir(parents=True, exist_ok=True)
    for name, path in sorted(candidates.items()):
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        created = False
        try:
            with temporary.open("xb") as handle, path.open("rb") as original:
                created = True
                if path.suffix == ".tex":
                    handle.write(bind_bundled_bst(original.read().decode("utf-8")).encode("utf-8"))
                else:
                    shutil.copyfileobj(original, handle)
            temporary.replace(destination)
        finally:
            if created and temporary.exists():
                temporary.unlink()
    return PublishResult(published=sorted(candidates))
