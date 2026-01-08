#!/usr/bin/env python3
"""
multi_language.py - 综述多语言翻译与智能编译

功能：
  1. 语言检测与验证
  2. AI 翻译（保留引用和结构）
  3. 智能修复编译（重试到成功）
  4. PDF/Word 导出
  5. 失败兜底（broken 文件 + 错误报告）

作者: systematic-literature-review skill
版本: 1.0.0
日期: 2026-01-03
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

try:
    from config_loader import load_config  # type: ignore
except Exception:
    load_config = None

# ============================================================================
# 常量定义
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent

# 编译超时配置
DEFAULT_COMPILE_TIMEOUT = 300  # 单次编译 5 分钟
DEFAULT_TOTAL_TIMEOUT = 1800   # 总计 30 分钟
MAX_COMPILE_RETRIES = 99       # 实际无上限

# 语言代码到名称的映射
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
}

# ============================================================================
# 配置加载
# ============================================================================

def get_multilingual_config() -> dict:
    """从 config.yaml 加载多语言配置."""
    if load_config is None:
        return get_default_multilingual_config()

    try:
        cfg = load_config()
        multi_cfg = cfg.get("multilingual") if isinstance(cfg, dict) else {}
        if isinstance(multi_cfg, dict) and multi_cfg.get("enabled"):
            return multi_cfg
    except Exception:
        pass

    return get_default_multilingual_config()


def get_default_multilingual_config() -> dict:
    """默认多语言配置."""
    return {
        "enabled": True,
        "supported_languages": [
            {"code": "en", "name": "English", "keywords": ["英语", "英文", "English", "en"], "latex_packages": []},
            {"code": "zh", "name": "Chinese", "keywords": ["中文", "汉语", "Chinese", "zh"], "latex_packages": ["ctex"]},
            {"code": "ja", "name": "Japanese", "keywords": ["日语", "日文", "Japanese", "ja"], "latex_packages": ["luatexja-preset"]},
            {"code": "de", "name": "German", "keywords": ["德语", "德文", "German", "de", "Deutsch"], "latex_packages": ["babel", "ngerman"]},
            {"code": "fr", "name": "French", "keywords": ["法语", "法文", "French", "fr", "Français"], "latex_packages": ["babel", "french"]},
            {"code": "es", "name": "Spanish", "keywords": ["西班牙语", "西班牙文", "Spanish", "es", "Español"], "latex_packages": ["babel", "spanish"]},
        ],
        "max_compile_retries": MAX_COMPILE_RETRIES,
        "compile_timeout": DEFAULT_COMPILE_TIMEOUT,
        "total_timeout": DEFAULT_TOTAL_TIMEOUT,
        "translation_prompt_template": """
你是一位学术翻译专家。请将以下综述正文翻译为{language}。

要求：
1. 保持学术语气、专业性和逻辑连贯性
2. 保留所有 \\cite{{key}} 引用标记及其位置，绝对不可修改
3. 保留所有 LaTeX 结构命令（\\section, \\subsection, \\begin{{itemize}}, \\begin{{enumerate}} 等）
4. 保留所有数学公式（$...$, \\[...\\], \\begin{{equation}} 等）
5. 保留图表标签和引用（\\label{{}}, \\ref{{}} 等）
6. 专业术语可保留原文或添加译注（如"Transformer（变换器）"）
7. 缩略词首次出现时展开（如"Artificial Intelligence (AI)"）

仅输出翻译后的 LaTeX 源码，不要包含任何解释性文字。
""",
    }


def get_language_config(lang_code: str) -> dict | None:
    """获取指定语言的配置."""
    cfg = get_multilingual_config()
    for lang in cfg.get("supported_languages", []):
        if isinstance(lang, dict) and lang.get("code") == lang_code:
            return lang
    return None


# ============================================================================
# 语言检测
# ============================================================================

def detect_language(user_input: str) -> str | None:
    """从用户输入中检测目标语言.

    Args:
        user_input: 用户输入字符串

    Returns:
        语言代码（如 'ja', 'de'）或 None
    """
    cfg = get_multilingual_config()
    user_input_lower = user_input.lower()

    for lang in cfg.get("supported_languages", []):
        if not isinstance(lang, dict):
            continue
        keywords = lang.get("keywords", [])
        code = lang.get("code")
        if isinstance(keywords, list) and code:
            for kw in keywords:
                if kw.lower() in user_input_lower:
                    return code
    return None


def validate_language(lang_code: str) -> bool:
    """验证语言代码是否支持."""
    cfg = get_multilingual_config()
    for lang in cfg.get("supported_languages", []):
        if isinstance(lang, dict) and lang.get("code") == lang_code:
            return True
    return False


# ============================================================================
# 备份与恢复
# ============================================================================

def backup_original_tex(tex_file: Path) -> Path:
    """备份原 tex 文件.

    Args:
        tex_file: 原 tex 文件路径

    Returns:
        备份文件路径
    """
    backup_file = tex_file.with_suffix('.tex.bak')
    if backup_file.exists():
        # 已有备份，添加时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = tex_file.with_suffix(f'.tex.bak.{timestamp}')
    shutil.copy2(tex_file, backup_file)
    print(f"✓ 原文已备份: {backup_file}", file=sys.stderr)
    return backup_file


def restore_backup(tex_file: Path) -> Path | None:
    """从备份恢复原文.

    Args:
        tex_file: 要恢复的 tex 文件路径

    Returns:
        恢复的备份文件路径，如果失败返回 None
    """
    # 先尝试带时间戳的备份（最新的）
    backups = sorted(tex_file.parent.glob(f"{tex_file.name}.bak.*"), reverse=True)
    if backups:
        backup_file = backups[0]
        shutil.copy2(backup_file, tex_file)
        print(f"✓ 已从备份恢复: {backup_file}", file=sys.stderr)
        return backup_file

    # 尝试不带时间戳的备份
    backup_file = tex_file.with_suffix('.tex.bak')
    if backup_file.exists():
        shutil.copy2(backup_file, tex_file)
        print(f"✓ 已从备份恢复: {backup_file}", file=sys.stderr)
        return backup_file

    print(f"⚠️ 未找到备份文件: {backup_file}", file=sys.stderr)
    return None


# ============================================================================
# AI 翻译
# ============================================================================

def translate_tex_content(tex_content: str, target_lang: str) -> str:
    """翻译 tex 内容（由 AI 在技能环境中调用）.

    注意：此函数返回翻译提示词，实际翻译由 AI 完成。

    Args:
        tex_content: 原 tex 内容
        target_lang: 目标语言代码

    Returns:
        翻译提示词（供 AI 使用）
    """
    cfg = get_multilingual_config()
    lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    template = cfg.get("translation_prompt_template", "")

    prompt = template.format(language=lang_name) + f"\n\nLaTeX 源码：\n{tex_content}"
    return prompt


def write_translated_tex(tex_file: Path, translated_content: str) -> Path:
    """写入翻译后的 tex 文件（覆盖原文）.

    Args:
        tex_file: tex 文件路径
        translated_content: 翻译后的内容

    Returns:
        tex 文件路径
    """
    # 备份原文
    backup_original_tex(tex_file)

    # 写入翻译内容
    tex_file.write_text(translated_content, encoding="utf-8")
    print(f"✓ 翻译完成，已覆盖: {tex_file}", file=sys.stderr)
    return tex_file


# ============================================================================
# LaTeX 错误分析
# ============================================================================

def analyze_latex_log(log_content: str) -> tuple[bool, str, str]:
    """分析 LaTeX 编译日志.

    Args:
        log_content: .log 文件内容

    Returns:
        (成功, 错误类型, 错误详情)
    """
    if not log_content:
        return False, "unknown_error", "空的日志文件"

    # 检查是否成功编译
    if "Output written on" in log_content and ".pdf" in log_content:
        # 还需要确认没有严重错误
        if "Error" not in log_content or ("Emergency stop" not in log_content and "Fatal error" not in log_content):
            return True, "", ""

    # 常见错误模式
    patterns = [
        # 缺少宏包
        (r"File `(.+?)\.sty' not found", "missing_package"),
        (r"! LaTeX Error: File `(.+?)\.sty' not found", "missing_package"),
        (r"! Undefined control sequence", "undefined_command"),
        # 字体问题
        (r"! Font .+? not found", "missing_font"),
        (r"! Font .*? cannot be found", "missing_font"),
        (r"kpathsea:.+? not found", "missing_font"),
        # 编码问题
        (r"Package inputenc Error", "encoding_error"),
        (r"Package utf8 Error", "encoding_error"),
        # 语法错误
        (r"! Missing \$? inserted", "syntax_error"),
        (r"! Missing { inserted", "syntax_error"),
        (r"! Missing } inserted", "syntax_error"),
        (r"Runaway argument?", "syntax_error"),
        # 文件系统错误
        (r"! I can't find file", "file_not_found"),
        (r"Permission denied", "permission_denied"),
        # 内存问题
        (r"TeX capacity exceeded", "memory_exceeded"),
        # CTeX 特定
        (r"! Package ctex Error", "ctex_error"),
    ]

    for pattern, error_type in patterns:
        match = re.search(pattern, log_content, re.MULTILINE | re.IGNORECASE)
        if match:
            # 提取错误详情（日志中错误前后几行）
            lines = log_content.split('\n')
            error_line = -1
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    error_line = i
                    break

            context_start = max(0, error_line - 2)
            context_end = min(len(lines), error_line + 3)
            details = '\n'.join(lines[context_start:context_end])

            return False, error_type, details

    # 未分类错误
    return False, "unknown_error", log_content[:500]


def is_fixable_error(error_type: str) -> bool:
    """判断错误是否可修复.

    Args:
        error_type: 错误类型

    Returns:
        是否可修复
    """
    fixable_errors = {
        "missing_package",
        "undefined_command",
        "missing_font",
        "encoding_error",
        "syntax_error",
        "file_not_found",
        "ctex_error",
    }
    return error_type in fixable_errors


# ============================================================================
# LaTeX 智能修复
# ============================================================================

def fix_tex_error(tex_file: Path, error_type: str, details: str, target_lang: str) -> tuple[bool, str]:
    """修复 tex 文件中的错误（由 AI 在技能环境中调用）.

    注意：此函数返回修复提示词，实际修复由 AI 完成。

    Args:
        tex_file: tex 文件路径
        error_type: 错误类型
        details: 错误详情
        target_lang: 目标语言代码

    Returns:
        (是否需要 AI 修复, 修复提示词)
    """
    lang_cfg = get_language_config(target_lang)
    latex_packages = lang_cfg.get("latex_packages", []) if lang_cfg else []

    # 可自动修复的简单错误
    tex_content = tex_file.read_text(encoding="utf-8", errors="replace")

    # 检查并添加缺失的宏包
    if error_type == "missing_package":
        match = re.search(r"File `(.+?)\.sty' not found", details)
        if match:
            package_name = match.group(1)
            # 检查是否已经包含
            if f"\\usepackage{{{package_name}}}" not in tex_content:
                # 在 \documentclass 后添加
                tex_content = tex_content.replace(
                    "\\begin{document}",
                    f"\\usepackage{{{package_name}}}\n\\begin{document}"
                )
                tex_file.write_text(tex_content, encoding="utf-8")
                return True, f"已自动添加宏包: {package_name}"

    # 检查并添加语言所需的宏包
    if latex_packages:
        for pkg in latex_packages:
            if f"\\usepackage{{{pkg}}}" not in tex_content:
                # 在 \documentclass 后添加
                if "\\begin{document}" in tex_content:
                    tex_content = tex_content.replace(
                        "\\begin{document}",
                        f"\\usepackage{{{pkg}}}\n\\begin{document}"
                    )
                else:
                    # 在 \documentclass 后添加
                    lines = tex_content.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip().startswith('\\documentclass'):
                            lines.insert(i + 1, f"\\usepackage{{{pkg}}}")
                            break
                    tex_content = '\n'.join(lines)

                tex_file.write_text(tex_content, encoding="utf-8")
                return True, f"已自动添加语言宏包: {pkg}"

    # 需要 AI 修复的复杂错误
    fix_prompt = f"""
LaTeX 编译失败，请修复以下错误：

错误类型: {error_type}
错误详情:
{details}

要求:
1. 仅修复与错误相关的部分，不要修改其他内容
2. 保留所有 \\cite{{}} 引用标记
3. 保留所有文本内容和学术逻辑
4. 如果是字体/宏包问题，添加相应的 \\usepackage
5. 如果是语法错误，修复括号或命令

请输出完整的修复后 LaTeX 源码（不要包含解释）。
当前 tex 文件内容:
{tex_content}
"""
    return False, fix_prompt


def apply_ai_fix(tex_file: Path, fixed_content: str) -> Path:
    """应用 AI 修复的内容.

    Args:
        tex_file: tex 文件路径
        fixed_content: AI 修复后的内容

    Returns:
        tex 文件路径
    """
    tex_file.write_text(fixed_content, encoding="utf-8")
    print(f"✓ AI 修复已应用", file=sys.stderr)
    return tex_file


# ============================================================================
# 编译
# ============================================================================

def _check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def _run_xelatex(tex_file: Path, work_dir: Path, env: dict[str, str] | None = None, timeout: int = 300) -> tuple[bool, str]:
    """运行 xelatex 编译.

    Args:
        tex_file: tex 文件路径
        work_dir: 工作目录
        env: 环境变量
        timeout: 超时时间（秒）

    Returns:
        (成功, 日志内容)
    """
    try:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        proc = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_file.name],
            cwd=work_dir,
            text=True,
            capture_output=True,
            env=merged_env,
            timeout=timeout
        )

        log_file = work_dir / f"{tex_file.stem}.log"
        log_content = ""
        if log_file.exists():
            log_content = log_file.read_text(encoding="utf-8", errors="replace")

        return proc.returncode == 0, log_content

    except subprocess.TimeoutExpired:
        return False, f"编译超时（{timeout}秒）"
    except Exception as e:
        return False, str(e)


def _run_bibtex(base: str, work_dir: Path, env: dict[str, str] | None = None, timeout: int = 60) -> tuple[bool, str]:
    """运行 bibtex.

    Args:
        base: 文件基础名
        work_dir: 工作目录
        env: 环境变量
        timeout: 超时时间（秒）

    Returns:
        (成功, 日志内容)
    """
    try:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        proc = subprocess.run(
            ["bibtex", base],
            cwd=work_dir,
            text=True,
            capture_output=True,
            env=merged_env,
            timeout=timeout
        )

        blg_file = work_dir / f"{base}.blg"
        log_content = ""
        if blg_file.exists():
            log_content = blg_file.read_text(encoding="utf-8", errors="replace")

        return proc.returncode == 0, log_content

    except subprocess.TimeoutExpired:
        return False, f"BibTeX 超时（{timeout}秒）"
    except Exception as e:
        return False, str(e)


def compile_with_smart_fix(
    tex_file: Path,
    bib_file: Path,
    target_lang: str,
    compile_timeout: int = DEFAULT_COMPILE_TIMEOUT,
    total_timeout: int = DEFAULT_TOTAL_TIMEOUT
) -> tuple[bool, Path, str]:
    """智能修复编译（重试到成功）.

    Args:
        tex_file: tex 文件路径
        bib_file: bib 文件路径
        target_lang: 目标语言代码
        compile_timeout: 单次编译超时
        total_timeout: 总超时

    Returns:
        (成功, PDF 路径, 错误报告)
    """
    cfg = get_multilingual_config()
    max_retries = cfg.get("max_compile_retries", MAX_COMPILE_RETRIES)

    tex_file = tex_file.resolve()
    work_dir = tex_file.parent
    base = tex_file.stem

    # 检查工具
    if not _check_tool("xelatex"):
        return False, tex_file, "xelatex 未找到，请安装 TeX Live / MacTeX / MiKTeX"
    if not _check_tool("bibtex"):
        return False, tex_file, "bibtex 未找到，请安装包含 bibtex 的 TeX 发行版"

    # 设置环境变量（引用模板目录）
    template_dir = SKILL_ROOT / "latex-template"
    separator = ";" if sys.platform == "win32" else ":"
    env = {
        "TEXINPUTS": f".//{separator}{template_dir}{separator}//",
        "BSTINPUTS": f".//{separator}{template_dir}{separator}//",
    }

    # 修复历史（用于循环检测）
    fix_history: list[tuple[str, str]] = []
    start_time = time.time()

    for attempt in range(1, max_retries + 1):
        # 超时检查
        elapsed = time.time() - start_time
        if elapsed > total_timeout:
            error_report = generate_error_report_text(tex_file, f"编译总超时（{total_timeout}秒），已尝试 {attempt} 轮", fix_history)
            return False, tex_file, error_report

        print(f"  第 {attempt} 轮编译...", file=sys.stderr)

        # 完整的 BibTeX 工作流：xelatex -> bibtex -> xelatex -> xelatex
        _, log1 = _run_xelatex(tex_file, work_dir, env, timeout=compile_timeout)
        _, bib_log = _run_bibtex(base, work_dir, env, timeout=60)
        _, log2 = _run_xelatex(tex_file, work_dir, env, timeout=compile_timeout)
        success, final_log = _run_xelatex(tex_file, work_dir, env, timeout=compile_timeout)

        # 合并日志
        combined_log = log1 + "\n" + bib_log + "\n" + log2 + "\n" + final_log

        # 检查是否成功
        success, error_type, error_details = analyze_latex_log(combined_log)
        if success:
            pdf_file = work_dir / f"{base}.pdf"
            if pdf_file.exists():
                print(f"✓ 编译成功: {pdf_file}", file=sys.stderr)
                return True, pdf_file, ""
            else:
                success = False
                error_type = "pdf_not_generated"
                error_details = "编译日志显示成功但未生成 PDF 文件"

        # 检查是否可修复
        if not is_fixable_error(error_type):
            error_report = generate_error_report_text(tex_file, f"不可修复错误: {error_type}\n{error_details}", fix_history)
            return False, tex_file, error_report

        # 循环检测
        fix_signature = (error_type, error_details[:100])  # 使用前 100 字符作为签名
        if fix_signature in fix_history:
            error_report = generate_error_report_text(tex_file, f"检测到修复循环，已尝试 {attempt} 轮\n错误类型: {error_type}", fix_history)
            return False, tex_file, error_report

        fix_history.append(fix_signature)

        # 尝试修复
        print(f"    错误: {error_type}", file=sys.stderr)
        auto_fixed, fix_result = fix_tex_error(tex_file, error_type, error_details, target_lang)

        if auto_fixed:
            print(f"    ✓ 自动修复: {fix_result}", file=sys.stderr)
        else:
            # 需要 AI 修复，返回提示词
            error_report = generate_error_report_text(
                tex_file,
                f"需要 AI 修复（第 {attempt} 轮）\n错误类型: {error_type}\n\n请使用以下提示词进行 AI 修复：\n\n{fix_result}",
                fix_history
            )
            return False, tex_file, error_report

    # 理论上不会到达这里
    error_report = generate_error_report_text(tex_file, f"达到最大重试次数 {max_retries}", fix_history)
    return False, tex_file, error_report


def generate_error_report_text(tex_file: Path, message: str, fix_history: list[tuple[str, str]]) -> str:
    """生成错误报告文本.

    Args:
        tex_file: tex 文件路径
        message: 主要错误消息
        fix_history: 修复历史

    Returns:
        错误报告文本
    """
    lines = [
        "# LaTeX 编译错误报告",
        f"\n文件: {tex_file}",
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\n{message}",
    ]

    if fix_history:
        lines.append("\n## 修复历史")
        for i, (error_type, error_details) in enumerate(fix_history, 1):
            lines.append(f"\n{i}. 错误类型: {error_type}")
            lines.append(f"   详情: {error_details[:100]}...")

    lines.append("\n## 建议操作")
    lines.append("1. 检查上述错误类型并修复相应问题")
    lines.append("2. 如需恢复原文，运行: python scripts/multi_language.py --tex-file FILE.tex --restore")
    lines.append("3. 人工检查并修复 tex 文件后重新编译")

    return "\n".join(lines)


def generate_error_report(tex_file: Path, log_content: str, error_history: list) -> Path:
    """生成错误报告文件.

    Args:
        tex_file: tex 文件路径
        log_content: 日志内容
        error_history: 错误历史

    Returns:
        错误报告文件路径
    """
    report_file = tex_file.parent / f"{tex_file.stem}_error_report.md"
    report_text = generate_error_report_text(tex_file, log_content, error_history)
    report_file.write_text(report_text, encoding="utf-8")
    print(f"✓ 错误报告已生成: {report_file}", file=sys.stderr)
    return report_file


# ============================================================================
# Word 导出
# ============================================================================

def export_word(tex_file: Path, bib_file: Path) -> Path:
    """导出 Word 文档.

    Args:
        tex_file: tex 文件路径
        bib_file: bib 文件路径

    Returns:
        docx 文件路径
    """
    # 检查 pandoc
    if not _check_tool("pandoc"):
        raise RuntimeError("pandoc 未找到，请安装 pandoc: https://pandoc.org/installing.html")

    docx_file = tex_file.parent / f"{tex_file.stem}.docx"

    cmd = [
        "pandoc",
        str(tex_file),
        "-o", str(docx_file),
        "--from=latex",
        "--standalone",
        "--citeproc",
        f"--bibliography={bib_file}",
    ]

    proc = subprocess.run(cmd, text=True, capture_output=True, cwd=tex_file.parent)
    if proc.returncode != 0:
        raise RuntimeError(
            f"pandoc 失败:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  stdout:\n{proc.stdout}\n"
            f"  stderr:\n{proc.stderr}\n"
        )

    if not docx_file.exists():
        raise RuntimeError(f"docx 未生成: {docx_file}")

    print(f"✓ Word 已生成: {docx_file}", file=sys.stderr)
    return docx_file


# ============================================================================
# CLI 入口
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="综述多语言翻译与智能编译",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 翻译为日语并编译
  python multi_language.py --tex-file review.tex --bib-file refs.bib --language ja

  # 从备份恢复
  python multi_language.py --tex-file review.tex --restore

支持的语言代码:
  en  - English
  zh  - Chinese
  ja  - Japanese
  de  - German
  fr  - French
  es  - Spanish
        """
    )

    parser.add_argument("--tex-file", required=True, type=Path, help="输入 .tex 文件")
    parser.add_argument("--bib-file", type=Path, help="输入 .bib 文件（编译时需要）")
    parser.add_argument("--language", type=str, help="目标语言代码（en/zh/ja/de/fr/es）")
    parser.add_argument("--restore", action="store_true", help="从 .bak 恢复原文")
    parser.add_argument("--compile-only", action="store_true", help="仅编译，不翻译")
    parser.add_argument("--export-word", action="store_true", help="编译成功后导出 Word")

    args = parser.parse_args()

    try:
        # 恢复模式
        if args.restore:
            backup = restore_backup(args.tex_file)
            if backup:
                print(f"✓ 已恢复原文: {args.tex_file}")
                return 0
            else:
                print(f"✗ 恢复失败", file=sys.stderr)
                return 1

        # 编译模式
        if args.compile_only:
            if not args.bib_file:
                print("✗ 编译模式需要 --bib-file 参数", file=sys.stderr)
                return 1

            success, pdf_path, error_report = compile_with_smart_fix(args.tex_file, args.bib_file, "en")
            if success:
                print(f"✓ 编译成功: {pdf_path}")
                if args.export_word:
                    export_word(args.tex_file, args.bib_file)
                return 0
            else:
                print(f"✗ 编译失败:\n{error_report}", file=sys.stderr)
                return 1

        # 翻译模式
        if args.language:
            # 验证语言
            if not validate_language(args.language):
                print(f"✗ 不支持的语言代码: {args.language}", file=sys.stderr)
                print("支持的语言: en, zh, ja, de, fr, es", file=sys.stderr)
                return 1

            # 生成翻译提示词（由 AI 执行实际翻译）
            tex_content = args.tex_file.read_text(encoding="utf-8", errors="replace")
            prompt = translate_tex_content(tex_content, args.language)
            print("\n" + "="*60, file=sys.stderr)
            print("请使用以下提示词进行 AI 翻译：", file=sys.stderr)
            print("="*60 + "\n", file=sys.stderr)
            print(prompt)
            print("\n" + "="*60, file=sys.stderr)
            print("翻译完成后，将内容写入 tex 文件，然后运行:", file=sys.stderr)
            print(f"python {sys.argv[0]} --tex-file {args.tex_file} --compile-only", file=sys.stderr)
            if args.bib_file:
                print(f"python {sys.argv[0]} --tex-file {args.tex_file} --bib-file {args.bib_file} --compile-only --export-word", file=sys.stderr)
            print("="*60 + "\n", file=sys.stderr)

            return 0

        # 无效参数
        parser.print_help()
        return 1

    except Exception as e:
        print(f"✗ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
