#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


# Hard-coded per spec: ALL intermediates must live under this hidden dir in CWD.
WORK_DIR_NAME = ".paper-explain-figures"


@dataclass(frozen=True)
class FsEntryState:
    rel_path: str
    kind: str
    size: int
    mtime_ns: int


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _load_yaml_if_possible(path: Path) -> Optional[dict]:
    # Optional dependency: keep KISS; fall back to hardcoded defaults if PyYAML isn't available.
    try:
        import yaml  # type: ignore
    except Exception:
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return None


def _deep_merge_dict(dst: dict, src: dict) -> dict:
    for k, v in (src or {}).items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge_dict(dst[k], v)  # type: ignore[index]
        else:
            dst[k] = v
    return dst


def _default_config() -> dict:
    return {
        "defaults": {
            "execution": "serial",
            "max_parallel": 3,
            "sleep_between_starts_sec": 2.0,
            "timeout_seconds": 0,
            "runner_type": "codex",
            "runner_profile": "deep",
            "runner_model": "",
            "code_search_max_parent_depth": 2,
            "code_search_max_files": 2000,
            "code_search_max_file_bytes": 200000,
            "code_search_min_stem_len": 8,
            "code_search_exts": [".R", ".Rmd", ".qmd", ".py", ".ipynb", ".jl", ".m", ".tex", ".sh"],
        },
        "cli": {
            "codex": {
                "cmd": ["codex"],
                "global_args": ["--ask-for-approval", "never", "--sandbox", "workspace-write"],
                "exec_subcommand": ["exec"],
                "subcommand_args": [],
                "model_flag": "-m",
                "profile_args": {"default": [], "fast": ["-c", 'reasoning_effort="low"'], "deep": ["-c", 'reasoning_effort="medium"']},
            },
            "claude": {
                "cmd": ["claude"],
                "global_args": ["--dangerously-skip-permissions", "--no-session-persistence"],
                "print_subcommand": ["-p"],
                "subcommand_args": [],
                "model_flag": "--model",
                "profile_args": {"default": [], "fast": ["--effort", "low"], "deep": ["--effort", "medium"]},
            },
        },
        "models": {"codex": {"default": "", "fast": "", "deep": ""}, "claude": {"default": "", "fast": "", "deep": ""}},
    }


def load_config() -> dict:
    skill_root = Path(__file__).resolve().parents[1]
    cfg_path = skill_root / "config.yaml"
    cfg = _load_yaml_if_possible(cfg_path)
    if isinstance(cfg, dict):
        merged = _default_config()
        return _deep_merge_dict(merged, cfg)
    return _default_config()


def _require_within(base_dir: Path, target: Path) -> None:
    base = base_dir.resolve()
    tgt = target.resolve()
    try:
        tgt.relative_to(base)
    except Exception as e:
        raise ValueError(f"path escapes base_dir: base={base} target={tgt}") from e


def _build_runtime_env(runtime_root: Path, *, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    runtime_root = runtime_root.resolve()
    home_dir = runtime_root / "home"
    tmp_dir = runtime_root / "tmp"
    cache_dir = runtime_root / "xdg-cache"
    state_dir = runtime_root / "xdg-state"
    config_dir = runtime_root / "xdg-config"
    pycache_dir = runtime_root / "pycache"
    mplconfig_dir = runtime_root / "mplconfig"
    codex_home = runtime_root / "codex-home"

    for p in [home_dir, tmp_dir, cache_dir, state_dir, config_dir, pycache_dir, mplconfig_dir, codex_home]:
        p.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home_dir),
            "TMPDIR": str(tmp_dir),
            "TMP": str(tmp_dir),
            "TEMP": str(tmp_dir),
            "XDG_CACHE_HOME": str(cache_dir),
            "XDG_STATE_HOME": str(state_dir),
            "XDG_CONFIG_HOME": str(config_dir),
            "PYTHONPYCACHEPREFIX": str(pycache_dir),
            "MPLCONFIGDIR": str(mplconfig_dir),
            "CODEX_HOME": str(codex_home),
        }
    )
    if extra:
        env.update({str(k): str(v) for k, v in extra.items()})
    return env


def _snapshot_visible_tree(root: Path, *, allowed_root_names: Sequence[str]) -> Dict[str, FsEntryState]:
    root = root.resolve()
    allowed = {str(x).strip() for x in allowed_root_names if str(x).strip()}
    out: Dict[str, FsEntryState] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        cur_dir = Path(dirpath)
        rel_dir = cur_dir.relative_to(root)
        if rel_dir.parts and rel_dir.parts[0] in allowed:
            dirnames[:] = []
            continue

        pruned: List[str] = []
        for name in dirnames:
            rel = rel_dir / name if rel_dir != Path('.') else Path(name)
            if rel.parts and rel.parts[0] in allowed:
                continue
            st = (cur_dir / name).lstat()
            out[str(rel)] = FsEntryState(rel_path=str(rel), kind="dir", size=0, mtime_ns=int(st.st_mtime_ns))
            pruned.append(name)
        dirnames[:] = pruned

        for name in filenames:
            rel = rel_dir / name if rel_dir != Path('.') else Path(name)
            if rel.parts and rel.parts[0] in allowed:
                continue
            st = (cur_dir / name).lstat()
            kind = "symlink" if (cur_dir / name).is_symlink() else "file"
            out[str(rel)] = FsEntryState(rel_path=str(rel), kind=kind, size=int(st.st_size), mtime_ns=int(st.st_mtime_ns))

    return out


def _cleanup_new_paths(root: Path, rel_paths: Sequence[str]) -> List[str]:
    cleaned: List[str] = []
    for rel in sorted({str(x) for x in rel_paths if str(x).strip()}, key=lambda x: (x.count(os.sep), len(x)), reverse=True):
        p = (root / rel).resolve()
        if not p.exists() and not p.is_symlink():
            continue
        try:
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p)
            else:
                p.unlink()
            cleaned.append(rel)
        except Exception:
            continue
    return cleaned


def _allowed_output_relpaths(cwd: Path, out_md: Path) -> List[str]:
    rels: List[str] = []
    try:
        rel_out = out_md.resolve().relative_to(cwd.resolve())
    except Exception:
        return rels
    cur = Path()
    for part in rel_out.parts[:-1]:
        cur = cur / part
        rels.append(str(cur))
    rels.append(str(rel_out))
    return rels


def _audit_workspace_leaks(
    *,
    cwd: Path,
    before: Dict[str, FsEntryState],
    out_md: Path,
) -> Tuple[List[str], List[str], List[str]]:
    after = _snapshot_visible_tree(cwd, allowed_root_names=[WORK_DIR_NAME])
    allowed_rel = set(_allowed_output_relpaths(cwd, out_md))

    new_paths: List[str] = []
    changed_paths: List[str] = []
    for rel, state in after.items():
        if rel in allowed_rel:
            continue
        prev = before.get(rel)
        if prev is None:
            new_paths.append(rel)
            continue
        if prev.kind != state.kind:
            changed_paths.append(rel)
            continue
        if state.kind in {"file", "symlink"} and (prev.size != state.size or prev.mtime_ns != state.mtime_ns):
            changed_paths.append(rel)

    cleaned = _cleanup_new_paths(cwd, new_paths)
    return sorted(new_paths), sorted(cleaned), sorted(changed_paths)


def _sha1_short(s: str) -> str:
    h = hashlib.sha1(s.encode("utf-8")).hexdigest()
    return h[:10]


def _read_text(path: Path, *, max_bytes: int) -> str:
    try:
        data = path.read_bytes()
    except Exception:
        return ""
    if len(data) > max_bytes:
        data = data[:max_bytes]
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _redact_secrets(text: str) -> str:
    """
    Best-effort redaction before sending code snippets to an external model.
    Keep KISS: we only mask very common secret patterns to reduce accidental leakage.
    """
    if not text:
        return ""
    lines: List[str] = []

    # Common token/key patterns.
    re_sk = re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")
    re_akia = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
    re_keyval = re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*(.+)$")
    re_private_key = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")

    for ln in str(text).splitlines():
        if re_private_key.search(ln):
            lines.append("[REDACTED_PRIVATE_KEY_BLOCK]")
            continue
        ln2 = re_sk.sub("sk-<REDACTED>", ln)
        ln2 = re_akia.sub("<REDACTED_AWS_ACCESS_KEY_ID>", ln2)
        m = re_keyval.search(ln2)
        if m:
            # Preserve the key name to keep context, redact the value.
            lines.append(f"{m.group(1)}=<REDACTED>")
            continue
        lines.append(ln2)
    return "\n".join(lines)


def _is_probably_text_file(path: Path) -> bool:
    # Heuristic: avoid scanning binaries without relying on external libs.
    try:
        data = path.read_bytes()[:4096]
    except Exception:
        return False
    if not data:
        return False
    # NUL byte strongly suggests binary.
    if b"\x00" in data:
        return False
    return True


@dataclass(frozen=True)
class CodeHit:
    path: Path
    line_start: int
    line_end: int
    snippet: str
    score: float
    reason: str


def _candidate_search_roots(fig_path: Path, *, max_parent_depth: int) -> List[Path]:
    roots: List[Path] = []
    p = fig_path.parent
    roots.append(p)
    cur = p
    for _ in range(max(0, int(max_parent_depth or 0))):
        # Never scan filesystem root (too broad). Stop before reaching it.
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
        if cur.parent == cur:
            # cur is root; do not include it.
            break
        roots.append(cur)
    # Keep unique in order.
    seen: set[str] = set()
    out: List[Path] = []
    for r in roots:
        key = str(r.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def find_source_code_for_figure(
    fig_path: Path,
    *,
    explicit_code_paths: Sequence[Path],
    cfg_defaults: dict,
) -> Optional[CodeHit]:
    """
    Best-effort: search code near the figure path. If no reliable hit, return None.

    Strategy:
    1) If explicit_code_paths provided, scan them first.
    2) Otherwise, search within figure directory and up to N parents.
    3) Match by figure filename (strong) and stem (weak).
    """
    max_parent_depth = int(cfg_defaults.get("code_search_max_parent_depth", 2) or 2)
    max_files = int(cfg_defaults.get("code_search_max_files", 2000) or 2000)
    max_file_bytes = int(cfg_defaults.get("code_search_max_file_bytes", 200000) or 200000)
    min_stem_len = int(cfg_defaults.get("code_search_min_stem_len", 8) or 8)
    exts = [str(x) for x in (cfg_defaults.get("code_search_exts") or []) if str(x).strip()]
    exts_set = set([e.lower() for e in exts])

    fig_name = fig_path.name
    stem = fig_path.stem
    patterns = [fig_name]
    stem_norm = (stem or "").strip()
    stem_l = stem_norm.lower()
    stem_stop = {
        "plot",
        "figure",
        "fig",
        "image",
        "panel",
        "result",
        "results",
        "output",
        "tmp",
        "temp",
        "test",
    }
    use_stem = bool(stem_norm) and (len(stem_norm) >= min_stem_len) and (stem_l not in stem_stop)
    if use_stem:
        patterns.append(stem_norm)

    def scan_file(fp: Path) -> Optional[CodeHit]:
        if fp.suffix.lower() not in exts_set:
            return None
        if not fp.exists() or not fp.is_file():
            return None
        if not _is_probably_text_file(fp):
            return None

        txt = _read_text(fp, max_bytes=max_file_bytes)
        if not txt:
            return None
        score = 0.0
        reason_parts: List[str] = []
        # Strong match: filename with extension.
        n1 = txt.count(fig_name)
        if n1:
            score += 10.0 * n1
            reason_parts.append(f"match(filename)*{n1}")
        # Weak match: stem (only when sufficiently specific).
        if use_stem:
            n2 = txt.count(stem_norm)
            if n2:
                score += 2.0 * n2
                reason_parts.append(f"match(stem)*{n2}")
        if score <= 0:
            return None

        lines = txt.splitlines()
        hit_line = 0
        hit_pat = ""
        for i, line in enumerate(lines, 1):
            for pat in patterns:
                if pat and pat in line:
                    hit_line = i
                    hit_pat = pat
                    break
            if hit_line:
                break
        if not hit_line:
            hit_line = 1
        line_start = max(1, hit_line - 30)
        line_end = min(len(lines), hit_line + 30)
        snippet = _redact_secrets("\n".join(lines[line_start - 1 : line_end]))
        return CodeHit(
            path=fp,
            line_start=line_start,
            line_end=line_end,
            snippet=snippet,
            score=score,
            reason=";".join(reason_parts) + (f";first_hit={hit_pat}@L{hit_line}" if hit_pat else ""),
        )

    best: Optional[CodeHit] = None
    scanned = 0

    # 1) explicit paths first
    for p in explicit_code_paths:
        if scanned >= max_files:
            break
        scanned += 1
        hit = scan_file(p)
        if not hit:
            continue
        if (best is None) or (hit.score > best.score):
            best = hit

    # 2) nearby search
    roots = _candidate_search_roots(fig_path, max_parent_depth=max_parent_depth)
    ignore_dir_names = {
        WORK_DIR_NAME,
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
    for root in roots:
        if scanned >= max_files:
            break
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                if scanned >= max_files:
                    # Stop walking deeper once we've hit the scan cap.
                    dirnames[:] = []
                    break
                # Prune ignored directories.
                dirnames[:] = [d for d in dirnames if d not in ignore_dir_names and not d.startswith(".")]
                for fn in filenames:
                    if scanned >= max_files:
                        break
                    if fn.startswith("."):
                        continue
                    fp = Path(dirpath) / fn
                    if fp.suffix.lower() not in exts_set:
                        continue
                    scanned += 1
                    hit = scan_file(fp)
                    if not hit:
                        continue
                    # Prefer closer files slightly.
                    try:
                        dist = len(fp.resolve().parts) - len(fig_path.parent.resolve().parts)
                    except Exception:
                        dist = 0
                    hit_adj = CodeHit(
                        path=hit.path,
                        line_start=hit.line_start,
                        line_end=hit.line_end,
                        snippet=hit.snippet,
                        score=hit.score - max(0, float(dist)) * 0.1,
                        reason=hit.reason + f";dist={dist}",
                    )
                    if (best is None) or (hit_adj.score > best.score):
                        best = hit_adj
                if scanned >= max_files:
                    dirnames[:] = []
                    break
        except Exception:
            continue

    return best


def _which(cmd: str) -> Optional[str]:
    try:
        return shutil.which(cmd)
    except Exception:
        return None


def convert_figure_to_jpg(src: Path, dst: Path, *, runtime_root: Path) -> Tuple[bool, str]:
    """
    Convert src to dst as jpg (best-effort). Returns (ok, detail).
    Does NOT modify src.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    env = _build_runtime_env(runtime_root)
    ext = src.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        try:
            shutil.copy2(src, dst)
            return True, "copied(jpeg)"
        except Exception as e:
            return False, f"copy_failed: {type(e).__name__}: {e}"

    # Prefer macOS sips if available.
    if _which("sips"):
        try:
            # sips supports many raster formats; for PDFs behavior depends on system.
            r = subprocess.run(
                ["sips", "-s", "format", "jpeg", str(src), "--out", str(dst)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(dst.parent),
                env=env,
            )
            if r.returncode == 0 and dst.exists():
                return True, "sips"
            # fall through to other methods
        except Exception:
            pass

    # ImageMagick fallback.
    if _which("magick"):
        try:
            in_arg = str(src)
            if ext == ".pdf":
                in_arg = str(src) + "[0]"  # first page
            r = subprocess.run(
                ["magick", in_arg, "-quality", "92", str(dst)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(dst.parent),
                env=env,
            )
            if r.returncode == 0 and dst.exists():
                return True, "magick"
        except Exception:
            pass

    return False, "no_converter_available"


def _resolve_model_id(cfg: dict, *, runner_type: str, model: str, profile: str) -> str:
    m = str(model or "").strip()
    if m:
        return m
    rt = str(runner_type or "").strip().lower()
    prof = str(profile or "").strip() or "default"
    models = (cfg.get("models", {}) or {}).get(rt, {}) or {}
    return str(models.get(prof) or models.get("default") or "").strip()


def _resolve_profile_args(cfg: dict, *, runner_type: str, profile: str) -> List[str]:
    rt = str(runner_type or "").strip().lower()
    prof = str(profile or "").strip() or "default"
    c = (cfg.get("cli", {}) or {}).get(rt, {}) or {}
    profile_args = c.get("profile_args", {}) or {}
    pa = profile_args.get(prof, None)
    if pa is None:
        pa = profile_args.get("default", None)
    if isinstance(pa, list):
        return [str(x) for x in pa if str(x).strip()]
    return []


def _cmd_with_optional_model(
    *,
    base_cmd: Sequence[str],
    global_args: Sequence[str],
    model_flag: str,
    model: str,
    subcommand: Sequence[str],
    subcommand_args: Sequence[str],
    prompt_arg: str,
) -> List[str]:
    cmd: List[str] = list(base_cmd)
    cmd.extend(list(global_args))
    m = str(model or "").strip()
    if m:
        cmd.extend([model_flag, m])
    cmd.extend(list(subcommand))
    cmd.extend(list(subcommand_args))
    cmd.append(prompt_arg)
    return cmd


def _build_shell_cmd_from_template(template: str, prompt: str) -> List[str]:
    t = str(template or "")
    if not t.strip():
        raise ValueError("runner-cmd is empty")
    if "{prompt}" not in t:
        raise ValueError("runner-cmd must include a '{prompt}' placeholder")
    cmd_str = t.replace("{prompt}", shlex.quote(prompt))
    return shlex.split(cmd_str)


def build_runner_cmd(
    *,
    runner_type: str,
    prompt: str,
    profile: str,
    model: str,
    runner_args: Optional[Sequence[str]],
    runner_sub_args: Optional[Sequence[str]],
    runner_cmd_template: Optional[str],
    cfg: dict,
) -> List[str]:
    t = str(runner_type or "").strip().lower()
    extra = [str(x) for x in (runner_args or []) if str(x).strip()]
    sub_extra = [str(x) for x in (runner_sub_args or []) if str(x).strip()]

    if t == "codex":
        c = (cfg.get("cli", {}) or {}).get("codex", {}) or {}
        base_cmd = list(c.get("cmd") or ["codex"])
        sub = list(c.get("exec_subcommand") or ["exec"])
        model_flag = str(c.get("model_flag") or "-m")
        global_args = [str(x) for x in (c.get("global_args") or []) if str(x).strip()]
        global_args.extend(_resolve_profile_args(cfg, runner_type="codex", profile=profile))
        global_args.extend(extra)
        sub_args = [str(x) for x in (c.get("subcommand_args") or []) if str(x).strip()]
        sub_args.extend(sub_extra)
        return _cmd_with_optional_model(
            base_cmd=base_cmd,
            global_args=global_args,
            model_flag=model_flag,
            model=model,
            subcommand=sub,
            subcommand_args=sub_args,
            prompt_arg=prompt,
        )

    if t == "claude":
        c = (cfg.get("cli", {}) or {}).get("claude", {}) or {}
        base_cmd = list(c.get("cmd") or ["claude"])
        sub = list(c.get("print_subcommand") or ["-p"])
        model_flag = str(c.get("model_flag") or "--model")
        global_args = [str(x) for x in (c.get("global_args") or []) if str(x).strip()]
        global_args.extend(_resolve_profile_args(cfg, runner_type="claude", profile=profile))
        global_args.extend(extra)
        sub_args = [str(x) for x in (c.get("subcommand_args") or []) if str(x).strip()]
        sub_args.extend(sub_extra)
        return _cmd_with_optional_model(
            base_cmd=base_cmd,
            global_args=global_args,
            model_flag=model_flag,
            model=model,
            subcommand=sub,
            subcommand_args=sub_args,
            prompt_arg=prompt,
        )

    if t == "shell":
        if not runner_cmd_template:
            raise ValueError("runner_cmd_template is required for runner_type=shell")
        return _build_shell_cmd_from_template(runner_cmd_template, prompt)

    if t == "local":
        # Deterministic "fake" runner for offline tests.
        code = (
            "import json, pathlib, textwrap\n"
            "meta = {}\n"
            "try:\n"
            "  meta = json.loads(pathlib.Path('job.json').read_text(encoding='utf-8'))\n"
            "except Exception:\n"
            "  meta = {}\n"
            "title = meta.get('figure_title') or meta.get('orig_path') or 'LOCAL_RUNNER'\n"
            "orig = meta.get('orig_path') or '(unknown)'\n"
            "code_ref = meta.get('code_ref') or 'NULL'\n"
            "p = pathlib.Path('analysis.md')\n"
            "p.write_text(textwrap.dedent(f'''\\\n"
            "## Figure: {title}\n\n"
            "> 文件位置： {orig}\n"
            "> 源代码： {code_ref}\n\n"
            "### 图表核心含义\n\n"
            "本段由 local runner 生成，用于离线测试管线与合并逻辑（不依赖外部模型）。\n\n"
            "### 变量定义\n\n"
            "| 元素 | 定义 |\n"
            "| --- | --- |\n"
            "| (local) | (local) |\n\n"
            "### 解读要点\n\n"
            "1. (local)\n\n"
            "### 解释\n\n"
            "(local)\n\n"
            "### 科学价值\n\n"
            "(local)\n"
            "'''), encoding='utf-8')\n"
            "print('wrote', str(p))\n"
        )
        return [sys.executable, "-c", code]

    raise ValueError(f"unknown runner_type: {runner_type}")


def _render_worker_prompt(
    *,
    figure_title: str,
    report_orig_path: Path,
    workspace_orig_copy: Optional[Path],
    jpg_path: Optional[Path],
    jpg_status: str,
    user_notes: str,
    code_hit: Optional[CodeHit],
) -> str:
    code_block = ""
    code_ref = "NULL"
    if code_hit is not None:
        code_ref = f"{code_hit.path} 第{code_hit.line_start}-{code_hit.line_end}行"
        ext = code_hit.path.suffix.lower().lstrip(".") or "text"
        code_block = (
            "\n\n代码片段（只读，供你理解图的真实含义；不要修改任何代码）：\n\n"
            f"```{ext}\n{code_hit.snippet.rstrip()}\n```\n"
        )

    jpg_line = "NULL"
    if jpg_path is not None:
        # Prefer job-local relative paths to avoid runner sandbox read restrictions.
        try:
            jpg_line = str(jpg_path.relative_to(jpg_path.parent))
        except Exception:
            jpg_line = str(jpg_path)

    orig_copy_line = "NULL"
    if workspace_orig_copy is not None:
        try:
            orig_copy_line = str(workspace_orig_copy.relative_to(workspace_orig_copy.parent))
        except Exception:
            orig_copy_line = str(workspace_orig_copy)

    return textwrap.dedent(
        f"""\
        你是“论文 Figure 解读老师”。你的任务是教会人类如何读懂一张 figure，并输出结构化报告。

        强约束（必须遵守）：
        - 只读：严禁修改任何文件（包括 figure 原图、源代码、以及任何外部路径文件）。
        - 不要运行任何会写入外部目录的命令；如需落盘，仅允许写入当前工作目录（你运行在 job 目录中）。
        - 如果关键信息缺失（例如无法打开图片/找不到代码），请明确写在报告里，不要编造。

        输入信息：
        - Figure 原始文件（工作区副本，只读，优先读取）：{orig_copy_line}
        - Figure 转换后的 JPG（工作区文件，优先用于视觉理解）：{jpg_line}
        - JPG 状态：{jpg_status}
        - 用户人工解读（可能有误；主要用于推测用户关心点）：{user_notes.strip() if user_notes.strip() else "NULL"}
        - Figure 原始文件（用户路径，仅用于报告引用）：{report_orig_path}
        - 可能的源代码定位（仅供引用；无需再读取原文件，直接以“代码片段”为准）：{code_ref}
        {code_block.rstrip()}

        输出要求（非常重要）：
        - 只输出 Markdown（不要输出解释性前言）。
        - 必须以 `## Figure: ...` 开头，且只写这一张图的内容。
        - 必须包含这些小节（标题级别必须一致）：`### 图表核心含义`、`### 变量定义`（用表格）、`### 解读要点`（用 1.2.3. 列表）、`### 解释`、`### 科学价值`。
        - `> 文件位置： ...` 与 `> 源代码： ...` 两行必须存在；找不到源代码则写 `NULL`。

        请按模板输出（把 xxx 替换为你的内容）：

        ## Figure: {figure_title}

        > 文件位置： {report_orig_path}
        > 源代码： {code_ref}

        ### 图表核心含义

        （一句话概括这张图在回答什么“问题/机制/对比”，尽量具体）

        ### 变量定义

        | 元素 | 定义 |
        | --- | --- |
        | ... | ... |

        ### 解读要点

        1. ...
        2. ...
        3. ...

        ### 解释

        （写一段“像教人读图一样”的解释，体现你真的读懂了图；优先以源代码为准）

        ### 科学价值

        （这张图能支持什么结论/诊断/洞见；有哪些误读风险与注意事项）
        """
    ).strip() + "\n"


@dataclass(frozen=True)
class Job:
    job_id: str
    index: int
    orig_path: Path
    job_dir: Path
    prompt_txt: Path
    runner_log: Path
    analysis_md: Path
    meta_json: Path


def _safe_filename(s: str) -> str:
    out = []
    for ch in s:
        if ch.isalnum() or ch in ("-", "_", "."):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)[:120] or "figure"


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _write_text(path: Path, s: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding="utf-8")


def _read_text_maybe(path: Path, *, max_chars: int = 200_000) -> str:
    try:
        s = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if len(s) > max_chars:
        return s[:max_chars] + f"\n\n...(truncated, total_chars={len(s)})\n"
    return s


def _normalize_section_from_log(log_txt: str, *, fallback_title: str, orig_path: Path, code_ref: str) -> str:
    t = (log_txt or "").strip()
    if t.startswith("## Figure:"):
        return t + "\n"
    # Fallback: keep something readable and traceable.
    return textwrap.dedent(
        f"""\
        ## Figure: {fallback_title}

        > 文件位置： {orig_path}
        > 源代码： {code_ref}

        ### 图表核心含义

        （runner 未能按模板输出；以下为原始输出节选）

        ```text
        {t}
        ```

        ### 变量定义

        | 元素 | 定义 |
        | --- | --- |
        | (unknown) | (unknown) |

        ### 解读要点

        1. (unknown)

        ### 解释

        (unknown)

        ### 科学价值

        (unknown)
        """
    ).strip() + "\n"


def _start_job(
    job: Job,
    *,
    runner_type: str,
    runner_profile: str,
    runner_model: str,
    cfg: dict,
    env_extra: Dict[str, str],
    runner_cmd_template: Optional[str],
    runner_args: Optional[Sequence[str]],
    runner_sub_args: Optional[Sequence[str]],
) -> Tuple[subprocess.Popen, Any, dict]:
    prompt = _read_text_maybe(job.prompt_txt, max_chars=400_000)
    model_id = _resolve_model_id(cfg, runner_type=runner_type, model=runner_model, profile=runner_profile)
    cmd = build_runner_cmd(
        runner_type=runner_type,
        prompt=prompt,
        profile=runner_profile,
        model=model_id,
        runner_args=runner_args,
        runner_sub_args=runner_sub_args,
        runner_cmd_template=runner_cmd_template,
        cfg=cfg,
    )

    job.runner_log.parent.mkdir(parents=True, exist_ok=True)
    log_f = job.runner_log.open("w", encoding="utf-8")
    meta = {"job_id": job.job_id, "start_at": _now_iso(), "cmd": cmd}

    env = _build_runtime_env(job.job_dir / "_runtime", extra=env_extra)
    p = subprocess.Popen(
        cmd,
        cwd=str(job.job_dir),
        stdout=log_f,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    return p, log_f, meta


def _finish_job(
    job: Job,
    p: subprocess.Popen,
    log_f: Any,
    meta: dict,
    *,
    timeout_seconds: int,
    fallback_title: str,
    orig_path: Path,
    code_ref: str,
) -> dict:
    timeout_killed = False
    err = ""
    try:
        if timeout_seconds and timeout_seconds > 0:
            try:
                p.wait(timeout=float(timeout_seconds))
            except subprocess.TimeoutExpired:
                timeout_killed = True
                try:
                    p.kill()
                except Exception:
                    pass
                p.wait(timeout=3)
        else:
            p.wait()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    try:
        log_f.flush()
        log_f.close()
    except Exception:
        pass

    exit_code = int(p.returncode or 0)
    end_at = _now_iso()
    done = dict(meta)
    done.update({"end_at": end_at, "exit_code": exit_code})
    if timeout_killed and not err:
        done["exit_code"] = 124
        done["error"] = f"timeout after {timeout_seconds}s"
    elif err:
        done["error"] = err
        done["exit_code"] = 1

    # Prefer a runner-produced analysis.md if present (some runners may choose to write files).
    existing = _read_text_maybe(job.analysis_md, max_chars=240_000).strip()
    if existing.startswith("## Figure:"):
        section_md = existing + "\n"
    else:
        log_txt = _read_text_maybe(job.runner_log, max_chars=200_000)
        section_md = _normalize_section_from_log(
            log_txt,
            fallback_title=fallback_title,
            orig_path=orig_path,
            code_ref=code_ref,
        )
        _write_text(job.analysis_md, section_md)
    _write_json(job.meta_json, done)
    return done


def run_jobs(
    jobs: Sequence[Job],
    *,
    parallel: bool,
    max_parallel: int,
    sleep_between_starts_sec: float,
    timeout_seconds: int,
    runner_type: str,
    runner_profile: str,
    runner_model: str,
    cfg: dict,
    env_extra: Dict[str, str],
    runner_cmd_template: Optional[str],
    runner_args: Optional[Sequence[str]],
    runner_sub_args: Optional[Sequence[str]],
    fallback_titles: Dict[str, str],
    orig_paths: Dict[str, Path],
    code_refs: Dict[str, str],
) -> List[dict]:
    metas: List[dict] = []
    running: List[Tuple[Job, subprocess.Popen, Any, dict]] = []

    def start_one(j: Job) -> Tuple[subprocess.Popen, Any, dict]:
        if sleep_between_starts_sec and sleep_between_starts_sec > 0:
            try:
                import time

                time.sleep(float(sleep_between_starts_sec))
            except Exception:
                pass
        return _start_job(
            j,
            runner_type=runner_type,
            runner_profile=runner_profile,
            runner_model=runner_model,
            cfg=cfg,
            env_extra=env_extra,
            runner_cmd_template=runner_cmd_template,
            runner_args=runner_args,
            runner_sub_args=runner_sub_args,
        )

    if not parallel:
        for j in jobs:
            try:
                p, log_f, meta = start_one(j)
                metas.append(
                    _finish_job(
                        j,
                        p,
                        log_f,
                        meta,
                        timeout_seconds=timeout_seconds,
                        fallback_title=fallback_titles.get(j.job_id, "UNKNOWN"),
                        orig_path=orig_paths[j.job_id],
                        code_ref=code_refs.get(j.job_id, "NULL"),
                    )
                )
            except FileNotFoundError as e:
                metas.append({"job_id": j.job_id, "exit_code": 127, "error": f"FileNotFoundError: {e}", "start_at": _now_iso(), "end_at": _now_iso()})
            except Exception as e:
                metas.append({"job_id": j.job_id, "exit_code": 1, "error": f"{type(e).__name__}: {e}", "start_at": _now_iso(), "end_at": _now_iso()})
        return metas

    cap = max(1, int(max_parallel or 1))
    q = list(jobs)
    while q or running:
        while q and len(running) < cap:
            j = q.pop(0)
            try:
                p, log_f, meta = start_one(j)
                running.append((j, p, log_f, meta))
            except FileNotFoundError as e:
                metas.append({"job_id": j.job_id, "exit_code": 127, "error": f"FileNotFoundError: {e}", "start_at": _now_iso(), "end_at": _now_iso()})
            except Exception as e:
                metas.append({"job_id": j.job_id, "exit_code": 1, "error": f"{type(e).__name__}: {e}", "start_at": _now_iso(), "end_at": _now_iso()})

        still: List[Tuple[Job, subprocess.Popen, Any, dict]] = []
        progressed = False
        for j, p, log_f, meta in running:
            if p.poll() is None:
                still.append((j, p, log_f, meta))
                continue
            metas.append(
                _finish_job(
                    j,
                    p,
                    log_f,
                    meta,
                    timeout_seconds=timeout_seconds,
                    fallback_title=fallback_titles.get(j.job_id, "UNKNOWN"),
                    orig_path=orig_paths[j.job_id],
                    code_ref=code_refs.get(j.job_id, "NULL"),
                )
            )
            progressed = True
        running = still
        if not progressed:
            try:
                import time

                time.sleep(0.2)
            except Exception:
                pass

    return metas


def merge_sections(jobs: Sequence[Job], *, out_md: Path) -> None:
    parts: List[str] = ["# Figures", ""]
    for j in jobs:
        parts.append(_read_text_maybe(j.analysis_md, max_chars=240_000).rstrip())
        parts.append("")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")


def _parse_notes(args: argparse.Namespace) -> str:
    notes: List[str] = []
    for n in (args.note or []):
        if n is None:
            continue
        notes.append(str(n))
    if args.notes_file:
        try:
            notes.append(Path(args.notes_file).read_text(encoding="utf-8"))
        except Exception:
            pass
    return "\n\n".join([x.strip() for x in notes if x.strip()]).strip()


def main(argv: Optional[Sequence[str]] = None) -> int:
    cfg = load_config()
    defaults = cfg.get("defaults", {}) or {}

    p = argparse.ArgumentParser(description="Explain paper figures and produce a human-readable report.")
    p.add_argument("--fig", action="append", required=True, help="Figure 文件绝对路径（可重复）")
    p.add_argument("--note", action="append", default=[], help="可选：人工解读/关注点（可重复）")
    p.add_argument("--notes-file", default="", help="可选：人工解读文本文件（UTF-8）")
    p.add_argument("--code-path", action="append", default=[], help="可选：源代码文件绝对路径（可重复；作为候选入口）")

    p.add_argument("--out", default="paper-explain-figures_report.md", help="最终报告输出路径（相对当前目录或绝对路径）")

    p.add_argument("--runner", default=str(defaults.get("runner_type", "codex")), help="runner：codex|claude|local")
    p.add_argument("--profile", default=str(defaults.get("runner_profile", "deep")), help="profile：default|fast|deep")
    p.add_argument("--model", default=str(defaults.get("runner_model", "")), help="模型 ID（可选；为空使用 CLI 默认模型）")
    p.add_argument("--runner-cmd", default="", help="runner_type=shell 时的命令模板（必须包含 {prompt}）")
    p.add_argument("--runner-arg", action="append", default=[], help="runner 全局额外参数（可重复；放在子命令前）")
    p.add_argument("--runner-sub-arg", action="append", default=[], help="runner 子命令额外参数（可重复；放在子命令后、prompt 前）")

    p.add_argument("--parallel", action="store_true", help="并行运行（默认串行）")
    p.add_argument("--max-parallel", type=int, default=int(defaults.get("max_parallel", 3) or 3), help="并发上限（仅 --parallel 生效）")
    p.add_argument("--sleep-between-starts-sec", type=float, default=float(defaults.get("sleep_between_starts_sec", 2.0) or 2.0), help="启动间隔（秒）")
    p.add_argument("--timeout-seconds", type=int, default=int(defaults.get("timeout_seconds", 0) or 0), help="每张图超时（秒；0 表示不超时）")
    p.add_argument("--run-id", default="", help="可选：自定义 run_id（为空则自动生成）")

    args = p.parse_args(list(argv) if argv is not None else None)

    figs = [Path(x).expanduser() for x in (args.fig or [])]
    for fp in figs:
        if not fp.is_absolute():
            print(f"[ERROR] --fig 必须是绝对路径：{fp}", file=sys.stderr)
            return 2
        if not fp.exists():
            print(f"[ERROR] figure 不存在：{fp}", file=sys.stderr)
            return 2

    explicit_code_paths = [Path(x).expanduser() for x in (args.code_path or []) if str(x).strip()]
    for cp in explicit_code_paths:
        if not cp.is_absolute():
            print(f"[ERROR] --code-path 必须是绝对路径：{cp}", file=sys.stderr)
            return 2
        if not cp.exists():
            print(f"[ERROR] 源代码文件不存在：{cp}", file=sys.stderr)
            return 2
        if not cp.is_file():
            print(f"[ERROR] --code-path 不是文件：{cp}", file=sys.stderr)
            return 2
    user_notes = _parse_notes(args)

    cwd = Path.cwd()
    workspace_before = _snapshot_visible_tree(cwd, allowed_root_names=[WORK_DIR_NAME])

    # Spec intent: final report should be placed in the current workdir (not arbitrary absolute paths).
    out_md = Path(args.out).expanduser()
    if not out_md.is_absolute():
        out_md = (cwd / out_md).resolve()
    try:
        _require_within(cwd, out_md)
    except Exception:
        print(f"[ERROR] --out 必须位于当前工作目录内：cwd={cwd} out={out_md}", file=sys.stderr)
        return 2

    base = (cwd / WORK_DIR_NAME).resolve()
    base.mkdir(parents=True, exist_ok=True)

    if args.run_id.strip():
        run_id = _safe_filename(args.run_id.strip())
    else:
        # Stable enough, readable.
        run_id = _dt.datetime.now().strftime("run_%Y%m%d%H%M%S") + "_" + _sha1_short("|".join([str(x) for x in figs]))

    run_dir = (base / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    # Preflight runner availability early to fail-fast (except local runner).
    runner_type = str(args.runner or "").strip().lower()
    if runner_type == "shell":
        print("[ERROR] --runner shell 已禁用：它无法提供“除最终结果外所有中间文件均限制在 .paper-explain-figures/ 内”的严格保证。", file=sys.stderr)
        return 2
    if runner_type in {"codex", "claude"}:
        if not _which(runner_type):
            print(f"[ERROR] runner 不可用（未在 PATH 中找到）：{runner_type}", file=sys.stderr)
            return 2

    cfg_max_parallel = int(defaults.get("max_parallel", 3) or 3)
    requested_max_parallel = int(args.max_parallel)
    effective_max_parallel = requested_max_parallel
    if effective_max_parallel > cfg_max_parallel:
        print(f"[WARN] --max-parallel={requested_max_parallel} 超过 config.yaml 上限 {cfg_max_parallel}，已自动降为 {cfg_max_parallel}", file=sys.stderr)
        effective_max_parallel = cfg_max_parallel
    if effective_max_parallel < 1:
        effective_max_parallel = 1

    jobs: List[Job] = []
    fallback_titles: Dict[str, str] = {}
    orig_paths: Dict[str, Path] = {}
    code_refs: Dict[str, str] = {}

    for i, fig in enumerate(figs, 1):
        job_id = f"{i:03d}_" + _sha1_short(str(fig))
        title = fig.name
        job_dir = run_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        # Copy original into job dir to avoid runner sandbox read restrictions on absolute paths.
        # This never mutates the user's original file (copy2 preserves metadata best-effort).
        orig_copy = job_dir / f"figure_orig{fig.suffix.lower()}"
        try:
            shutil.copy2(fig, orig_copy)
        except Exception:
            orig_copy = None

        # Convert to jpg inside job dir.
        jpg_path = job_dir / "figure.jpg"
        ok, detail = convert_figure_to_jpg(fig, jpg_path, runtime_root=job_dir / "_runtime")
        if not ok:
            jpg_path = None
        jpg_status = "ok:" + detail if ok else "failed:" + detail

        # Find code hit (best-effort).
        code_hit = find_source_code_for_figure(fig, explicit_code_paths=explicit_code_paths, cfg_defaults=defaults)
        code_ref = "NULL"
        if code_hit is not None:
            code_ref = f"{code_hit.path} 第{code_hit.line_start}-{code_hit.line_end}行"

        prompt_txt = job_dir / "prompt.txt"
        runner_log = job_dir / "runner.log"
        analysis_md = job_dir / "analysis.md"
        meta_json = job_dir / "job_meta.json"

        prompt = _render_worker_prompt(
            figure_title=title,
            report_orig_path=fig,
            workspace_orig_copy=orig_copy,
            jpg_path=jpg_path,
            jpg_status=jpg_status,
            user_notes=user_notes,
            code_hit=code_hit,
        )
        _write_text(prompt_txt, prompt)

        job_meta = {
            "job_id": job_id,
            "index": i,
            "orig_path": str(fig),
            "figure_title": title,
            "jpg_path": str(jpg_path) if jpg_path is not None else "",
            "jpg_status": jpg_status,
            "code_path": str(code_hit.path) if code_hit is not None else "",
            "code_line_start": int(code_hit.line_start) if code_hit is not None else 0,
            "code_line_end": int(code_hit.line_end) if code_hit is not None else 0,
            "code_ref": code_ref,
            "workspace_orig_copy": str(orig_copy) if orig_copy is not None else "",
            "code_reason": str(code_hit.reason) if code_hit is not None else "",
            "created_at": _now_iso(),
        }
        _write_json(job_dir / "job.json", job_meta)
        if code_hit is not None:
            _write_text(job_dir / "code_snippet.txt", code_hit.snippet.rstrip() + "\n")

        j = Job(
            job_id=job_id,
            index=i,
            orig_path=fig,
            job_dir=job_dir,
            prompt_txt=prompt_txt,
            runner_log=runner_log,
            analysis_md=analysis_md,
            meta_json=meta_json,
        )
        jobs.append(j)
        fallback_titles[job_id] = title
        orig_paths[job_id] = fig
        code_refs[job_id] = code_ref

    run_meta = {
        "run_id": run_id,
        "created_at": _now_iso(),
        "cwd": str(cwd),
        "work_dir": str(base),
        "runner": {"type": args.runner, "profile": args.profile, "model": args.model},
        "execution": {
            "parallel": bool(args.parallel),
            "max_parallel": int(args.max_parallel),
            "effective_max_parallel": int(effective_max_parallel),
            "sleep_between_starts_sec": float(args.sleep_between_starts_sec),
        },
        "figures": [str(x) for x in figs],
        "explicit_code_paths": [str(x) for x in explicit_code_paths],
        "out": str(args.out),
    }
    _write_json(run_dir / "run.json", run_meta)

    # Allow config defaults to control execution unless user explicitly enables --parallel.
    parallel = bool(args.parallel) or (str(defaults.get("execution", "serial")).strip().lower() == "parallel")

    env_extra = {"EXPLAIN_FIGURES_RUN_ID": run_id}
    metas = run_jobs(
        jobs,
        parallel=parallel,
        max_parallel=int(effective_max_parallel),
        sleep_between_starts_sec=float(args.sleep_between_starts_sec),
        timeout_seconds=int(args.timeout_seconds),
        runner_type=str(args.runner),
        runner_profile=str(args.profile),
        runner_model=str(args.model),
        cfg=cfg,
        env_extra=env_extra,
        runner_cmd_template=str(args.runner_cmd) if str(args.runner_cmd).strip() else None,
        runner_args=list(args.runner_arg or []),
        runner_sub_args=list(args.runner_sub_arg or []),
        fallback_titles=fallback_titles,
        orig_paths=orig_paths,
        code_refs=code_refs,
    )
    _write_json(run_dir / "jobs_done.json", metas)
    merge_sections(jobs, out_md=out_md)

    leaked_new, cleaned_new, changed_existing = _audit_workspace_leaks(cwd=cwd, before=workspace_before, out_md=out_md)
    if leaked_new or changed_existing:
        if cleaned_new:
            print(f"[WARN] 已自动清理 .paper-explain-figures/ 外的新增中间文件：{', '.join(cleaned_new)}", file=sys.stderr)
        if changed_existing:
            print(f"[ERROR] 检测到工作目录中存在被修改的非授权路径：{', '.join(changed_existing)}", file=sys.stderr)
            return 1
        remaining = [p for p in leaked_new if p not in set(cleaned_new)]
        if remaining:
            print(f"[ERROR] 检测到无法清理的 .paper-explain-figures/ 外中间文件：{', '.join(remaining)}", file=sys.stderr)
            return 1

    print(str(out_md))
    print(str(run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
