from __future__ import annotations

import argparse
from pathlib import Path

from nano_banana_client import load_gemini_config, nano_banana_generate_png
from utils import fatal, info, read_text


def main() -> None:
    p = argparse.ArgumentParser(description="Generate a PNG with Gemini Nano Banana (image model).")
    p.add_argument("--prompt-file", type=Path, required=True)
    p.add_argument("--output-png", type=Path, required=True)
    p.add_argument("--canvas-w", type=int, default=3200)
    p.add_argument("--canvas-h", type=int, default=2000)
    p.add_argument("--dotenv", type=Path, default=None, help="可选：显式指定 .env 路径（默认从 CWD 向上搜索）")
    p.add_argument("--debug-dir", type=Path, default=None)
    args = p.parse_args()

    try:
        prompt = read_text(args.prompt_file)
    except Exception as exc:
        fatal(f"读取 prompt 失败：{exc}")

    cfg = load_gemini_config(dotenv_path=args.dotenv, search_from=Path.cwd())
    try:
        nano_banana_generate_png(
            cfg=cfg,
            prompt=prompt,
            output_png=args.output_png,
            canvas_w=int(args.canvas_w),
            canvas_h=int(args.canvas_h),
            debug_dir=args.debug_dir,
        )
    except Exception as exc:
        fatal(f"生成 PNG 失败：{exc}")

    info(f"完成：{args.output_png}")


if __name__ == "__main__":
    main()

