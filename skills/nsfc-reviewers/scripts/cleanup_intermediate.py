#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
import time
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


def _rm_tree(p: Path, *, apply: bool) -> None:
    if not p.exists():
        return
    if apply:
        shutil.rmtree(p)


def _rm_file(p: Path, *, apply: bool) -> None:
    if not p.exists():
        return
    if apply:
        p.unlink()


def _pr(msg: str) -> None:
    print(msg)


def main(argv: list[str] | None = None) -> int:
    skill_root = Path(__file__).resolve().parents[1]
    cfg_path = skill_root / "config.yaml"
    if not cfg_path.exists():
        print(f"error: missing config.yaml at {cfg_path}", file=sys.stderr)
        return 2
    cfg = _load_yaml(cfg_path)

    p = argparse.ArgumentParser(prog="cleanup_intermediate.py")
    p.add_argument("--review-path", required=True, help="评审会话目录（通常是标书目录或 review session 根目录）")
    p.add_argument(
        "--intermediate-dir",
        default="",
        help="覆盖 config.yaml:output_settings.intermediate_dir（默认 .nsfc-reviewers）",
    )
    p.add_argument(
        "--logs-max-age-days",
        type=int,
        default=0,
        help="覆盖 config.yaml:maintenance.cleanup.logs_max_age_days；仅清理 logs/ 下非 plans 的旧文件",
    )
    p.add_argument(
        "--delete-parallel-vibe",
        action="store_true",
        help="删除 intermediate_dir 下的 parallel-vibe/ 与 .parallel_vibe/（以及 review 根目录的 legacy .parallel_vibe/，若存在）",
    )
    p.add_argument(
        "--delete-snapshot",
        action="store_true",
        help="删除 intermediate_dir 下的 snapshot/（默认保留以便追溯）",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="实际执行删除操作（默认仅输出将要执行的动作）",
    )
    args = p.parse_args(argv)

    review_root = Path(str(args.review_path)).expanduser().resolve()
    if not review_root.exists() or not review_root.is_dir():
        print(f"error: review path is not a directory: {review_root}", file=sys.stderr)
        return 2

    os_cfg = cfg.get("output_settings") if isinstance(cfg, dict) else None
    os_cfg = os_cfg if isinstance(os_cfg, dict) else {}
    intermediate_dir_name = str(args.intermediate_dir or os_cfg.get("intermediate_dir") or ".nsfc-reviewers").strip()
    if not intermediate_dir_name:
        print("error: intermediate_dir is empty", file=sys.stderr)
        return 2
    p_intermediate = Path(intermediate_dir_name)
    if p_intermediate.is_absolute() or ".." in p_intermediate.parts:
        print(f"error: intermediate_dir must be a relative name without '..': {intermediate_dir_name!r}", file=sys.stderr)
        return 2
    if len(p_intermediate.parts) != 1:
        print(f"error: intermediate_dir should be a single directory name (no slashes): {intermediate_dir_name!r}", file=sys.stderr)
        return 2

    intermediate_root = (review_root / intermediate_dir_name).resolve()
    if not _within(review_root, intermediate_root):
        print(
            f"error: intermediate_dir escapes review root: review_root={review_root} intermediate_root={intermediate_root}",
            file=sys.stderr,
        )
        return 2

    m_cfg = cfg.get("maintenance") if isinstance(cfg, dict) else None
    m_cfg = m_cfg if isinstance(m_cfg, dict) else {}
    c_cfg = m_cfg.get("cleanup") if isinstance(m_cfg, dict) else None
    c_cfg = c_cfg if isinstance(c_cfg, dict) else {}
    logs_max_age_days = int(args.logs_max_age_days or c_cfg.get("logs_max_age_days") or 14)
    keep_plans = bool(c_cfg.get("keep_plans", True))

    apply = bool(args.apply)
    mode = "APPLY" if apply else "DRY-RUN"
    _pr(f"[cleanup_intermediate] mode={mode}")
    _pr(f"[cleanup_intermediate] review_root={review_root}")
    _pr(f"[cleanup_intermediate] intermediate_root={intermediate_root}")

    if not intermediate_root.exists():
        _pr(f"[cleanup_intermediate] skip: intermediate_root not found: {intermediate_root}")
        return 0

    # 1) parallel-vibe environment cleanup (optional)
    if args.delete_parallel_vibe:
        candidates = [
            intermediate_root / "parallel-vibe",
            intermediate_root / ".parallel_vibe",
            review_root / ".parallel_vibe",
        ]
        for d in candidates:
            if not d.exists():
                continue
            if not _within(review_root, d):
                print(f"error: refusing to delete outside review_root: {d}", file=sys.stderr)
                return 2
            _pr(f"[cleanup_intermediate] delete dir: {d}")
            _rm_tree(d, apply=apply)

    # 2) logs cleanup (age-based, keep logs/plans by default)
    logs_dir = intermediate_root / "logs"
    plans_dir = logs_dir / "plans"
    if logs_dir.exists():
        cutoff = time.time() - (max(0, logs_max_age_days) * 86400)
        _pr(f"[cleanup_intermediate] logs_max_age_days={logs_max_age_days} cutoff_epoch={int(cutoff)} keep_plans={keep_plans}")

        to_delete: list[Path] = []
        for f in logs_dir.rglob("*"):
            if not f.is_file():
                continue
            if keep_plans and plans_dir.exists():
                try:
                    f.resolve().relative_to(plans_dir.resolve())
                    continue
                except Exception:
                    pass
            try:
                st = f.stat()
            except Exception:
                continue
            if st.st_mtime < cutoff:
                to_delete.append(f)

        for f in sorted(to_delete):
            if not _within(review_root, f):
                print(f"error: refusing to delete outside review_root: {f}", file=sys.stderr)
                return 2
            _pr(f"[cleanup_intermediate] delete file: {f}")
            _rm_file(f, apply=apply)

    # 3) snapshot cleanup (optional)
    snapshot_dir = intermediate_root / "snapshot"
    if args.delete_snapshot and snapshot_dir.exists():
        if not _within(review_root, snapshot_dir):
            print(f"error: refusing to delete outside review_root: {snapshot_dir}", file=sys.stderr)
            return 2
        _pr(f"[cleanup_intermediate] delete dir: {snapshot_dir}")
        _rm_tree(snapshot_dir, apply=apply)

    _pr("[cleanup_intermediate] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
