from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Optional


def find_dotenv(start: Path, *, filename: str = ".env", max_levels: int = 8) -> Optional[Path]:
    """
    Find a .env file by walking up parent directories from `start`.
    This keeps the skill usable when invoked from a subfolder (e.g. output_dir/).
    """
    cur = start.resolve()
    for _ in range(max_levels + 1):
        p = cur / filename
        if p.exists() and p.is_file():
            return p
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def _strip_inline_comment(value: str) -> str:
    """
    Strip inline comments for unquoted values:
    - KEY=foo # comment  -> foo
    - KEY="foo # keep"   -> foo # keep
    """
    v = value.strip()
    if not v:
        return v
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    # Best-effort: split on first unescaped '#'
    if "#" in v:
        return v.split("#", 1)[0].rstrip()
    return v


def parse_dotenv(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Common bash-style: export KEY=VALUE
        if line.startswith("export "):
            raw_line = raw_line.lstrip()[len("export ") :]
        m = _LINE_RE.match(raw_line)
        if not m:
            continue
        key = m.group(1)
        val = _strip_inline_comment(m.group(2))
        out[key] = val
    return out


def load_dotenv(path: Path) -> Dict[str, str]:
    try:
        data = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Be tolerant: .env sometimes contains non-UTF8 comments.
        data = path.read_text(encoding="utf-8", errors="replace")
    return parse_dotenv(data)


def merged_env(*, dotenv_path: Optional[Path]) -> Dict[str, str]:
    """
    Return a merged env dict where:
    - values from .env (if present) are loaded first
    - os.environ overrides .env (so user can override without editing files)
    """
    out: Dict[str, str] = {}
    if dotenv_path is not None and dotenv_path.exists():
        out.update(load_dotenv(dotenv_path))
    out.update({k: v for k, v in os.environ.items() if isinstance(v, str)})
    return out


def mask_secret(secret: str, *, keep: int = 4) -> str:
    s = str(secret or "")
    if not s:
        return ""
    if len(s) <= keep:
        return "*" * len(s)
    return "*" * max(8, len(s) - keep) + s[-keep:]
