#!/usr/bin/env python3
r"""
validate_counts.py - 渲染前的正文字数与引用数量硬校验

设计原则（无 AI 参与，纯规则）：
- 去掉注释/导言/数学/代码环境/命令名，仅保留正文纯文本
- 中文按单字计数；英文按单词边界计数；标点/空白不计
- \cite* 族引用：解析花括号内的 key，去重后计数
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

import yaml


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_body(tex: str) -> Tuple[str, list[str]]:
    """裁剪到 \\begin{document} 之后，并去掉常见非正文环境。"""
    debug_notes: list[str] = []
    marker = "\\begin{document}"
    idx = tex.find(marker)
    if idx == -1:
        raise ValueError("tex 缺少 \\begin{document}")
    body = tex[idx + len(marker) :]
    # 去注释（忽略被转义的 \\%）
    body = re.sub(r"(?<!\\)%.*", " ", body)
    # 去数学（多种写法）
    patterns = [
        r"\$\$.*?\$\$",
        r"\\\[.*?\\\]",
        r"\\\(.*?\\\)",
        r"\$.*?\$",
        r"\\begin\{equation\*?\}.*?\\end\{equation\*?\}",
        r"\\begin\{align\*?\}.*?\\end\{align\*?\}",
    ]
    for pat in patterns:
        body, n = re.subn(pat, " ", body, flags=re.DOTALL)
        if n:
            debug_notes.append(f"removed math blocks: {pat} x{n}")
    # 去代码/逐字环境
    for env in ["lstlisting", "verbatim", "Verbatim", "minted"]:
        env_pat = rf"\\begin\{{{env}\*?\}}.*?\\end\{{{env}\*?\}}"
        body, n = re.subn(env_pat, " ", body, flags=re.DOTALL)
        if n:
            debug_notes.append(f"removed env {env}: {n}")
    # 去掉 begin/end 结构标记
    body = re.sub(r"\\begin\{[^\}]+\}|\s*\\end\{[^\}]+\}", " ", body)
    # 去可选参数，例如 \section[短题]{长题}
    body = re.sub(r"\\[a-zA-Z@]+\*?\s*\[[^\]]*\]", " ", body)
    # 去命令名（保留花括号里的文本）
    body = re.sub(r"\\[a-zA-Z@]+\*?", " ", body)
    # 清理花括号与特殊空白
    body = body.replace("{", " ").replace("}", " ").replace("~", " ")
    # 合并空白
    body = re.sub(r"\s+", " ", body)
    return body.strip(), debug_notes


def count_words(text: str) -> Tuple[int, int, int, int]:
    """返回 (总计, 中文, 英文, 数字token)。

    计数口径：
    - 中文：按单字计数（含中文数字“一二三”等）
    - 英文：按单词边界计数
    - 数字：按连续数字串 token 计数（如 "2023年" 计为 1 个数字 token）
    - 总计：默认不把数字计入 words_total（保持历史口径），另输出 words_total_including_digits 供参考
    """
    cn_matches = re.findall(r"[\u4e00-\u9fff]", text)
    en_matches = re.findall(r"\b[A-Za-z][A-Za-z0-9'-]*\b", text)
    digit_matches = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    cn_count = len(cn_matches)
    en_count = len(en_matches)
    digit_count = len(digit_matches)
    total = cn_count + en_count
    return total, cn_count, en_count, digit_count


def extract_cite_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    pattern = re.compile(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}")
    for m in pattern.finditer(tex):
        raw = m.group(1)
        for part in re.split(r"[,\s]+", raw):
            k = part.strip()
            if k:
                keys.add(k)
    return keys


def load_thresholds(config: dict, review_level: str, override_words: Optional[int], override_cites: Optional[int]) -> Tuple[int, int]:
    validation_cfg = config.get("validation", {}) or {}
    words_cfg = validation_cfg.get("words", {}) or {}
    refs_cfg = validation_cfg.get("references", {}) or {}
    min_words_default = (words_cfg.get("min") or {}).get(review_level, 0)
    max_words_default = (words_cfg.get("max") or {}).get(review_level, 0)
    min_cites_default = (refs_cfg.get("min") or {}).get(review_level, 0)
    max_cites_default = (refs_cfg.get("max") or {}).get(review_level, 0)

    min_words = override_words if override_words is not None else min_words_default
    min_cites = override_cites if override_cites is not None else min_cites_default
    return min_words, min_cites, max_words_default, max_cites_default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate review.tex word/citation counts")
    parser.add_argument("--tex", required=True, type=Path, help="Path to {topic}_review.tex")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent.parent / "config.yaml", help="Path to config.yaml")
    parser.add_argument("--review-level", choices=["premium", "standard", "basic"], help="Override review level (default: config.review_levels.default)")
    parser.add_argument("--min-words", type=int, help="Override minimum body words")
    parser.add_argument("--max-words", type=int, help="Override maximum body words")
    parser.add_argument("--min-cites", type=int, help="Override minimum unique citation keys")
    parser.add_argument("--max-cites", type=int, help="Override maximum unique citation keys")
    parser.add_argument("--debug", action="store_true", help="Print debug notes to stderr")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tex_path = args.tex.resolve()
    config_path = args.config.resolve()

    if not tex_path.exists():
        print(f"✗ tex 不存在: {tex_path}", file=sys.stderr)
        return 2

    try:
        config = load_config(config_path)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 读取配置失败: {exc}", file=sys.stderr)
        return 2

    review_level = args.review_level
    if review_level is None:
        review_level = config.get("review_levels", {}).get("default", "premium")

    min_words, min_cites, max_words_default, max_cites_default = load_thresholds(config, review_level, args.min_words, args.min_cites)
    max_words = args.max_words if args.max_words is not None else max_words_default
    max_cites = args.max_cites if args.max_cites is not None else max_cites_default

    try:
        tex_raw = tex_path.read_text(encoding="utf-8", errors="replace")
        body_text, debug_notes = extract_body(tex_raw)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 读取/解析 tex 失败: {exc}", file=sys.stderr)
        return 2

    words_total, words_cn, words_en, words_digits = count_words(body_text)
    cite_keys = extract_cite_keys(tex_raw)

    passed = True
    if min_words and words_total < min_words:
        passed = False
    if max_words and words_total > max_words:
        passed = False
    if min_cites and len(cite_keys) < min_cites:
        passed = False
    if max_cites and len(cite_keys) > max_cites:
        passed = False

    result = {
        "file": str(tex_path),
        "review_level": review_level,
        "words_total": words_total,
        "words_chinese": words_cn,
        "words_english": words_en,
        "words_digits": words_digits,
        "words_total_including_digits": words_total + int(words_digits),
        "cite_keys_count": len(cite_keys),
        "thresholds": {
          "min_words": min_words,
          "max_words": max_words,
          "min_unique_citations": min_cites,
          "max_unique_citations": max_cites,
        },
        "passed": passed,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.debug:
        print(f"[debug] body length (chars): {len(body_text)}", file=sys.stderr)
        for note in debug_notes:
            print(f"[debug] {note}", file=sys.stderr)

    if not passed:
        if min_words and words_total < min_words:
            print(f"✗ 正文字数不足: {words_total} < {min_words}", file=sys.stderr)
        if max_words and words_total > max_words:
            print(f"✗ 正文字数超出: {words_total} > {max_words}", file=sys.stderr)
        if min_cites and len(cite_keys) < min_cites:
            print(f"✗ 引用数不足: {len(cite_keys)} < {min_cites}", file=sys.stderr)
        if max_cites and len(cite_keys) > max_cites:
            print(f"✗ 引用数超出: {len(cite_keys)} > {max_cites}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
