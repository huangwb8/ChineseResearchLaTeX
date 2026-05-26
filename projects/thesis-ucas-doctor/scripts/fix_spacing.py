#!/usr/bin/env python3
"""
UCAS 博士论文空格清理脚本
功能：去掉中文与数字/英文之间不必要的空格，保护 LaTeX 命令和数学模式

用法示例：
  python fix_spacing.py --dry-run
  python fix_spacing.py
  python fix_spacing.py --from-backup
"""

import argparse
import re
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
EXTRA_TEX = PROJECT_ROOT / "extraTex"
BACKUP_DIR = PROJECT_ROOT / "workdirs" / "tex-cleanup" / "spacing_backup"

SENTINEL_PREFIX = "__BENSZ_SPACING_SENTINEL_"
SENTINEL_SUFFIX = "__"
PLACEHOLDER_PATTERN = re.compile(r"PLACEHOLDER_\d+")
SENTINEL_PATTERN = re.compile(
    re.escape(SENTINEL_PREFIX) + r"\d+" + re.escape(SENTINEL_SUFFIX)
)

STRUCTURED_SPACING_PATTERNS = [
    re.compile(r"第\s+\d+\s*[章节篇部]"),
    re.compile(r"[图表]\s+\d+(?:\s*-\s*\d+)+"),
]

# 需要处理的 .tex 文件（按优先级排序）
TARGET_FILES = [
    "chapter2.tex",
    "chapter3.tex",
    "chapter5.tex",
    "chapter4.tex",
    "chapter6.tex",
    "chapter7.tex",
    "appendixA.tex",
    "chapter1.tex",
    "appendixB.tex",
    "config-pre.tex",
    "cv.tex",
    "acknowledgements.tex",
    "abstract.tex",
    "info.tex",
]


def make_parser():
    parser = argparse.ArgumentParser(description="UCAS 博士论文空格清理工具")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写回文件")
    parser.add_argument(
        "--from-backup",
        action="store_true",
        help="从 workdirs/tex-cleanup/spacing_backup 读取源文本并重建 extraTex",
    )
    return parser


def protect_latex_content(text, counter=None):
    """将 LaTeX 命令和数学模式内容暂存为占位符，返回 (处理后文本, 占位符字典)。

    若提供 ``counter``（长度为 1 的列表），则共享该计数器，避免多轮保护之间
    的哨兵键碰撞。
    """
    placeholders = {}
    if counter is None:
        counter = [0]

    def replacer(match):
        key = f"{SENTINEL_PREFIX}{counter[0]}{SENTINEL_SUFFIX}"
        counter[0] += 1
        placeholders[key] = match.group(0)
        return key

    # 保护数学模式 $...$
    text = re.sub(r"\$(?:[^$\\]|\\.)*?\$", replacer, text)
    # 保护 \cite{...}, \ref{...}, \label{...}, \input{...}, \graphicspath{...}
    text = re.sub(
        r"\\(?:cite|ref|label|textcelsius|textsubscript|textsuperscript|percent|input|graphicspath)[^{]*\{[^}]*\}",
        replacer,
        text,
    )
    # 保护控制词后面作为分隔符使用的空格，避免 \item 张... 被误压成 \item张...
    text = re.sub(
        r"\\[A-Za-z@]+(?=\s+[\u4e00-\u9fff①②③④⑤⑥⑦⑧⑨□（）])\s+",
        replacer,
        text,
    )
    # 保护 \BenszTableNote{...}, \BenszFigureNote{...}, \BenszInline...{...}
    text = re.sub(r"\\Bensz\w+\{[^}]*\}", replacer, text)
    # 保护 \\, \hline 等表格命令
    text = re.sub(r"\\\\|\\hline", replacer, text)

    return text, placeholders


def restore_latex_content(text, placeholders):
    """恢复被保护的 LaTeX 内容。"""
    # 采用多轮恢复，处理“外层占位符恢复后才出现内层占位符”的嵌套场景。
    sorted_keys = sorted(placeholders.keys(), key=len, reverse=True)
    max_rounds = len(sorted_keys) + 1
    for _ in range(max_rounds):
        changed = False
        for key in sorted_keys:
            if key in text:
                text = text.replace(key, placeholders[key])
                changed = True
        if not changed:
            break
    return text


def protect_spacing_sensitive_labels(text, counter=None):
    """保护章节/图表编号等结构化文本，避免被通用空格清理误改。

    若提供 ``counter``（长度为 1 的列表），则共享该计数器。
    """
    placeholders = {}
    if counter is None:
        counter = [0]

    def replacer(match):
        key = f"{SENTINEL_PREFIX}{counter[0]}{SENTINEL_SUFFIX}"
        counter[0] += 1
        placeholders[key] = match.group(0)
        return key

    for pattern in STRUCTURED_SPACING_PATTERNS:
        text = pattern.sub(replacer, text)

    return text, placeholders


def inspect_text_safety(text):
    """返回文本安全检测信息，用于 dry-run 显示与写回门禁。"""
    nul_lines = []
    placeholder_lines = []
    sentinel_lines = []
    for i, line in enumerate(text.splitlines(), start=1):
        if "\x00" in line:
            nul_lines.append(i)
        if PLACEHOLDER_PATTERN.search(line):
            placeholder_lines.append(i)
        if SENTINEL_PATTERN.search(line):
            sentinel_lines.append(i)
    return {
        "nul_lines": nul_lines,
        "placeholder_lines": placeholder_lines,
        "sentinel_lines": sentinel_lines,
    }


def format_line_hits(line_numbers, limit=12):
    if not line_numbers:
        return "-"
    shown = ",".join(str(x) for x in line_numbers[:limit])
    if len(line_numbers) > limit:
        shown += f"...(+{len(line_numbers) - limit})"
    return shown


def ensure_safe_for_write(text, target_path):
    """写回门禁：禁止 NUL / PLACEHOLDER / 内部哨兵残留。"""
    checks = inspect_text_safety(text)
    failed = []
    if checks["nul_lines"]:
        failed.append(f"NUL 行={format_line_hits(checks['nul_lines'])}")
    if checks["placeholder_lines"]:
        failed.append(
            f"PLACEHOLDER 行={format_line_hits(checks['placeholder_lines'])}"
        )
    if checks["sentinel_lines"]:
        failed.append(f"SENTINEL 行={format_line_hits(checks['sentinel_lines'])}")
    if failed:
        raise RuntimeError(
            f"[BLOCK] 安全门禁失败：{target_path}\n  " + "\n  ".join(failed)
        )
    return checks


def fix_spacing_in_text(text):
    """保护 LaTeX 命令后，对纯文本执行空格清理。

    两次保护（LaTeX 内容 + 结构化标签）共享同一计数器，避免两轮保护
    各自从 0 开始产生相同哨兵键，导致 placeholders.update() 时后一轮
    覆盖前一轮（如 $_2$ 被替换为"第 X 章"）。
    """
    shared_counter = [0]
    protected_text, placeholders = protect_latex_content(text, counter=shared_counter)
    protected_text, structured_placeholders = protect_spacing_sensitive_labels(
        protected_text, counter=shared_counter
    )
    placeholders.update(structured_placeholders)
    changes = 0

    # 规则1：中文 + 空格 + 数字 → 中文+数字
    new_text, n = re.subn(r"([\u4e00-\u9fff])\s+(?=\d)", r"\1", protected_text)
    changes += n

    # 规则2：中文 + 空格 + 英文字母 → 中文+英文
    new_text, n = re.subn(r"([\u4e00-\u9fff])\s+(?=[a-zA-Z])", r"\1", new_text)
    changes += n

    # 规则3：数字/英文 + 空格 + 中文 → 数字/英文+中文
    new_text, n = re.subn(r"(?<=[a-zA-Z])\s+([\u4e00-\u9fff])", r"\1", new_text)
    changes += n

    # 规则4：数字 + 空格 + 中文 → 数字+中文
    new_text, n = re.subn(r"(?<=\d)\s+([\u4e00-\u9fff])", r"\1", new_text)
    changes += n

    result = restore_latex_content(new_text, placeholders)
    return result, changes


def process_file(target_path, source_path, dry_run=False, backup_current=True):
    """处理单个文件：从 source_path 读，写到 target_path。"""
    with open(source_path, encoding="utf-8") as f:
        source_text = f.read()

    fixed_text, changes = fix_spacing_in_text(source_text)
    source_checks = inspect_text_safety(source_text)
    output_checks = inspect_text_safety(fixed_text)
    safe_to_write = not (
        output_checks["nul_lines"]
        or output_checks["placeholder_lines"]
        or output_checks["sentinel_lines"]
    )

    print(f"  [{ 'DRY RUN' if dry_run else 'RUN' }] {target_path.name}: {changes} 处建议修改")
    print(
        "    [CHECK] source_nul={0} source_placeholder={1} source_sentinel={2}".format(
            len(source_checks["nul_lines"]),
            len(source_checks["placeholder_lines"]),
            len(source_checks["sentinel_lines"]),
        )
    )
    print(
        "    [CHECK] output_nul={0} output_placeholder={1} output_sentinel={2} safe_to_write={3}".format(
            len(output_checks["nul_lines"]),
            len(output_checks["placeholder_lines"]),
            len(output_checks["sentinel_lines"]),
            1 if safe_to_write else 0,
        )
    )

    if dry_run:
        return changes

    ensure_safe_for_write(fixed_text, target_path)

    if backup_current:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / target_path.name
        with open(target_path, encoding="utf-8") as f:
            current_text = f.read()
        with open(backup_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(current_text)

    with open(target_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(fixed_text)

    if backup_current:
        print(f"    [OK] 已写回并更新备份：{target_path.name}")
    else:
        print(f"    [OK] 已写回（from-backup，不覆盖备份）：{target_path.name}")
    return changes


def main():
    args = make_parser().parse_args()

    print("=" * 72)
    print("DRY RUN 模式：仅预览修改，不实际写入" if args.dry_run else "实际执行模式：将写回文件")
    print("源模式：workdirs/tex-cleanup/spacing_backup -> extraTex" if args.from_backup else "源模式：extraTex -> extraTex")
    print("=" * 72)

    total_changes = 0
    for filename in TARGET_FILES:
        target_path = EXTRA_TEX / filename
        source_path = (BACKUP_DIR / filename) if args.from_backup else target_path
        if not target_path.exists():
            print(f"  [SKIP] {filename}: 目标文件不存在")
            continue
        if not source_path.exists():
            print(f"  [SKIP] {filename}: 源文件不存在 ({source_path})")
            continue
        backup_current = (not args.from_backup)
        changes = process_file(
            target_path=target_path,
            source_path=source_path,
            dry_run=args.dry_run,
            backup_current=backup_current,
        )
        total_changes += changes

    print("=" * 72)
    print(f"总计: {total_changes} 处修改")
    if not args.dry_run and BACKUP_DIR.exists():
        print(f"备份目录: {BACKUP_DIR}")
        print("如需回退，逐文件从备份目录恢复即可。")


if __name__ == "__main__":
    main()
