# NSFC 青年科学基金项目申请书正文模板（2026 v2 模板对齐版）

国家自然科学基金青年科学基金项目申请书正文 LaTeX 模板，基于 **2026 年最新 v2 Word 模板**精确对齐。

## 模板特点

- ✅ **精确对齐 2026 v2 Word 模板**：页面边距、行距体系、标题格式完全对齐官方模板
- ✅ **版式优化**：加粗 `\section` 标题、优化标题与正文间距、收紧段落间距、固定行距 22pt/段后 7.8pt
- ✅ 正文原则上不超过 30 页
- ✅ 提纲不做限制，按研究逻辑灵活撰写
- ✅ 结构化的内容模板，便于快速上手
- ✅ 双层文件结构，写作指导与内容模板分离

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
- **系统**：macOS / Windows / Linux
- **平台**：本地编辑器（VSCode + TeXLive）或 Overleaf

## 文件结构

```
NSFC_Young/
├── main.tex                          # 主控文件（申请书入口）
├── extraTex/                         # 内容模板目录
│   ├── @config.tex                   # 配置文件（字体、格式、自定义命令）
│   │
│   ├── 第（一）部分 立项依据:
│   │   └── 1.1.立项依据.tex          # 内容模板（背景/现状/问题/思路）
│   │
│   ├── 第（二）部分 研究内容:
│   │   ├── 2.1.研究内容.tex          # 内容模板（研究内容/目标）
│   │   ├── 2.2.特色与创新.tex        # 内容模板（创新点）
│   │   └── 2.3.年度研究计划.tex      # 内容模板（年度计划/预期成果）
│   │
│   ├── 第（三）部分 研究基础:
│   │   ├── 3.1.研究基础.tex          # 内容模板（基础/成绩/可行性）
│   │   ├── 3.2.工作条件.tex          # 内容模板（实验条件/平台）
│   │   ├── 3.3.承担项目情况.tex      # 正在承担的科研项目
│   │   └── 3.4.完成国基项目情况.tex  # 已完成的国基项目
│   │
│   └── 第（四）部分 其他说明:
│       ├── 4.1.不同类型国基情况.tex
│       ├── 4.2.同年单位不一致.tex
│       ├── 4.3.承担中单位不一致.tex
│       ├── 4.4.不同专业技术职务的申请.tex
│       └── 4.6.其他.tex
│
├── references/                       # 参考文献目录
├── figures/                          # 图片目录
├── bibtex-style/                     # BibTeX 样式目录
└── fonts/                            # 字体目录
```

## 使用指南

### 快速开始

1. **直接编辑内容模板文件**
   - 打开 `extraTex/1.1.立项依据.tex` 等文件
   - 按照模板中的注释和 `\NSFCBlankPara` 占位符填写内容
   - 编译 `main.tex` 生成 PDF

2. **文件命名说明**
   - `1.xxx.tex`, `2.xxx.tex`：对应申请书的主要部分
   - `2.1.xxx.tex`, `2.2.xxx.tex`：详细内容模板文件
   - `@config.tex`：配置文件（一般无需修改）

### 内容填写建议

#### 第（一）部分 立项依据

文件：[extraTex/1.1.立项依据.tex](extraTex/1.1.立项依据.tex)

**写作顺序**：背景/意义 → 国内外现状与不足 → 关键科学问题 → 研究思路与预期贡献

#### 第（二）部分 研究内容

文件：
- [2.1.研究内容.tex](extraTex/2.1.研究内容.tex)：研究内容 + 目标
- [2.2.特色与创新.tex](extraTex/2.2.特色与创新.tex)：创新点（1-2 条高含金量）
- [2.3.年度研究计划.tex](extraTex/2.3.年度研究计划.tex)：年度计划 + 预期成果

#### 第（三）部分 研究基础

文件：
- [3.1.研究基础.tex](extraTex/3.1.研究基础.tex)：研究基础 + 成绩 + 可行性
- [3.2.工作条件.tex](extraTex/3.2.工作条件.tex)：实验条件和平台
- [3.3.承担项目情况.tex](extraTex/3.3.承担项目情况.tex)：正在承担的科研项目
- [3.4.完成国基项目情况.tex](extraTex/3.4.完成国基项目情况.tex)：已完成的国基项目情况

#### 第（四）部分 其他说明

根据实际情况填写 4.1-4.6 各项声明文件。

### 常用命令

```latex
% 空白段落占位符（内容填写后可删除）
\NSFCBlankPara

% 列表项标题
\item \itemtitlefont{标题：}内容...

% 子标题
\subsubsection{标题}

% 第 4 层标题（需要时使用）
\subsubsubsection{标题}
```

## 样式微调指南

本节介绍如何根据个人需求微调模板样式。所有样式配置集中在 [`extraTex/@config.tex`](extraTex/@config.tex) 文件中。

### 行距与段落间距

**当前设置**：
- 固定行距：22pt
- 段间距：紧凑模式（默认 `\parskip=0pt`；正文区块由 `\NSFCBodyText` 再次显式设为 `0pt`）

**微调方法**：

```latex
% 在 extraTex/@config.tex 的“行距”段落修改
% 固定行距：第二个参数（本模板默认对齐 Word：22pt）
\AtBeginDocument{\fontsize{12pt}{22pt}\selectfont\frenchspacing}

% 全局段间距（不推荐改；如改动，注意正文区块的 \NSFCBodyText 可能会覆盖）
\setlength{\parskip}{0pt}
```

**常见调整**：

| 需求 | 修改方式 | 效果 |
|------|----------|------|
| 更紧凑 | `\setlength{\parskip}{0pt}` 或 `{1pt}` | 段落间隙更小 |
| 更宽松 | `\setlength{\parskip}{5pt}` 或 `{8pt}` | 段落间隙更大 |
| 行距增大 | `\fontsize{12pt}{24pt}` | 固定行距 24pt |

> 提示：正文内容文件（`extraTex/*.tex`）建议在开头使用 `\justifying` + `\NSFCBodyText`，以启用“两端对齐 + 2em 段首缩进”，并避免正文段间距受其它区域影响。

### 参考文献间距（标题/条目/行距）

参考文献的间距分两层控制：

1. **标题与上文/标题与条目/条目间距**：通过以下长度参数控制（默认值定义在 `extraTex/@config.tex`；推荐在 `references/reference.tex` 用 `\setlength` 覆盖）：
   - `\NSFCBibTitleAboveSkip`：进入参考文献块前的额外垂直距离
   - `\NSFCBibTitleBelowSkip`：标题后到第一条条目的额外距离
   - `\NSFCBibItemSep`：条目之间的间距（`thebibliography` 的 `\itemsep`）
   - （可选）`\NSFCBibTextWidth`：条目有效行宽（影响换行；用于跨项目对齐）

   例：在 `references/reference.tex` 的 `\bibliographystyle/\bibliography` 之前加入：

   ```latex
   % references/reference.tex
   \setlength{\NSFCBibTitleAboveSkip}{10pt}
   \setlength{\NSFCBibTitleBelowSkip}{10pt}
   \setlength{\NSFCBibItemSep}{2pt}
   % \setlength{\NSFCBibTextWidth}{380pt} % 需要时再改（会影响换行）
   ```

2. **参考文献内部行距**：由 `references/reference.tex` 中的 `\begin{spacing}{...}` 控制；把 `1` 改为 `0.95/1.05` 等即可（这不是条目间距）。

### 标题间距

**当前设置**（以 `extraTex/@config.tex` 为准）：

```latex
% section / subsection / subsubsection / subsubsubsection 的标题前后间距
\titlespacing*{\section}{0pt}{2pt plus 0pt minus 0pt}{1.5pt}
\titlespacing*{\subsection}{0pt}{1.5pt plus 0pt minus 0pt}{5pt}
\titlespacing*{\subsubsection}{0pt}{3pt plus 0pt minus 0pt}{2pt plus 0pt minus 0pt}
\titlespacing*{\subsubsubsection}{0pt}{0pt plus 0pt minus 0pt}{0pt plus 0pt minus 0pt}
```

**微调说明**：
- 第一个 `{0pt}`：左缩进
- 第二个 `{0pt}`：标题前间距
- 第三个 `{Xpt}`：标题后间距（设为负值可收紧）

**示例**：

```latex
% 让 subsubsubsection 更“像小标题”，上下留白更多
\titlespacing*{\subsubsubsection}{0pt}{4pt}{2pt}
```

> 更低层级说明：
> - 模板提供 `\subsubsubsection{...}` 作为第 4 层标题；
> - 若你需要更低层级（“第 5 层”及以下），常见做法是使用 `\paragraph/\subparagraph` 并配合 `titlesec` 自定义 `\titleformat` + `\titlespacing*`；
> - 模板也提供 `\ssssubtitle{1}` 这种“圈号小标题”作为行内标题，若要控制其上下间距，建议在使用处配合 `\vspace{...}` 或封装一个带 `\vspace` 的新命令来统一管理。

### 标题字体与大小

**当前设置**（第 172-174 行）：

```latex
\newcommand{\sectionzihao}{\fontsize{14pt}{22pt}\selectfont}      % 四号
\newcommand{\subsectionzihao}{\fontsize{14pt}{22pt}\selectfont}   % 四号
\newcommand{\subsubsectionzihao}{\fontsize{13.5pt}{20pt}\selectfont}  % 近小四
```

**微调示例**：

```latex
% 改大 section 字号
\newcommand{\sectionzihao}{\fontsize{16pt}{24pt}\selectfont}  % 二号

% 改小 subsection 字号
\newcommand{\subsectionzihao}{\fontsize{12pt}{22pt}\selectfont}  % 小四
```

### 正文字体

**当前设置**（第 76-92 行）：

| 系统 | 中文字体 | 英文字体 |
|------|----------|----------|
| macOS | Kaiti（楷体） | Times New Roman |
| Windows | KaiTi（楷体） | Times New Roman |

**更换字体示例**：

```latex
% macOS 下改用宋体
\setCJKmainfont[Path=./fonts/, Extension=.ttf, AutoFakeBold=3]{SimSun}

% Windows 下改用黑体
\setCJKmainfont{SimHei}[AutoFakeBold=3]
```

**字号对照表**（第 49-67 行）：

| 命令 | 字号 | 用途 |
|------|------|------|
| `\erhao` | 22pt | 二号 |
| `\sanhao` | 16pt | 三号 |
| `\sihao` | 14pt | 四号 |
| `\xiaosihao` | 12pt | 小四（正文默认） |
| `\wuhao` | 10.5pt | 五号 |

### 标题颜色

**当前设置**：蓝色 `MsBlue`（RGB: 0,113,192）

**修改颜色**（第 31 行）：

```latex
% 改为黑色
\definecolor{MsBlue}{RGB}{0,0,0}

% 改为深灰
\definecolor{MsBlue}{RGB}{64,64,64}

% 改为自定义颜色
\definecolor{MsBlue}{RGB}{128,0,128}  % 紫色
```

### 标题格式

**取消加粗**（第 178、192 行）：

```latex
% section 不加粗
\titleformat{\section}
  {\color{MsBlue} \sectionzihao \templatefont}  % 去掉 \bfseries
  {\hspace*{2em}}
  {0pt}
  {}
```

**修改缩进**（第 179、188 行）：

```latex
% 调整 section 缩进
\titleformat{\section}
  {...}
  {\hspace*{0em}}  % 改为 0（不缩进）
  ...
```

### 列表格式

**当前设置**（第 120-129 行）：

```latex
\setlist[enumerate]{
  label={\templatefont \bfseries \hspace{1em} \color{MsBlue}（\arabic*）},
  leftmargin=0em,      % 左边界
  itemindent=4em,      % 首行缩进
  itemsep=0em,         % 列表项间距
  ...
}
```

#### 如何调整/自定义序号样式（enumerate 编号）

本模板的“序号样式”由 `extraTex/@config.tex` 中 `\setlist[enumerate]{...}` 的 `label=...` 控制（默认是蓝色加粗的 `（1）` 风格）。

**全局修改（推荐）**：在 `extraTex/@config.tex` 找到类似这一行并改动 `label`：

```latex
\setlist[enumerate]{
  label={\templatefont \bfseries \hspace{1em} \color{MsBlue}（\arabic*）},
  ...
}
```

常见改法（只改 `（\arabic*）` 这一段即可）：

```latex
label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\arabic*)}              % 1)
label={\templatefont \bfseries \hspace{1em} \color{MsBlue}\arabic*.}              % 1.
label={\templatefont \bfseries \hspace{1em} \color{MsBlue}(\alph*)}               % (a)
\setlist[enumerate,1]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}（\chinese{enumi}）}} % （一）
\setlist[enumerate,2]{label={\templatefont \bfseries \hspace{1em} \color{MsBlue}（\arabic{enumii}）}} % （1）(二级)
```

**三套常用“多级序号组合”（复制即用）**：适合有嵌套列表（`enumerate` 里再 `enumerate`）的情况。把其中一套粘贴到 `extraTex/@config.tex`（放在 `\setlist[enumerate]{...}` 之后即可）。

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

**局部修改（只影响某一个列表）**：在正文里对单个 `enumerate` 加可选参数覆盖：

```latex
\begin{enumerate}[label=(\roman*), leftmargin=0em, itemindent=4em, itemsep=0em]
  \item ...
  \item ...
\end{enumerate}
```

**缩进对齐提示**：如果改了 `label` 后出现“编号挤压/正文不齐”，优先微调 `itemindent`（首行缩进）或 `labelsep`（编号与正文间距）。

**微调示例**：

```latex
% 减小缩进
\setlist[enumerate]{
  leftmargin=0em,
  itemindent=2em,  % 改为 2em
  ...
}

% 增大列表项间距
\setlist[enumerate]{
  ...
  itemsep=5pt,  % 改为 5pt
  ...
}
```

### 页面边距

**当前设置**（第 24 行）：

```latex
\geometry{left=3.20cm,right=3.20cm,top=2.54cm,bottom=2.54cm}
```

**微调示例**：

```latex
% 更窄的左右边距（节省空间）
\geometry{left=2.8cm,right=2.8cm,top=2.54cm,bottom=2.54cm}

% 更大的上下边距
\geometry{left=3.20cm,right=3.20cm,top=3cm,bottom=3cm}
```

### 快速微调清单

| 想要... | 修改位置 | 参数 |
|---------|----------|------|
| 行距更大 | 第 99 行 | `\fontsize{12pt}{24pt}` |
| 段落更紧凑 | 第 101 行 | `\setlength{\parskip}{0pt}` |
| 标题更大 | 第 172-174 行 | 调整 `\fontsize{Xpt}{Ypt}` |
| 标题间距更小 | 第 213-234 行 | 减小第三个参数 |
| 改字体颜色 | 第 31 行 | 修改 `MsBlue` 定义 |
| 标题不加粗 | 第 178、192 行 | 去掉 `\bfseries` |

> **提示**：修改后建议先编译查看效果，如需大幅调整请先备份原文件。

## 格式要求

### 字体与字号

- 标题：自动应用模板样式
- 正文：小四号（12pt）
- 首行缩进：2 字符

### 页面设置

- 纸张：A4
- 页数：原则上不超过 30 页
- 边距：左右 3.20cm，上下 2.54cm（对齐 2026 v2 Word 模板）

### 行距设置

- 固定行距：22pt
- 段间距：默认紧凑（`\\parskip=0pt`；正文区块由 `\\NSFCBodyText` 控制段首缩进与段间距）
- `\frenchspacing`：英文标点间距优化

### 标题换行

对于需要精确控制换行的长标题，使用 `\linebreak{}`：

```latex
\subsection{（提纲不做限制，请按照研究工作的自身逻辑撰写。应提炼出特\linebreak{}色与创新点、年度研究计划）}
```

## 资源文件使用

### 📁 文件夹结构

```
NSFC_Young/
├── code/              # 代码示例目录
├── figures/           # 图片资源目录
└── references/        # 参考文献目录
    ├── myexample.bib  # BibTeX 参考文献数据库
    └── reference.tex  # 参考文献样式文件
```

### 📝 参考文献引用

**步骤**：

1. 在 `references/myexample.bib` 中维护参考文献条目
2. 在正文中使用 `\cite{key}` 引用
3. 参考文献已在 `main.tex` 中通过 `\input{references/reference.tex}` 引用
4. 完整编译顺序：`xelatex -> bibtex -> xelatex -> xelatex`

**说明**：参考文献会显示在第（一）部分立项依据之后。

**示例**：

```latex
% 在正文中引用
已有研究表明... \cite{Smith1900}
多项研究证实... \cite{Smith1900,Piter1992,John1997}
```

### 🖼️ 图片插入

**步骤**：

1. 将图片放入 `figures/` 目录
2. 使用以下代码插入图片

**示例**：

```latex
\begin{figure}[!th]
    \begin{center}
        \includegraphics[width=0.8\linewidth]{figures/example.jpg}
        \caption{研究现状示意图。\\
        \raggedright \justifying \noindent
        图片说明文字应清晰描述图片内容，并与正文相互呼应。}
        \label{fig:example}
    \end{center}
\end{figure}

% 在正文中引用图片
如图 \ref{fig:example} 所示...
```

**支持的图片格式**：`.jpg`, `.png`, `.pdf`, `.eps`

### 💻 代码插入

**步骤**：

1. 将代码文件放入 `code/` 目录
2. 使用 `\lstinputlisting` 引用代码文件

**示例**：

```latex
\subsubsection{关键算法实现}
% 引用 Bash 脚本
\lstinputlisting[style=codestyle01, language=Bash]{code/test.sh}

% 或直接在文档中嵌入代码
\begin{lstlisting}[language=Python]
def hello():
    print("Hello, NSFC!")
\end{lstlisting}
```

**支持的代码语言**：`Python`, `Bash`, `R`, `C++`, `Java` 等

### 📊 表格插入

**简单表示例**：

```latex
\begin{table}[htbp]
    \centering
    \caption{\textbf{研究现状对比表}}
    \begin{tabular}{llll}
    \toprule
    方法 & 优势 & 不足 & 适用场景 \\
    \midrule
    方法A & 优势1 & 不足1 & 场景1 \\
    方法B & 优势2 & 不足2 & 场景2 \\
    \bottomrule
    \end{tabular}
    \label{tab:method-comparison}
\end{table}

% 在正文中引用表格
如表 \ref{tab:method-comparison} 所示...
```

### 🔗 交叉引用

使用 `\label{}` 和 `\ref{}` 实现图表、公式、章节的交叉引用：

```latex
\section{研究方法}\label{sec:methods}
如图 \ref{fig:example} 所示，表 \ref{tab:data} 列出了...
```

## 常见问题

### Q1：编译时报错找不到字体

**解决方案**：
- macOS：系统自带字体，无需额外安装
- Windows：确保安装了 CTex 宏包所需的字体
- Overleaf：直接使用，无需配置

### Q2：参考文献显示为问号

**解决方案**：
- 确保按顺序编译：`xelatex -> bibtex -> xelatex -> xelatex`
- 检查 `.bib` 文件路径是否正确

### Q3：超出 30 页限制

**解决方案**：
- 使用 `\NSFCBlankPara` 占位符在填写前控制篇幅
- 填写后适当精简，保持简洁表达
- 利用 `\vspace{-0.5em}` 等微调间距（谨慎使用）

## 更新日志

### v3.2.x - 2026 年 v2 模板对齐

**核心变更**：基于 2026 年最新 v2 Word 模板重新校准

- **页面边距精确对齐**：左右 3.20cm、上下 2.54cm，严格对齐 `template/2026年最新word模板-青年科学基金项目（C类）-正文-v2.pdf`
- **正文行距体系改进**：
  - 固定行距：22pt
  - 段后间距：7.8pt
  - 启用 `\frenchspacing` 优化英文标点间距
- **版式间距优化**：
  - 加粗 `\section` 标题，提升视觉层次
  - 调整 `\section` 缩进到 2em，与 Word 模板一致
  - 增大"提纲提示语"与首个 `\section` 之间的垂直间距
  - 减小 `\section` 与 `\subsection` 的间隙
  - 进一步收紧段落间距（含 `\subsubsection` 后首段）
  - 避免 `\indent` 形成空段落造成额外空白
- **标题换行控制**：使用 `\linebreak{}` 精确控制长标题断行，更贴近 Word 模板观感
- **提纲标题调整**：按 v2 模板将"其他需要说明的情况"收敛为 `5. 其他。`
- **生成式 AI 说明章节**：v2 模板已删除官方强制要求，但保留模板文件供自愿披露使用

完整变更记录参见项目根目录 [CHANGELOG.md](../../CHANGELOG.md)

## 关于生成式人工智能使用说明

> **重要说明**：2026 年 v2 模板已删除"生成式人工智能使用情况"的强制填报要求。这并非反对使用 AI 工具辅助科研写作，而是为了减轻申请人的思想负担。

**本模板的处理方式**：
- 保留 `extraTex/4.5.生成式人工智能.tex` 模板文件（未被 `main.tex` 引用）
- 如您愿意主动披露 AI 使用情况，可在 `main.tex` 中取消注释：
  ```latex
  % \input{extraTex/4.5.生成式人工智能.tex}
  ```
- 如无需披露，保持当前状态即可（已符合 v2 模板要求）

**官方态度解读**：
- ❌ 不再强制要求披露 AI 使用情况 ≠ 禁止使用 AI
- ✅ 鼓励合理利用 AI 工具提升科研写作效率
- ⚠️ 仍需对研究内容的真实性和原创性负责

**建议**：
- 使用 AI 辅助语言润色、格式调整、文献管理等机械性工作是安全的
- 涉及核心科学观点、创新点提炼、研究设计等关键内容应由申请人主导
- 本项目的 [AI 技能体系](../../skills/) 正是为这种人机协作模式而设计

## 许可证

本项目遵循项目根目录的 [license.txt](../../license.txt)

## 致谢

本模板参考了以下优秀的开源项目：
- [Ruzim/NSFC-application-template-latex](https://github.com/Ruzim/NSFC-application-template-latex)
- [Readon/NSFC-application-template-latex](https://github.com/Readon/NSFC-application-template-latex)

---

**祝您申请顺利！** 🎉
