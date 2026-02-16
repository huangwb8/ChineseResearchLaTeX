from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any, Dict, NoReturn, Optional, Tuple

import hashlib
import sys

SKILL_NAME = "nsfc-schematic"


def skill_root() -> Path:
    # scripts/* -> skill root
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fatal(message: str, exit_code: int = 2) -> NoReturn:
    print(f"[{SKILL_NAME}] ERROR: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def warn(message: str) -> None:
    print(f"[{SKILL_NAME}] WARN: {message}", file=sys.stderr)


def info(message: str) -> None:
    print(f"[{SKILL_NAME}] {message}")


def load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        fatal(
            "缺少依赖 PyYAML。请先安装：python3 -m pip install pyyaml\n"
            f"原始错误：{exc}"
        )

    try:
        raw = read_text(path)
    except FileNotFoundError:
        fatal(f"YAML 文件不存在：{path}")
    except Exception as exc:
        fatal(f"读取 YAML 文件失败：{path}\n{exc}")

    try:
        data = yaml.safe_load(raw)
    except Exception as exc:
        fatal(f"解析 YAML 失败：{path}\n{exc}")

    if not isinstance(data, dict):
        fatal(f"YAML 根节点必须为 mapping：{path}")
    return data


def dump_yaml(data: Dict[str, Any]) -> str:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        fatal(
            "缺少依赖 PyYAML。请先安装：python3 -m pip install pyyaml\n"
            f"原始错误：{exc}"
        )
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


@dataclass(frozen=True)
class FontChoice:
    path: Optional[Path]
    size: int


def pick_font(candidates: list[str], size: int) -> FontChoice:
    for p in candidates:
        path = Path(p)
        if path.exists():
            return FontChoice(path=path, size=size)
    return FontChoice(path=None, size=size)


def clamp(n: int, low: int, high: int) -> int:
    return max(low, min(high, n))


def is_safe_relative_path(p: str) -> bool:
    """
    Ensure a config-controlled path is:
    - relative (no absolute / drive / UNC)
    - does not contain '..'

    This is used to prevent accidental path traversal when resolving skill-local resources.
    """
    s = str(p).strip()
    if not s:
        return False
    if Path(s).is_absolute():
        return False
    win = PureWindowsPath(s)
    if win.is_absolute() or win.drive:
        return False
    if s.startswith("\\\\"):
        return False
    parts = [part for part in Path(s).parts if part not in {"", "."}]
    return all(part != ".." for part in parts)


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    s = hex_color.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
