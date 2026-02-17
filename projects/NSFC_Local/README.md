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
- 模板也提供 `\ssssubtitle{1}` 这种"圈号小标题"作为行内标题；若要统一控制其上下间距，建议封装一个带 `\vspace{...}` 的新命令来管理。

### 标题编号样式

标题编号由 `extraTex/@config.tex` 的"标题计数"区域控制（`\titleformat` 的 label 参数 + `\renewcommand\theXXX`）。

**当前默认编号**：

| 层级 | 命令 | 编号样式 | 示例 |
|------|------|----------|------|
| section | `\section` | 无自动编号（正文手写） | （一）立项依据 |
| subsection | `\subsection` | 无自动编号（正文手写） | 1. 研究意义 |
| subsubsection | `\subsubsection` | `\arabic{subsection}.\arabic{subsubsection}` | 1.1 |
| subsubsubsection | `\subsubsubsection` | `（\arabic{subsubsubsection}）` | （1） |

**自定义 subsubsection 编号**（第 201-206 行）：

```latex
% 默认：1.1 风格
\titleformat{\subsubsection}
  {\color{MsBlue} \subsubsectionzihao \templatefont \bfseries}
  {\hspace{1.1em}  \textnormal{\templatefont \arabic{subsection}.\arabic{subsubsection}}}
  {0.5em}
  {}
\renewcommand\thesubsubsection{\arabic{subsection}.\arabic{subsubsection}}
```

**自定义 subsubsubsection 编号**（第 208-215 行）：

```latex
% 默认：（1）风格
\renewcommand\thesubsubsubsection{（\arabic{subsubsubsection}）}
\titleformat{\subsubsubsection}
  {\templatefont \bfseries}
  {\hspace{1em} （\arabic{subsubsubsection}）}
  {0.5pt}
  {}
```

**常见替换方案**：

```latex
% 方案 A：三级层级编号（1.1 → 1.1.1）
% 修改 subsubsubsection 的 label 和 \theXXX
\renewcommand\thesubsubsubsection{\arabic{subsection}.\arabic{subsubsection}.\arabic{subsubsubsection}}
\titleformat{\subsubsubsection}
  {\templatefont \bfseries}
  {\hspace{1em} \textnormal{\templatefont \arabic{subsection}.\arabic{subsubsection}.\arabic{subsubsubsection}}}
  {0.5pt}
  {}
```

```latex
% 方案 B：纯数字递进（1) → a) → i)）
\renewcommand\thesubsubsubsection{\alph{subsubsubsection})}
\titleformat{\subsubsubsection}
  {\templatefont \bfseries}
  {\hspace{1em} \alph{subsubsubsection})}
  {0.5pt}
  {}
```

> 注意：修改编号样式时，`\titleformat` 的 label 参数（控制显示）和 `\renewcommand\theXXX`（控制交叉引用）需要同步修改，否则 `\ref{}` 引用会与显示不一致。

## 列表格式与序号样式（enumerate）

本模板的列表样式统一在 `extraTex/@config.tex` 中配置，核心入口是：

```latex
\setlist[enumerate]{
  label={\templatefont \bfseries \hspace{1em} \color{MsBlue}（\arabic*）},
  leftmargin=0em,
  itemindent=4em,
  itemsep=0em,
  ...
}
```

### 如何调整/自定义序号样式

把 `label=...` 改成你想要的“序号外观”即可（建议只改末尾的 `（\arabic*）` 部分，保留前面的字体/颜色设置）。

常见样式示例：

```latex
label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\arabic*)}              % 1)
label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\arabic*.}              % 1.
label={\templatefont \bfseries \hspace{1em} \color{MsBlue}(\alph*)}               % (a)
\setlist[enumerate,1]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}（\chinese{enumi}）}} % （一）
\setlist[enumerate,2]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}（\arabic{enumii}）}} % （1）(二级)
```

**三套常用"多级序号组合"（复制即用）**：适合有嵌套列表（`enumerate` 里再 `enumerate`）的情况。把其中一套粘贴到 `extraTex/@config.tex`（放在 `\setlist[enumerate]{...}` 之后即可）。

```latex
% 组合 A：中文标书常见（（一）→ 1. → （1）→ a)）
\setlist[enumerate,1]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}（\chinese{enumi}）}}
\setlist[enumerate,2]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\arabic{enumii}.}}
\setlist[enumerate,3]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}（\arabic{enumiii}）}}
\setlist[enumerate,4]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\alph{enumiv})}}
```

```latex
% 组合 B：英文论文常见（1. → (a) → (i) → 1)）
\setlist[enumerate,1]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\arabic{enumi}.}}
\setlist[enumerate,2]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}(\alph{enumii})}}
\setlist[enumerate,3]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}(\roman{enumiii})}}
\setlist[enumerate,4]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\arabic{enumiv})}}
```

```latex
% 组合 C：简洁括号风（1) → (1) → a) → i)）
\setlist[enumerate,1]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\arabic{enumi})}}
\setlist[enumerate,2]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}(\arabic{enumii})}}
\setlist[enumerate,3]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\alph{enumiii})}}
\setlist[enumerate,4]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\roman{enumiv})}}
```

### 局部覆盖（只影响某一个列表）

正文里对单个 `enumerate` 加可选参数即可：

```latex
\begin{enumerate}[label=(\roman*), leftmargin=0em, itemindent=4em, itemsep=0em]
  \item ...
  \item ...
\end{enumerate}
```

### 缩进对齐提示

改了 `label` 后如果出现“编号挤压/正文不齐”，优先微调 `itemindent`（首行缩进）或 `labelsep`（编号与正文间距）。
