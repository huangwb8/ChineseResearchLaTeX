# NSFC 面上项目申请书正文模板（2026 v2 模板对齐版）

国家自然科学基金面上项目申请书正文 LaTeX 模板，基于 **2026 年最新 v2 Word 模板**精确对齐。

## 模板特点

- ✅ **精确对齐 2026 v2 Word 模板**：页面边距、行距体系、标题格式完全对齐官方模板
- ✅ **版式优化**：加粗 `\section` 标题、优化标题与正文间距、收紧段落间距
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
NSFC_General/
├── main.tex                          # 主控文件（申请书入口）
├── extraTex/                         # 内容模板目录
│   ├── @config.tex                   # 配置文件（字体、格式、自定义命令）
│   │
│   ├── 第（一）部分 立项依据:
│   │   ├── 1.立项依据.tex            # 路由文件（写作指导）
│   │   └── 1.1.立项依据.tex          # 内容模板（背景/现状/问题/思路）
│   │
│   ├── 第（二）部分 研究内容:
│   │   ├── 2.研究内容.tex            # 路由文件（结构组织）
│   │   ├── 1.2.内容目标问题.tex      # 内容模板（研究内容/目标/问题）
│   │   ├── 1.3.研究方案.tex          # 内容模板（方法/路线/技术）
│   │   ├── 1.4.特色与创新.tex        # 内容模板（创新点）
│   │   └── 1.5.研究计划.tex          # 内容模板（年度计划/预期成果）
│   │
│   ├── 第（三）部分 研究基础:
│   │   ├── 3.1.研究基础与可行性分析.tex  # 内容模板（基础/成绩/可行性）
│   │   ├── 3.2.工作条件.tex          # 内容模板（实验条件/平台）
│   │   ├── 3.3.正在承担的与本项目相关的科研项目情况.tex
│   │   └── 3.4.完成国家自然科学基金项目情况.tex
│   │
│   └── 第（四）部分 其他需要说明的情况:
│       ├── 4.1.同年申请不同类型国基情况.tex
│       ├── 4.2.同年单位不一致.tex
│       ├── 4.3.承担中单位不一致.tex
│       ├── 4.4.不同专业技术职务的申请.tex
│       ├── 4.5.生成式人工智能使用情况.tex
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
   - `1.1.xxx.tex`, `1.2.xxx.tex`：详细内容模板文件
   - `@config.tex`：配置文件（一般无需修改）

### 内容填写建议

#### 第（一）部分 立项依据

文件：[extraTex/1.1.立项依据.tex](extraTex/1.1.立项依据.tex)

**写作顺序**：背景/意义 → 国内外现状与不足 → 关键科学问题 → 研究思路与预期贡献

#### 第（二）部分 研究内容

文件：
- [1.2.内容目标问题.tex](extraTex/1.2.内容目标问题.tex)：研究内容 + 目标 + 关键问题
- [1.3.研究方案.tex](extraTex/1.3.研究方案.tex)：研究方法 + 技术路线 + 关键技术
- [1.4.特色与创新.tex](extraTex/1.4.特色与创新.tex)：创新点（1-2 条高含金量）
- [1.5.研究计划.tex](extraTex/1.5.研究计划.tex)：年度计划 + 预期成果

#### 第（三）部分 研究基础

文件：
- [3.1.研究基础与可行性分析.tex](extraTex/3.1.研究基础与可行性分析.tex)：研究基础 + 成绩 + 可行性
- [3.2.工作条件.tex](extraTex/3.2.工作条件.tex)：实验条件和平台

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

## 格式要求

### 字体与字号

- 标题：自动应用模板样式
- 正文：小四号（12pt）
- 首行缩进：2 字符

### 页面设置

- 纸张：A4
- 页数：原则上不超过 30 页
- 边距：符合 NSFC 默认要求

### 标题换行

对于需要精确控制换行的长标题，使用 `\linebreak{}`：

```latex
\subsection{2. 工作条件（包括已具备的实验条件，尚缺少的实验条件和拟\linebreak{}解决的途径...）}
```

## 资源文件使用

### 📁 文件夹结构

```
NSFC_General/
├── code/              # 代码示例目录
│   └── test.sh        # Bash 脚本示例
├── figures/           # 图片资源目录
│   ├── zzmx-115.jpg
│   └── zzmx-mobile-105.jpg
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

**示例 1：研究现状图**（见 [1.1.立项依据.tex](extraTex/1.1.立项依据.tex)）

```latex
\begin{figure}[!th]
    \begin{center}
        \includegraphics[width=0.8\linewidth]{figures/zzmx-115.jpg}
        \caption{研究现状示意图。\\
        \raggedright \justifying \noindent
        图片说明文字应清晰描述图片内容，并与正文相互呼应。}
        \label{fig:research-status}
    \end{center}
\end{figure}

% 在正文中引用图片
如图 \ref{fig:research-status} 所示...
```

**示例 2：理论框架设计图**（见 [1.2.内容目标问题.tex](extraTex/1.2.内容目标问题.tex)）

```latex
\begin{figure}[!th]
    \begin{center}
        \includegraphics[width=0.8\linewidth]{figures/zzmx-mobile-105.jpg}
        \caption{理论框架设计示意图。\\
        \raggedright \justifying \noindent
        本图展示了研究内容1中理论框架的构建思路。}
        \label{fig:framework-design}
    \end{center}
\end{figure}
```

**支持的图片格式**：`.jpg`, `.png`, `.pdf`, `.eps`

**说明**：模板中已包含两个图片示例，分别在不同章节中展示不同类型的图示用途。

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

**说明**：模板中已包含一个详细的临床特征统计分析表示例（table1），展示了复杂表格的排版效果。

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

**复杂表示例**：参见 [1.1.立项依据.tex](extraTex/1.1.立项依据.tex) 中的临床特征统计分析表，包含多维度数据（性别、年龄、病理分期、MSI 状态等）。

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

- **页面边距精确对齐**：右/上/下边距严格对齐 `template/2026年最新word模板-1.面上项目-正文-v2.pdf`
- **版式间距优化**：
  - 加粗 `\section` 标题，提升视觉层次
  - 调整 `\section` 缩进到 2em，与 Word 模板一致
  - 增大"提纲提示语"与首个 `\section` 之间的垂直间距
  - 对部分 `\subsection` 标题内关键词加粗
  - 减小"（四）其他需要说明的情况"与首个 `\subsection` 之间的局部空白
- **标题换行控制**：使用 `\linebreak{}` 精确控制长标题断行，更贴近 Word 模板观感
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
