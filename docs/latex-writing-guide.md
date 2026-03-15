# LaTeX 写作指南

本指南提供 LaTeX 写作的常用命令和最佳实践。

## 基本文档结构

```latex
\documentclass[12pt,a4paper]{article}
\usepackage[UTF8]{ctex}  % 中文支持

\begin{document}
\title{文档标题}
\author{作者姓名}
\date{\today}
\maketitle

\section{引言}
正文内容...

\end{document}
```

## 常用命令

### 文本格式
- `\textbf{粗体文本}` - 粗体
- `\textit{斜体文本}` - 斜体
- `\underline{下划线文本}` - 下划线
- `\texttt{等宽字体}` - 打字机字体

### 列表
```latex
% 无序列表
\begin{itemize}
  \item 第一项
  \item 第二项
\end{itemize}

% 有序列表
\begin{enumerate}
  \item 第一项
  \item 第二项
\end{enumerate}
```

### 数学公式
```latex
% 行内公式
$E = mc^2$

% 行间公式
\begin{equation}
  \int_{a}^{b} f(x) dx = F(b) - F(a)
\end{equation}

% 多行公式对齐
\begin{align}
  f(x) &= x^2 + 2x + 1 \\
      &= (x + 1)^2
\end{align}
```

### 表格
```latex
\begin{table}[h]
\centering
\caption{表格标题}
\begin{tabular}{|c|c|c|}
\hline
列1 & 列2 & 列3 \\
\hline
数据1 & 数据2 & 数据3 \\
\hline
\end{tabular}
\end{table}
```

### 图片
```latex
\begin{figure}[h]
\centering
\includegraphics[width=0.8\textwidth]{figures/image.png}
\caption{图片标题}
\label{fig:image}
\end{figure}

% 引用图片
见图 \ref{fig:image}
```

## 中文支持

使用 `ctex` 宏包支持中文：

```latex
\usepackage[UTF8]{ctex}
```

编译时使用 `xelatex` 而非 `pdflatex`。

## 参考文献建议

1. 使用 BibTeX 管理参考文献
2. 保持条目格式一致性
3. DOI 应为可点击链接
4. 优先引用近 5 年的文献

更多细节请参考具体项目的模板文件。
