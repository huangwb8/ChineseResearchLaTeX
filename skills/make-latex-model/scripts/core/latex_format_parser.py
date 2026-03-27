#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LaTeX 格式解析器（轻量、无依赖）

用途：
- 从 LaTeX 标题参数中提取“可见文本 + 加粗/斜体状态”片段
- 为 compare_headings / heading_validator 等组件提供统一口径，避免各处正则各写一套

设计原则：
- 只解析与标题对齐相关的“常见文本格式命令”，不追求完整 TeX 语法覆盖
- 尽量容错：遇到未知命令，默认跳过命令 token，但保留其花括号内容（由通用花括号处理完成）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class _FmtState:
    bold: bool = False
    italic: bool = False
    underline: bool = False

    def with_updates(self, **kwargs: Any) -> "_FmtState":
        data = {"bold": self.bold, "italic": self.italic, "underline": self.underline}
        data.update(kwargs)
        return _FmtState(**data)


class LatexFormatParser:
    # “包裹式”命令：\textbf{...}
    WRAP_BOLD = {"textbf", "mathbf"}
    WRAP_ITALIC = {"textit", "mathit", "emph"}

    # “声明式”命令：{\bfseries ...}
    DECL_BOLD = {"bfseries", "boldmath"}
    DECL_ITALIC = {"itshape"}

    # 产生空白的命令：作为一个空格处理
    SPACE_COMMANDS = {" ", "quad", "qquad", "hspace", "vspace", "kern"}

    # 换行控制：作为空白处理（标题对齐时以空格归一）
    BREAK_COMMANDS = {"linebreak", "newline"}

    @staticmethod
    def extract_formatted_text(latex_text: str) -> List[Dict[str, Any]]:
        """
        提取格式片段：
          [{"text": "...", "bold": bool, "italic": bool, "underline": bool}, ...]
        """
        frags = LatexFormatParser._parse(latex_text, _FmtState())
        return LatexFormatParser._merge_consecutive_fragments(frags)

    @staticmethod
    def clean_latex_text(text: str) -> str:
        """将 LaTeX 文本清理为“可见纯文本”（保留空格语义）。"""
        frags = LatexFormatParser.extract_formatted_text(text)
        out = "".join(f.get("text", "") for f in frags)
        # 标题对齐的最小归一：~ 与多空白归一交由调用方决定，这里只做 strip
        return out.strip()

    @staticmethod
    def fragments_to_latex(fragments: List[Dict[str, Any]]) -> str:
        """
        将格式片段转换回 LaTeX（只保证 bold/italic 的最常见可用表示）：
        - bold  → \textbf{...}
        - italic → \textit{...}
        """
        def esc(s: str) -> str:
            # 最小转义：避免把用户的花括号直接带回去造成结构问题
            return s.replace("{", "\\{").replace("}", "\\}")

        out: List[str] = []
        i = 0
        while i < len(fragments):
            f = fragments[i]
            text = str(f.get("text", "") or "")
            bold = bool(f.get("bold", False))
            italic = bool(f.get("italic", False))

            # 尽量合并连续相同样式
            j = i + 1
            while j < len(fragments):
                g = fragments[j]
                if bool(g.get("bold", False)) != bold:
                    break
                if bool(g.get("italic", False)) != italic:
                    break
                text += str(g.get("text", "") or "")
                j += 1

            if bold and italic:
                out.append(f"\\textbf{{\\textit{{{esc(text)}}}}}")
            elif bold:
                out.append(f"\\textbf{{{esc(text)}}}")
            elif italic:
                out.append(f"\\textit{{{esc(text)}}}")
            else:
                out.append(esc(text))

            i = j

        return "".join(out)

    @staticmethod
    def _extract_braced_arg(src: str, brace_start_idx: int) -> Tuple[str, int]:
        """从 src[brace_start_idx]=='{' 开始提取配对花括号内容（支持嵌套）。"""
        if brace_start_idx < 0 or brace_start_idx >= len(src) or src[brace_start_idx] != "{":
            return "", brace_start_idx
        depth = 1
        i = brace_start_idx + 1
        start = i
        while i < len(src) and depth > 0:
            ch = src[i]
            if ch == "\\" and i + 1 < len(src):
                i += 2
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1
        if depth != 0:
            return "", brace_start_idx
        return src[start : i - 1], i

    @staticmethod
    def _parse(src: str, initial: _FmtState) -> List[Dict[str, Any]]:
        frags: List[Dict[str, Any]] = []
        stack: List[_FmtState] = [initial]
        buf: List[str] = []

        def flush() -> None:
            if not buf:
                return
            state = stack[-1]
            frags.append(
                {
                    "text": "".join(buf),
                    "bold": state.bold,
                    "italic": state.italic,
                    "underline": state.underline,
                }
            )
            buf.clear()

        i = 0
        while i < len(src):
            ch = src[i]

            if ch == "{":
                flush()
                stack.append(stack[-1])
                i += 1
                continue

            if ch == "}":
                flush()
                if len(stack) > 1:
                    stack.pop()
                i += 1
                continue

            if ch == "~":
                buf.append(" ")
                i += 1
                continue

            if ch != "\\":
                buf.append(ch)
                i += 1
                continue

            # 处理反斜杠：\\ 或 \command 或转义字符
            if i + 1 < len(src) and src[i + 1] == "\\":
                # 换行：当作空格（标题对齐不关心强制换行）
                buf.append(" ")
                i += 2
                continue

            if i + 1 >= len(src):
                i += 1
                continue

            # 命令名：字母串；否则视为转义字符（\% \_ \{ ...）
            if not src[i + 1].isalpha():
                buf.append(src[i + 1])
                i += 2
                continue

            j = i + 1
            while j < len(src) and src[j].isalpha():
                j += 1
            if j < len(src) and src[j] == "*":
                j += 1
            cmd = src[i + 1 : j]

            # 跳过命令后的空白
            k = j
            while k < len(src) and src[k].isspace():
                k += 1

            # 空白类命令
            if cmd in LatexFormatParser.SPACE_COMMANDS:
                buf.append(" ")
                i = k
                # 支持 \hspace{...} 这种带参数的空白命令：跳过其参数，但不输出
                if i < len(src) and src[i] == "{":
                    _, end_idx = LatexFormatParser._extract_braced_arg(src, i)
                    if end_idx > i:
                        i = end_idx
                continue

            # 换行类命令：输出一个空格，并跳过可选 {..}
            if cmd in LatexFormatParser.BREAK_COMMANDS:
                buf.append(" ")
                i = k
                if i < len(src) and src[i] == "{":
                    _, end_idx = LatexFormatParser._extract_braced_arg(src, i)
                    if end_idx > i:
                        i = end_idx
                continue

            # 包裹式命令：\textbf{...}
            if cmd in LatexFormatParser.WRAP_BOLD and k < len(src) and src[k] == "{":
                arg, end_idx = LatexFormatParser._extract_braced_arg(src, k)
                flush()
                frags.extend(LatexFormatParser._parse(arg, stack[-1].with_updates(bold=True)))
                i = end_idx
                continue

            if cmd in LatexFormatParser.WRAP_ITALIC and k < len(src) and src[k] == "{":
                arg, end_idx = LatexFormatParser._extract_braced_arg(src, k)
                flush()
                frags.extend(LatexFormatParser._parse(arg, stack[-1].with_updates(italic=True)))
                i = end_idx
                continue

            # 声明式命令：\bfseries / \itshape
            if cmd in LatexFormatParser.DECL_BOLD:
                flush()
                stack[-1] = stack[-1].with_updates(bold=True)
                i = k
                continue

            if cmd in LatexFormatParser.DECL_ITALIC:
                flush()
                stack[-1] = stack[-1].with_updates(italic=True)
                i = k
                continue

            # 其它未知命令：跳过命令 token，本体文字由后续花括号解析自然保留
            i = k

        flush()
        return frags

    @staticmethod
    def _merge_consecutive_fragments(fragments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not fragments:
            return []
        merged: List[Dict[str, Any]] = []
        for frag in fragments:
            text = str(frag.get("text", "") or "")
            if not text:
                continue
            cur = {
                "text": text,
                "bold": bool(frag.get("bold", False)),
                "italic": bool(frag.get("italic", False)),
                "underline": bool(frag.get("underline", False)),
            }
            if not merged:
                merged.append(cur)
                continue
            last = merged[-1]
            if (
                bool(last.get("bold")) == bool(cur.get("bold"))
                and bool(last.get("italic")) == bool(cur.get("italic"))
                and bool(last.get("underline")) == bool(cur.get("underline"))
            ):
                last["text"] += cur["text"]
            else:
                merged.append(cur)
        return merged

