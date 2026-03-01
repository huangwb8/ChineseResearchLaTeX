from __future__ import annotations

import argparse
from pathlib import Path

from nano_banana_client import nano_banana_health_check
from utils import fatal, info


def main() -> None:
    p = argparse.ArgumentParser(description="Check Gemini Nano Banana connectivity using .env config.")
    p.add_argument("--dotenv", type=Path, default=None, help="可选：显式指定 .env 路径（默认从 CWD 向上搜索）")
    args = p.parse_args()

    try:
        cfg = nano_banana_health_check(dotenv_path=args.dotenv, search_from=Path.cwd(), timeout_s=30)
    except Exception as exc:
        fatal(f"Nano Banana 连通性检查失败：{exc}")

    dotenv = str(cfg.dotenv_path) if cfg.dotenv_path is not None else "(not found)"
    info(f"OK: dotenv={dotenv}, base_url={cfg.base_url}, model={cfg.model}")


if __name__ == "__main__":
    main()

