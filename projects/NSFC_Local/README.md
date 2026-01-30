# NSFC 地区科学基金项目申请书正文模板（2026 v2 模板对齐版）

国家自然科学基金地区科学基金项目申请书正文 LaTeX 模板，基于 **2026 年最新 v2 Word 模板**精确对齐。

## 编译说明

### 推荐编译顺序

```bash
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

### 编译环境

- **引擎**：XeLaTeX
- **编码**：UTF-8
- **平台**：本地编辑器（VSCode + TeXLive）或 Overleaf

## 文件结构

```
NSFC_Local/
├── main.tex                          # 主控文件（申请书入口）
├── extraTex/                         # 正文内容文件
│   ├── @config.tex                   # 样式配置（字体/行距/标题/参考文献参数等）
│   ├── 1.1.立项依据.tex
│   ├── 1.2.内容目标问题.tex
│   ├── 1.3.方案及可行性.tex
│   ├── 1.4.特色与创新.tex
│   ├── 1.5.研究计划.tex
│   ├── 2.1.研究基础.tex
│   ├── 2.2.工作条件.tex
│   ├── 2.3.承担项目.tex
│   ├── 2.4.项目完成情况.tex
│   └── 3.*.tex                       # 其他说明（按需填写）
├── references/                       # 参考文献
│   ├── myexample.bib
│   └── reference.tex                 # 参考文献渲染入口（建议在此覆盖间距参数）
├── figures/                          # 图片目录
├── bibtex-style/                     # BibTeX 样式（gbt7714-nsfc）
└── fonts/                            # 字体目录
```

## 使用指南

### 快速开始

1. 编辑 `extraTex/*.tex` 填写正文内容（各文件对应 `main.tex` 中的提纲位置）。
2. 正文文件开头建议使用：

```latex
\justifying
\NSFCBodyText
```

3. 编译 `main.tex` 生成 PDF（参考文献修改后建议跑完整 4 步编译）。

## 间距设置（重点）

本模板的“正文间距 / 参考文献间距 / 深层标题间距”均已在配置中预留了可调入口；推荐按下述方式修改，避免改散到各处导致升级困难。

### 设置正文间距（行距/段间距）

位置：`extraTex/@config.tex` 的“行距”段落。

- 固定行距：由 `\AtBeginDocument{\fontsize{12pt}{22pt}\selectfont...}` 的第二个参数控制（默认 22pt，对齐 Word）。
- 段间距：全局默认 `\parskip=0pt`；正文区块通常由 `\NSFCBodyText` 再次显式设为 `0pt`。

常见调整示例：

```latex
% 固定行距从 22pt 调到 24pt（会影响与 Word 的像素级对齐）
\AtBeginDocument{\fontsize{12pt}{24pt}\selectfont\frenchspacing}

% 如确实需要正文段后距（注意：\NSFCBodyText 也需要同步改）
\setlength{\parskip}{3pt}
```

### 设置参考文献间距（标题/条目/行距）

参考文献的间距分两层控制：

1. **标题与上文/标题与条目/条目间距**：通过以下长度参数控制（默认值定义在 `extraTex/@config.tex`；推荐在 `references/reference.tex` 用 `\setlength` 覆盖）：
   - `\NSFCBibTitleAboveSkip`
   - `\NSFCBibTitleBelowSkip`
   - `\NSFCBibItemSep`
   - （可选）`\NSFCBibTextWidth`（影响换行；用于跨项目对齐）

   例：在 `references/reference.tex` 的 `\bibliographystyle/\bibliography` 之前加入：

```latex
% references/reference.tex
\setlength{\NSFCBibTitleAboveSkip}{10pt}
\setlength{\NSFCBibTitleBelowSkip}{10pt}
\setlength{\NSFCBibItemSep}{2pt}
% \setlength{\NSFCBibTextWidth}{380pt} % 需要时再改（会影响换行）
```

2. **参考文献内部行距**：由 `references/reference.tex` 中的 `\begin{spacing}{...}` 控制；把 `1` 改为 `0.95/1.05` 等即可（这不是条目间距）。

### 设置 subsubsubsection 及更低层级的间距

位置：`extraTex/@config.tex` 的 `titlesec` 配置段落（`\\titlespacing*{...}`）。

模板提供 `\subsubsubsection{...}` 作为第 4 层标题，其前后间距由：

```latex
\titlespacing*{\subsubsubsection}{0pt}{0pt plus 0pt minus 0pt}{0pt plus 0pt minus 0pt}
```

控制。常见调整示例：

```latex
% 让 subsubsubsection 上下留白更多
\titlespacing*{\subsubsubsection}{0pt}{4pt}{2pt}
```

更低层级说明：

- 若需要“第 5 层”及以下，建议使用 `\paragraph/\subparagraph` 并配合 `titlesec` 自定义 `\titleformat` + `\titlespacing*`。
- 模板也提供 `\ssssubtitle{1}` 这种“圈号小标题”作为行内标题；若要统一控制其上下间距，建议封装一个带 `\vspace{...}` 的新命令来管理。

