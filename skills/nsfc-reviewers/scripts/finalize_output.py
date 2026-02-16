#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _load_yaml(p: Path) -> dict:
    try:
        obj = yaml.safe_load(_read_text(p)) or {}
    except Exception as e:
        raise ValueError(f"failed to read yaml: {p}: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError(f"expected yaml mapping: {p}")
    return obj


def _within(base: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def _pr(msg: str) -> None:
    print(msg)


def _warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def _err(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)


def _ensure_single_dir_name(name: str, *, label: str) -> str:
    n = str(name or "").strip()
    if not n:
        raise ValueError(f"{label} is empty")
    p = Path(n)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"{label} must be a relative name without '..': {n!r}")
    if len(p.parts) != 1:
        raise ValueError(f"{label} should be a single directory name (no slashes): {n!r}")
    return n


def _ensure_dir(p: Path, *, apply: bool) -> None:
    if p.exists():
        return
    _pr(f"[finalize_output] mkdir -p {p}")
    if apply:
        p.mkdir(parents=True, exist_ok=True)


def _move_children(src: Path, dest_dir: Path, *, apply: bool, review_root: Path) -> None:
    if not src.exists() or not src.is_dir():
        return
    if not _within(review_root, src):
        raise ValueError(f"refusing to move from outside review_root: {src}")

    for child in sorted(src.iterdir()):
        dest = dest_dir / child.name
        if dest.exists():
            _warn(f"skip move (dest exists): {child} -> {dest}")
            continue
        if not _within(review_root, dest):
            raise ValueError(f"refusing to move to outside review_root: {dest}")
        _pr(f"[finalize_output] move: {child} -> {dest}")
        if apply:
            shutil.move(str(child), str(dest))

    # Clean up the now-empty directory (best-effort).
    try:
        if apply:
            src.rmdir()
            _pr(f"[finalize_output] rmdir: {src}")
    except Exception:
        pass


def _stage_file(
    src: Path,
    dest: Path,
    *,
    apply: bool,
    review_root: Path,
    mode: str,
) -> None:
    if not src.exists() or not src.is_file():
        return
    if not _within(review_root, src):
        # Allow staging from outside review_root (copy-only), but still keep destination under review_root.
        if mode == "move":
            mode = "copy"
    if not _within(review_root, dest):
        raise ValueError(f"refusing to stage to outside review_root: {dest}")
    if dest.exists():
        _warn(f"skip {mode} (dest exists): {dest}")
        return

    dest.parent.mkdir(parents=True, exist_ok=True) if apply else None
    _pr(f"[finalize_output] {mode}: {src} -> {dest}")
    if not apply:
        return
    if mode == "move":
        shutil.move(str(src), str(dest))
    else:
        shutil.copy2(str(src), str(dest))


def _stage_dir(src: Path, dest_dir: Path, *, apply: bool, review_root: Path) -> None:
    if not src.exists() or not src.is_dir():
        return
    if not _within(review_root, src):
        raise ValueError(f"refusing to move dir from outside review_root: {src}")
    dest = dest_dir / src.name
    if dest.exists():
        _warn(f"skip move dir (dest exists): {src} -> {dest}")
        return
    if not _within(review_root, dest):
        raise ValueError(f"refusing to move dir to outside review_root: {dest}")
    _pr(f"[finalize_output] move dir: {src} -> {dest}")
    if apply:
        shutil.move(str(src), str(dest))


def _discover_parallel_vibe_roots(review_root: Path, intermediate_root: Path, extra: Path | None) -> list[Path]:
    roots: list[Path] = []
    candidates = [
        intermediate_root / ".parallel_vibe",
        review_root / ".parallel_vibe",
    ]
    if extra:
        if extra.is_dir() and extra.name == ".parallel_vibe":
            candidates.append(extra)
        elif extra.is_dir() and (extra / ".parallel_vibe").exists():
            candidates.append(extra / ".parallel_vibe")
        else:
            candidates.append(extra)
    for p in candidates:
        try:
            if p.exists() and p.is_dir() and p.name == ".parallel_vibe":
                roots.append(p)
        except Exception:
            continue
    # De-dup (resolve is best-effort; keep stable order).
    seen: set[str] = set()
    out: list[Path] = []
    for p in roots:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    skill_root = Path(__file__).resolve().parents[1]
    cfg_path = skill_root / "config.yaml"
    if not cfg_path.exists():
        _err(f"missing config.yaml at {cfg_path}")
        return 2
    try:
        cfg = _load_yaml(cfg_path)
    except Exception as e:
        _err(str(e))
        return 2

    os_cfg = cfg.get("output_settings") if isinstance(cfg, dict) else None
    os_cfg = os_cfg if isinstance(os_cfg, dict) else {}
    default_intermediate = str(os_cfg.get("intermediate_dir") or ".nsfc-reviewers")
    default_panel_dir = str(os_cfg.get("panel_dir") or "panels")
    default_filename = str(os_cfg.get("default_filename") or "comments-from-nsfc-reviewers.md")
    warn_missing_intermediate = bool(os_cfg.get("warn_missing_intermediate", True))
    cfg_validation_level = str(os_cfg.get("validation_level") or "warn").strip().lower()

    p = argparse.ArgumentParser(prog="finalize_output.py")
    p.add_argument("--review-path", required=True, help="标书目录 / 本次评审会话根目录（交付文件所在目录）")
    p.add_argument("--panel-count", type=int, default=1, help="本次评审组数（用于校验并行产物是否齐全）")
    p.add_argument(
        "--intermediate-dir",
        default=default_intermediate,
        help="覆盖 config.yaml:output_settings.intermediate_dir（默认 .nsfc-reviewers）",
    )
    p.add_argument(
        "--master-prompt-file",
        default="",
        help="可选：master prompt 文本文件路径；若提供则会归档到 logs/master_prompt.txt（优先 copy，必要时 move）",
    )
    p.add_argument(
        "--plan-file",
        default="",
        help="可选：plan.json 路径；若提供则会归档到 logs/plans/（优先 copy，必要时 move）",
    )
    p.add_argument(
        "--parallel-vibe-path",
        default="",
        help="可选：额外的 .parallel_vibe/ 位置（兼容 legacy 实例）；可指向 .parallel_vibe/ 或其父目录",
    )
    p.add_argument(
        "--validation-level",
        default="",
        help="覆盖 config.yaml:output_settings.validation_level（warn|error）",
    )
    p.add_argument("--apply", action="store_true", help="实际执行移动/复制（默认仅 DRY-RUN）")
    args = p.parse_args(argv)

    apply = bool(args.apply)
    mode = "APPLY" if apply else "DRY-RUN"
    review_root = Path(str(args.review_path)).expanduser().resolve()
    if not review_root.exists() or not review_root.is_dir():
        _err(f"review path is not a directory: {review_root}")
        return 2

    try:
        intermediate_dir_name = _ensure_single_dir_name(str(args.intermediate_dir), label="--intermediate-dir")
        panel_dir_name = _ensure_single_dir_name(default_panel_dir, label="config.yaml:output_settings.panel_dir")
    except Exception as e:
        _err(str(e))
        return 2

    validation_level = str(args.validation_level or cfg_validation_level or "warn").strip().lower()
    if validation_level not in {"warn", "error"}:
        _err("--validation-level must be warn|error")
        return 2

    intermediate_root = (review_root / intermediate_dir_name).resolve()
    if not _within(review_root, intermediate_root):
        _err(f"intermediate_dir escapes review root: review_root={review_root} intermediate_root={intermediate_root}")
        return 2

    _pr(f"[finalize_output] mode={mode}")
    _pr(f"[finalize_output] review_root={review_root}")
    _pr(f"[finalize_output] intermediate_root={intermediate_root}")

    # 1) Create the standard intermediate directory structure.
    _ensure_dir(intermediate_root / "parallel-vibe", apply=apply)
    _ensure_dir(intermediate_root / "logs" / "plans", apply=apply)
    _ensure_dir(intermediate_root / "snapshot", apply=apply)

    # 2) Move/collect parallel-vibe environment(s) into intermediate_root/parallel-vibe/
    extra_parallel = Path(str(args.parallel_vibe_path)).expanduser().resolve() if str(args.parallel_vibe_path).strip() else None
    pv_roots = _discover_parallel_vibe_roots(review_root, intermediate_root, extra_parallel)
    for src in pv_roots:
        _pr(f"[finalize_output] collect parallel-vibe env from: {src}")
        _move_children(src, intermediate_root / "parallel-vibe", apply=apply, review_root=review_root)

    # 3) Snapshot (legacy)
    _stage_dir(review_root / "proposal_snapshot", intermediate_root / "snapshot", apply=apply, review_root=review_root)

    # 4) Logs: master prompt + plan files
    # master prompt: prefer explicit, else legacy review_root/master_prompt.txt
    mp_src = Path(str(args.master_prompt_file)).expanduser().resolve() if str(args.master_prompt_file).strip() else None
    if not mp_src:
        mp_src = (review_root / "master_prompt.txt") if (review_root / "master_prompt.txt").exists() else None
    if mp_src:
        _stage_file(
            mp_src,
            intermediate_root / "logs" / "master_prompt.txt",
            apply=apply,
            review_root=review_root,
            mode="move",
        )

    # plan file: explicit single file + auto-discovery of review_root/plan*.json
    plan_src = Path(str(args.plan_file)).expanduser().resolve() if str(args.plan_file).strip() else None
    if plan_src and plan_src.exists():
        _stage_file(
            plan_src,
            intermediate_root / "logs" / "plans" / plan_src.name,
            apply=apply,
            review_root=review_root,
            mode="move",
        )
    for f in sorted(review_root.glob("plan*.json")):
        # Avoid double-staging an explicit plan file.
        if plan_src and f.resolve() == plan_src.resolve():
            continue
        _stage_file(
            f,
            intermediate_root / "logs" / "plans" / f.name,
            apply=apply,
            review_root=review_root,
            mode="move",
        )

    # 5) Validations (warn by default; error if configured).
    warnings: list[str] = []

    panel_count = int(args.panel_count or 1)
    pv_dest = intermediate_root / "parallel-vibe"
    has_parallel_env = pv_dest.exists() and any(pv_dest.iterdir())
    legacy_parallel_exists = (review_root / ".parallel_vibe").exists() or (intermediate_root / ".parallel_vibe").exists()
    any_parallel_seen = has_parallel_env or legacy_parallel_exists

    # In DRY-RUN, legacy .parallel_vibe is expected to remain; only warn when nothing is found at all.
    if panel_count > 1 and warn_missing_intermediate and (not any_parallel_seen):
        warnings.append(f"panel_count={panel_count} but no parallel-vibe env found (.parallel_vibe missing)")

    if warn_missing_intermediate:
        if not (intermediate_root / "logs").exists() and apply:
            warnings.append(f"missing logs dir after apply: {intermediate_root / 'logs'}")

    final_report = review_root / default_filename
    if not final_report.exists():
        warnings.append(f"final report not found (expected): {final_report}")

    panels_dir = review_root / panel_dir_name
    if panel_count > 1:
        if not panels_dir.exists():
            warnings.append(f"panels dir not found (expected): {panels_dir}")
        else:
            has_panel_files = any(p.name.startswith("G") and p.suffix.lower() == ".md" for p in panels_dir.iterdir() if p.is_file())
            if not has_panel_files:
                warnings.append(f"panels dir has no G*.md files: {panels_dir}")

    for w in warnings:
        _warn(w)

    if warnings and validation_level == "error":
        return 3

    _pr("[finalize_output] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
