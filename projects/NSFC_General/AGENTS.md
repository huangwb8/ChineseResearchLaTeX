# NSFC 面上项目申请书 - AI 写作指令

本目录是 **国家自然科学基金面上项目**申请书的 LaTeX 工作区。AI 在此的核心任务是**辅助撰写和优化标书内容**，不做版式开发，不改动 `extraTex/@config.tex`（除非用户明确要求调整版式）。

正文原则上不超过 **30 页**，鼓励简洁表达。

---

## 文件职责映射

所有正文内容集中在 `extraTex/`，与 `main.tex` 中的章节一一对应：

| 文件 | 对应章节 | 内容要点 |
|------|----------|----------|
| `extraTex/1.1.立项依据.tex` | （一）立项依据 | 研究意义 / 国内外现状 / 关键科学问题 / 研究思路 |
| `extraTex/2.1.研究内容.tex` | （二）研究内容 | 研究内容 / 目标 / 拟解决的关键科学问题 |
| `extraTex/2.2.特色与创新.tex` | （二）特色与创新 | 1–2 条高含金量创新点 |
| `extraTex/2.3.年度研究计划.tex` | （二）年度研究计划 | 三年分年度计划 / 预期成果 |
| `extraTex/3.1.研究基础.tex` | （三）研究基础 | 相关工作积累 / 已取得成绩 / 可行性 / 风险应对 |
| `extraTex/3.2.工作条件.tex` | （三）工作条件 | 已具备实验条件 / 尚缺条件 / 解决途径 |
| `extraTex/3.3.承担项目情况.tex` | （三）承担项目 | 正在承担的相关项目（申请人 + 主要参与者） |
| `extraTex/3.4.完成国基项目情况.tex` | （三）完成情况 | 前一期已满科学基金项目完成情况 |
| `extraTex/4.1–4.6.*.tex` | （四）其他说明 | 申请情况声明，按实际情况如实填写 |
| `references/myexample.bib` | 参考文献库 | BibTeX 格式条目，通过 `\cite{key}` 在正文引用 |
| `references/reference.tex` | 参考文献渲染入口 | 控制文献样式和间距，一般无需修改 |

---

## 写作顺序建议

```
明确科学问题
  → 立项依据（1.1）
  → 研究内容（2.1） + 特色与创新（2.2） + 年度计划（2.3）
  → 研究基础（3.1） + 工作条件（3.2）
  → 承担/完成项目（3.3, 3.4）
  → 其他说明（4.x）
  → 全文质量控制
```

---

## 各章节写作要点

### （一）立项依据 → `extraTex/1.1.立项依据.tex`

写作逻辑：**背景/意义** → **国内外现状分析** → **现有不足与关键科学问题** → **研究思路与预期贡献**

- 参考文献随立项依据之后渲染，通过 `\cite{key}` 引用，文献条目维护在 `references/myexample.bib`
- 现状分析应结合科学研究发展趋势，有据可查

### （二）研究内容 → `extraTex/2.1–2.3.*.tex`

- **2.1 研究内容**：明确"做什么、为什么"，研究目标层次清晰，三个子目标对应三个子内容
- **2.2 特色与创新**：聚焦科学意义而非技术手段，1–2 条，言简意赅
- **2.3 年度研究计划**：三年分年度，预期产出（论文/方法/数据库等）具体可查

### （三）研究基础 → `extraTex/3.1–3.4.*.tex`

- **3.1 研究基础**：用证据链（代表性论文/项目/数据）证明申请人有能力完成本课题，含可行性分析和风险应对措施
- **3.2 工作条件**：已具备条件 + 缺少的条件 + 解决方案，简洁务实
- **3.3–3.4**：如实填写，格式参照模板中的 `\NSFCBlankPara` 占位区

### （四）其他说明 → `extraTex/4.1–4.6.*.tex`

据实填写，无相关情况则保留 `\NSFCBlankPara` 或按模板默认处理。

---

## 常用 LaTeX 命令速查

```latex
% 空白占位符（草稿期使用，填写内容后删除）
\NSFCBlankPara

% 正文文件开头推荐加（两端对齐 + 2em 段首缩进）
\justifying
\NSFCBodyText

% 列表项标题（加粗蓝色标题 + 正文内容）
\item \itemtitlefont{标题：}内容...

% 三级标题（自动编号 1.1 风格）
\subsubsection{标题}

% 四级标题（自动编号（1）风格）
\subsubsubsection{标题}

% 圈号行内小标题
\ssssubtitle{1}

% 插入图片
\begin{figure}[!th]
    \begin{center}
        \includegraphics[width=0.8\linewidth]{figures/图片名.jpg}
        \caption{图片说明文字}
        \label{fig:label}
    \end{center}
\end{figure}

% 引用文献
已有研究表明...\cite{bibkey}
```

---

## AI 技能调用指引

以下技能已为 NSFC 写作优化，优先调用：

| 任务 | 推荐技能 | 触发示例 |
|------|----------|----------|
| 写/改立项依据 | `nsfc-justification-writer` | "帮我写立项依据" |
| 写/改研究内容 + 创新 + 年度计划 | `nsfc-research-content-writer` | "帮我写研究内容" |
| 写/改研究基础 + 工作条件 | `nsfc-research-foundation-writer` | "帮我写研究基础" |
| 生成中英文摘要 | `nsfc-abstract` | "帮我生成摘要" |
| 去 AI 机器味润色 | `nsfc-humanization` | "润色这段文字" |
| 全文质量控制 | `nsfc-qc` | "帮我做质量控制" |
| 模拟专家评审 | `nsfc-reviewers` | "帮我模拟专家评审" |
| 新增/核验参考文献 | `nsfc-bib-manager` | "帮我加引用" |
| 引用与文献一致性 | `nsfc-ref-alignment` | "检查引用是否对齐" |
| 篇幅调整（扩/缩） | `nsfc-length-aligner` | "把这节压缩到 X 页" |
| 技术路线图 | `nsfc-roadmap` | "生成技术路线图" |
| 机制/原理图 | `nsfc-schematic` | "生成机制图" |
| 申请代码推荐 | `nsfc-code` | "推荐申请代码" |

---

## 编译说明

**完整仓库模式**（项目在 `ChineseResearchLaTeX/projects/NSFC_General/`）：

```bash
python scripts/nsfc_build.py build --project-dir .
```

**手工兜底**（任意环境均可，需已安装 TeXLive + 中文字体）：

```bash
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

编译输出：中间文件进入 `.latex-cache/`，最终 PDF 保留在项目根目录 `main.pdf`。

---

## 工程原则

- **只改内容文件**：仅修改 `extraTex/*.tex`、`references/myexample.bib`、`figures/`；不改 `@config.tex` 版式（除非用户明确要求）
- **先读后写**：修改前先读取目标文件，了解现有内容和占位符再动笔
- **不造假引用**：添加参考文献必须经 `nsfc-bib-manager` 核实，不虚构 BibTeX 条目
- **篇幅意识**：完成后检查全文是否超过 30 页；超出时优先用 `nsfc-length-aligner` 压缩
- **语言**：始终用简体中文与用户交流，撰写中文标书内容
