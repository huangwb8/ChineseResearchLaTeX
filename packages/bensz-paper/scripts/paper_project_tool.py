#!/usr/bin/env python3
r"""SCI 论文构建工具入口（薄封装）。

本文件是 bensz-paper 公共包的命令行入口点，实际构建逻辑
全部委托给 manuscript_tool.main()。支持的命令：

    python paper_project_tool.py build --project-dir <项目路径>
    python paper_project_tool.py count-words <tex-1> [<tex-2> ...]

构建输出：
- PDF：XeLaTeX + Biber 标准学术排版
- DOCX：LaTeX → Markdown → HTML5+MathML → DOCX 多步转换

字数统计输出：
- 递归跟随 ``main.tex`` / ``\input`` / ``\include`` 链
- 只统计渲染后可见文本，忽略 LaTeX 命令名、引用 keys 与数学公式源码

详见 manuscript_tool.py 的模块级文档与各函数 docstring。
"""
from __future__ import annotations

from manuscript_tool import main


if __name__ == "__main__":
    main()
