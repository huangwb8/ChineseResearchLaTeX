---
name: make_latex_model
version: 2.7.0
author: ChineseResearchLaTeX Project
maintainer: project-maintainers
status: stable
category: normal
description: LaTeX 模板高保真优化器，支持任意 LaTeX 模板的样式参数对齐、标题文字对齐、标题格式对比（加粗）、HTML 可视化报告、LaTeX 自动修复建议和像素级 PDF 对比验证
tags:
  - latex
  - template
  - optimization
  - nsfc
  - pdf-analysis
  - style-alignment
  - iterative-optimization
dependencies:
  python: ">=3.8"
  packages:
    - name: PyMuPDF
      version: ">=1.23.0"
      purpose: PDF 样式参数提取
    - name: python-docx
      version: ">=0.8.11"
      purpose: Word 标题提取
    - name: Pillow
      version: ">=9.0.0"
      purpose: 图像处理和像素对比
    - name: PyYAML
      version: ">=6.0"
      purpose: 配置文件解析
requires:
  - xelatex
  - pdflatex
  - bibtex
compatibility:
  platforms:
    - macos
    - windows
    - linux
  latex_templates:
    - NSFC_Young
    - NSFC_General
    - NSFC_Local
    - generic
last_updated: 2026-01-06
changelog: ../../CHANGELOG.md
---

# NSFC LaTeX 模板高保真优化器

## 📋 文档目录

- **[深度参考](#深度参考)** - 文档参考范围
- **[核心目标](#核心目标)** - 样式要素与关键点
- **[执行模式说明](#执行模式说明)** - 硬编码工具 + AI 规划
- **[工作空间说明](#工作空间说明)** - 专用工作空间管理
- **[触发条件](#触发条件)** - 何时使用本技能
- **[输入参数](#输入参数)** - 必需与可选参数
- **[执行流程](#执行流程)** - 完整的 6 步工作流程
- **[迭代优化闭环](#迭代优化闭环)** - 自动化迭代优化
- **[输出规范](#输出规范)** - 修改摘要与代码变更
- **[核心原则](#核心原则底线)** - 绝对禁区与修改原则
- **[验证清单](#验证清单完成后自检按优先级排序)** - 验收标准
- **[常见问题](#常见问题)** - FAQ 解答

---

## 深度参考
- 本项目的 [CLAUDE.md](../../CLAUDE.md) 和 [skills/README.md](../README.md) 规范
- 现有某个 project 的 `@config.tex` 的样式定义模式
- ⚠️ **关于 `main.tex` 的参考范围**：
  - ✅ **允许参考**：`main.tex` 中的 `\section{}`、`\subsection{}` 标题文本
  - ❌ **禁止参考**：`main.tex` 中的 `\input{}` 引用的正文内容文件

## 核心目标
确保 LaTeX 渲染的 PDF 与 Word 版打印的 PDF **像素级对齐**：

### 样式要素（必须完全一致）
- 标题层级格式（一级、二级、三级、四级）
- **⚠️ 标题文字内容**（每年度的 Word 模板标题可能不同）
- 字体（中文楷体 + 英文 Times New Roman）
- 字号（三号、四号、小四等）
- 颜色（MsBlue RGB 0,112,192）
- 间距（行距、段前段后、缩进）
- 列表样式（编号格式、缩进）
- 页面设置（边距、版心）

### ⚠️ 关键 1：标题文字对齐
- **标题的文字内容必须与 Word 完全相同**
- **标题的编号格式必须与 Word 完全相同**（如"1." vs "1．"）
- **标点符号必须与 Word 完全相同**（如全角/半角符号）
- 例如：Word 是"1. 项目的立项依据"，LaTeX 必须完全一致

### ⚠️ 关键 2：每行字数对齐
- **每行的字数必须与 Word 完全相同**
- **换行位置必须与 Word 完全一致**
- 这需要精确调整：字号、字间距、行距、段间距

## 执行模式说明

本技能采用**"硬编码工具 + AI 规划"**的混合模式：

### 自动模式（硬编码脚本）
以下步骤由 Python 脚本自动执行，无需 AI 干预：

| 步骤 | 脚本工具 | 输入 | 输出 |
|------|---------|------|------|
| 状态检查 | `scripts/check_state.py` | 项目路径 | 状态报告 |
| PDF 样式分析 | `scripts/analyze_pdf.py` | Word PDF | `*_analysis.json` |
| 标题文字对比 | `scripts/compare_headings.py` | Word .docx + LaTeX | 对比报告 |
| 样式参数验证 | `scripts/run_validators.py` | 项目路径 | 验证报告 |
| 编译检查 | `xelatex` 命令 | .tex 文件 | .pdf |

### AI 规划模式（需要智能决策）
以下步骤需要 AI 根据分析结果进行规划和执行：

| 决策点 | 输入数据 | AI 任务 | 输出 |
|--------|---------|---------|------|
| **决策点 1**: 是否需要修改样式？ | PDF 分析结果 + 当前配置 | 判断差异是否超出容忍度 | 修改清单或跳过 |
| **决策点 2**: 生成具体修改方案 | 差异分析结果 | 规划 LaTeX 代码修改 | 具体修改内容 |
| **决策点 3**: 应用修改到配置文件 | 修改方案 | 使用 Edit 工具修改 | 修改后的 @config.tex |
| **决策点 4**: 验证结果是否达标 | 修改前后的验证报告 | 判断是否需要迭代 | 继续微调/完成 |

### 协作流程

```
Word 模板 → [自动] analyze_pdf.py → 分析结果
                                    ↓
                          当前 @config.tex
                                    ↓
                         [AI 决策点 1] 是否需修改？
                                    ↓
                           是 → [AI 决策点 2] 生成方案
                                    ↓
                          [AI 决策点 3] 应用修改
                                    ↓
                          [自动] 编译 + 验证
                                    ↓
                         [AI 决策点 4] 是否达标？
                                    ↓
                     否 → 微调 → 返回 [AI 决策点 2]
                     是 → 完成
```

**关键原则**:
- ✅ **数据提取** 由硬编码工具完成（精确、稳定）
- ✅ **决策判断** 由 AI 完成（灵活、可解释）
- ✅ **代码修改** 由 AI + Edit 工具完成（可控、可回溯）

**注**：AI 决策点的详细规范已整合到"第 3 节 执行流程"的相应步骤中。

## 工作空间说明

本 skill 使用专用工作空间存储所有工作产物，避免污染用户项目目录。

### 工作空间结构

```
skills/make_latex_model/workspace/{project_name}/
├── baseline/          # Word PDF 基准文件
│   ├── word.pdf
│   ├── word_analysis.json
│   └── quality_report.json
├── iterations/        # 迭代历史记录
│   ├── iteration_001/
│   │   ├── main.pdf
│   │   ├── config.tex
│   │   └── metrics.json
│   └── iteration_002/
├── reports/           # 生成的报告
│   ├── diff_report.html
│   └── optimization_report.html
├── backup/            # 备份文件
│   └── main_*.tex.bak
└── cache/             # 缓存文件
    └── pdf_renders/
```

### 路径管理

所有脚本统一使用 `WorkspaceManager` 获取路径：

```python
from core.workspace_manager import WorkspaceManager

ws_manager = WorkspaceManager()
baseline_dir = ws_manager.get_baseline_path("NSFC_Young")
report_path = ws_manager.get_reports_path("NSFC_Young")
```

### 清理策略

- 缓存文件默认保留 24 小时
- 迭代历史默认保留最近 10 轮
- 可通过 `config.yaml` 的 `workspace` 节配置清理策略

## 触发条件
用户在以下场景触发本技能：
- NSFC 发布了新的年度 Word 模板
- 当前 LaTeX 模板与 Word 模板存在明显样式差异
- 用户主动要求"对齐 Word 样式""更新模板格式"

## 输入参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `project` | string | 是 | 项目名称（如 `NSFC_Young`、`NSFC_General`） |
| `word_template_year` | string | 是 | Word 模板年份（如 `2025`） |
| `optimization_level` | string | 否 | 优化级别：`minimal`（最小改动）\|`moderate`（中等）\|`thorough`（彻底），默认 `moderate` |
| `dry_run` | boolean | 否 | 预览模式，不实际修改文件，默认 `false` |

## 执行流程

### 步骤 0：预检查（AI 必须首先执行）

AI 在开始任何优化工作前，**必须先执行状态检查**：

```bash
python3 skills/make_latex_model/scripts/check_state.py projects/{project}
```

根据状态报告决定后续行动：
- 如果 `has_baseline=false`：提示用户先生成 Word PDF
- 如果 `compilation_status=failed`：先修复编译错误
- 如果 `baseline_source=quicklook`：调整像素对比权重

---

#### AI 决策点 1：是否需要修改样式？

**输入数据**:
- `*_analysis.json`: Word PDF 分析结果
- `extraTex/@config.tex`: 当前样式配置
- `config.yaml`: 容忍度配置

**判断逻辑**:
```python
# 伪代码
for 参数 in ["行距", "字号", "颜色", "边距"]:
    word_value = analysis[参数]
    latex_value = extract_from_config(config_tex)
    diff = abs(word_value - latex_value)
    tolerance = config["validation"]["tolerance"][参数]

    if diff > tolerance:
        需要修改 = True
        修改清单.append({
            "参数": 参数,
            "当前值": latex_value,
            "目标值": word_value,
            "差异": diff
        })
```

**输出格式**:
```markdown
| 参数 | 当前值 | 目标值 | 差异 | 容忍度 | 是否需修改 |
|------|--------|--------|------|--------|-----------|
| 行距 | 1.5 | 1.2 | 0.3 | 0.1 | ✅ 是 |
| MsBlue RGB | (0,112,190) | (0,112,192) | 2 | 2 | ⚠️ 边界 |
```

---

### 步骤 1：理解现状（深度阅读）
1. 读取 `projects/{project}/extraTex/@config.tex`，重点分析：
   - 宏包加载
   - 页面设置（geometry）
   - 颜色定义（definecolor）
   - 字体设置（fontspec、xeCJK）
   - 字号系统（newcommand 字号命令）
   - 标题格式（titlesec 定制）
   - 列表样式（enumitem 配置）

### 步骤 2：分析 Word 模板（像素级测量）

#### 2.1 获取 Word PDF 基准

**方案 0：用户已提供 PDF**（最快）

如果用户已经从 Word 模板导出了 PDF 文件，直接使用即可：

```bash
# 复制用户提供的 PDF 到工作空间
cp /path/to/user/provided/word.pdf \
   skills/make_latex_model/workspace/{project}/baseline/word.pdf
```

**要求**：
- PDF 必须是 Word/LibreOffice 导出的，不能用 QuickLook 预览
- PDF 应包含完整的模板样式（标题、正文、列表等）

---

**方案 1：LibreOffice 命令行自动转换**（主推）

如果用户只有 Word 模板文件（.doc/.docx），使用 LibreOffice 自动转换：

```bash
# 自动检测并转换 Word 模板为 PDF
python3 skills/make_latex_model/scripts/generate_baseline.py \
  --project NSFC_Young \
  --template-year 2025
```

脚本会自动完成：
1. 定位 Word 模板文件（支持 .doc 和 .docx）
2. 使用 LibreOffice 无头模式转换为 PDF
3. 保存到工作空间 `workspace/{project}/baseline/word.pdf`
4. 生成高分辨率 PNG 用于像素对比（通过 `pdftoppm`）

**环境要求**：
- LibreOffice（安装命令见下方）
- pdftoppm（poppler-utils）

**LibreOffice 安装**：
```bash
# macOS
brew install --cask libreoffice

# Ubuntu/Debian
sudo apt-get install libreoffice

# Windows
# 从 https://www.libreoffice.org/ 下载安装
```

---

**方案 2：Microsoft Word COM 自动化**（Windows 仅）

如果在 Windows 环境且无法安装 LibreOffice，可使用 Microsoft Word COM 自动化（需 Python `pywin32` 库）：

```bash
python3 skills/make_latex_model/scripts/generate_baseline.py \
  --project NSFC_Young \
  --template-year 2025 \
  --use-msword
```

---

**渲染质量说明**：

| 渲染引擎 | 精度 | 自动化程度 | 推荐度 |
|---------|------|-----------|--------|
| **用户已提供 PDF** | 取决于来源 | 零操作 | ⭐⭐⭐⭐⭐ |
| LibreOffice | 高（与 Word 99% 一致） | 完全自动化 | ⭐⭐⭐⭐⭐ |
| Microsoft Word COM | 最高（100% Word 原生） | 自动化（Windows 仅） | ⭐⭐⭐⭐ |
| QuickLook 预览 | 低（断行/行距有差异） | 自动化但不准确 | ⚠️ 不推荐 |

**为什么不用 QuickLook**：
- QuickLook 预览渲染引擎与 Word 本质不同（行距、字体渲染、断行算法都有差异）
- 使用 QuickLook 基准会导致正确的样式修改反而显示像素对比指标恶化
- 如果只能使用 QuickLook 基准，应降低像素对比指标的权重，以样式参数正确性为主要验收标准

#### 2.2 自动提取样式参数（推荐）
使用 `analyze_pdf.py` 工具自动提取 Word PDF 的样式参数：

```bash
# 安装依赖（首次使用）
pip install PyMuPDF

# 分析 Word PDF 基准
python3 skills/make_latex_model/scripts/analyze_pdf.py \
  projects/NSFC_Young/template/word_baseline.pdf
```

**输出内容**：
- 📐 **页面布局**：页面尺寸、边距（左/右/上/下，单位：cm）
- 🔤 **字体统计**：字体名称、使用频率、字号列表、颜色（RGB）
- 📏 **行距分析**：平均行距（pt）
- 💾 **详细分析结果**：自动保存为 `*_analysis.json`，可用于后续对比

**输出示例**：
```
============================================================
页面布局
============================================================
页面尺寸: 21.01 cm x 29.71 cm
边距:
  左:   3.20 cm
  右:   3.14 cm
  上:   2.54 cm
  下:   2.54 cm

============================================================
字体使用统计
============================================================
字体: TimesNewRomPSMT
  使用次数: 245
  字号: [12.0, 14.0, 15.0]
  颜色 (RGB): [[0, 0, 0], [0, 112, 192]]
  是否加粗: False

字体: KaiTi_GB2312
  使用次数: 128
  字号: [12.0, 15.0, 16.0]
  颜色 (RGB): [[0, 0, 0], [0, 112, 192]]
  是否加粗: True

============================================================
行距分析
============================================================
平均行距: 18.00 pt

详细分析结果已保存到: word_baseline_analysis.json
```

**优势**：
- ✅ **自动化**：无需手动测量，减少人为误差
- ✅ **精确**：直接从 PDF 提取参数，精度 ±0.01pt
- ✅ **可追溯**：保存 JSON 分析结果，便于版本对比
- ✅ **快速**：几秒内完成分析

### 步骤 2.5：提取标题结构

**自动化工具**：使用 `compare_headings.py` 自动对比标题文字

1. **安装依赖**（首次使用）：
   ```bash
   pip install python-docx
   ```

2. **自动对比 Word 和 LaTeX 标题**：
   ```bash
   # 生成 HTML 可视化报告
   python3 skills/make_latex_model/scripts/compare_headings.py \
     projects/NSFC_Young/template/最新word模板-青年科学基金项目（C类）-正文.docx \
     projects/NSFC_Young/main.tex \
     --report heading_report.html
   ```

3. **查看报告**：
   - 打开 `heading_report.html` 查看可视化对比结果
   - 报告会显示：
     - ✅ 完全匹配的标题（绿色）
     - ⚠️ 有差异的标题（黄色，并排显示 Word 和 LaTeX 内容）
     - ❌ 仅在一方的标题（红色）

4. **格式对比（加粗）**：
   ```bash
   # 检查标题内的加粗格式是否一致
   python3 skills/make_latex_model/scripts/compare_headings.py \
     projects/NSFC_Young/template/最新word模板-青年科学基金项目（C类）-正文.docx \
     projects/NSFC_Young/main.tex \
     --check-format \
     --report heading_format_report.txt
   ```

   - Word 模板中的标题可能包含混合格式，例如"**立项依据**与研究内容"
   - 使用 `--check-format` 参数可以检测 LaTeX 是否正确实现了加粗样式
   - 报告会显示：
     - ✅ 文本和格式都完全匹配
     - ⚠️ 文本差异（传统的文字内容不匹配）
     - 🔶 格式差异（加粗位置不一致，并标注具体位置）

5. **🎨 HTML 可视化报告**：
   ```bash
   # 生成包含格式对比的 HTML 报告
   python3 skills/make_latex_model/scripts/compare_headings.py \
     projects/NSFC_Young/template/最新word模板-青年科学基金项目（C类）-正文.docx \
     projects/NSFC_Young/main.tex \
     --check-format \
     --report heading_format_report.html
   ```

   - HTML 报告直观显示 Word 和 LaTeX 的格式差异
   - 加粗文本用 `<b>` 标签高亮显示
   - 格式差异用黄色背景和详细位置标注
   - 支持并排对比（Word vs LaTeX）

6. **🔧 LaTeX 修复建议**：
   ```bash
   # 自动生成 LaTeX 修复代码
   python3 skills/make_latex_model/scripts/compare_headings.py \
     projects/NSFC_Young/template/最新word模板-青年科学基金项目（C类）-正文.docx \
     projects/NSFC_Young/main.tex \
     --check-format \
     --fix-file heading_fix_suggestions.tex
   ```

   - 自动生成可直接复制的 LaTeX 修复代码
   - 根据 Word 格式生成正确的 `\textbf{}` 标记
   - 输出文件示例：
     ```latex
     % LaTeX 标题格式修复建议
     % section_1: （一）立项依据与研究内容
     \section{\textbf{（一）立项依据}与研究内容}
     ```

7. **自动转换 .doc 为 .docx**（如需要）：
   ```bash
   # 脚本会自动检测并转换 .doc 格式
   python3 skills/make_latex_model/scripts/compare_headings.py \
     projects/NSFC_Young/template/最新word模板-青年科学基金项目（C类）-正文.doc \
     projects/NSFC_Young/main.tex \
     --auto-convert \
     --report heading_report.html
   ```

8. **手动验证**（可选，用于调试）：
   - **⚠️ 不推荐手动对比**，应使用自动化工具
   - 如需验证，可打开生成的 HTML 报告查看可视化结果
   - 或使用 `--fix-file` 参数自动生成修复代码

### 步骤 3：差异分析与优化策略（像素级）
1. **对比当前 LaTeX 样式与 Word 模板**，识别差异：
   - 字号差异（如 14pt vs 15pt）—— 精度 ±0.1pt
   - 颜色差异（MsBlue RGB 值）
   - 间距差异（行距、段前段后）—— 精度 ±0.5pt
   - 编号格式差异（1.1 vs 1.1.）
   - **⚠️ 换行位置差异** —— 需要调整字间距或字号微调
2. **根据 optimization_level 确定修改策略**：
   - `minimal`：仅修改明显错误的样式（如颜色值错误）
   - `moderate`（默认）：调整与 Word 不一致的样式，保持结构稳定
   - `thorough`：重构样式系统，实现最大保真度

---

#### AI 决策点 2：生成修改方案

**输入**: 修改清单（来自决策点 1）

**AI 任务**:
1. 定位 `@config.tex` 中的相关代码段
2. 生成具体的 LaTeX 代码修改
3. 确保修改符合"轻量级修改原则"（见 5.1 节）

**输出示例**:
```latex
% 修改行距：1.5 → 1.2
- \renewcommand{\baselinestretch}{1.5}
+ \renewcommand{\baselinestretch}{1.2}

% 修改 MsBlue 颜色
- \definecolor{MsBlue}{RGB}{0,112,190}
+ \definecolor{MsBlue}{RGB}{0,112,192}
```

**约束条件**:
- ✅ 优先调整参数值
- ✅ 新增自定义命令（如需要）
- ❌ 不删除或重命名现有命令
- ❌ 不改变宏包加载顺序

---

### 步骤 4：轻量级修改原则（像素级精度）
1. **优先调整参数，不重构结构**：
   - 调整 `\titleformat` 中的字号（精度 0.1pt）、颜色、间距参数
   - 调整 `\geometry` 中的边距值（精度 0.1mm）
   - 调整 `\newcommand` 字号定义中的 pt 值
   - **如需换行对齐**：微调 `\XeTeXinterchartokenstate`、字间距、或字号 ±0.1pt
2. **保留老样式的稳定性**：
   - 不修改宏包加载顺序
   - 不删除已有的自定义命令
   - 不改变条件判断结构（如 `\ifwindows`）
3. **增量添加新样式**（如有必要）：
   - 新增 `\newcommand` 而非修改现有命令
   - 使用注释标记新增内容：`% 新增样式注释`

### 步骤 5：执行修改
1. **修改 `@config.tex`**（样式配置层）：
   - 调整颜色定义
   - 调整字号系统
   - 调整标题格式（titlesec）
   - 调整列表样式
   - 调整页面设置（geometry）
2. **修改 `main.tex` 中的标题文本**（⚠️ 仅限标题，不触碰正文内容）：
   - 更新章节标题以匹配 Word 模板
   - 保持 LaTeX 结构（`\section{}`、`\subsection{}`）不变
   - 仅修改花括号内的标题文字
   - ⚠️ **绝不修改正文段落内容**
3. **保留原有结构**：
   - 不改变 `\input{extraTex/xxx.tex}` 的引用关系
   - 不修改正文内容文件（`extraTex/*.tex`）
   - 唯一例外：用户明确要求修改示例内容

---

#### AI 决策点 3：应用修改

**工具**: 使用 Edit 工具精确修改

**流程**:
1. 使用 Read 工具读取 `@config.tex`
2. 使用 Edit 工具应用每一处修改
3. 保留原有注释和代码风格

**验证**:
```bash
# 检查编译是否成功
cd projects/{project}
xelatex -interaction=nonstopmode main.tex
```

---

### 步骤 6：验证与迭代（像素级验证）
1. 编译检查：
   ```bash
   cd projects/{project}
   xelatex -interaction=nonstopmode main.tex
   ```

2. **自动化验证**（推荐）：
   ```bash
   # 运行完整验证脚本（包括标题文字一致性检查）
   cd skills/make_latex_model
   ./scripts/validate.sh
   ```
   验证脚本会自动检查：
   - ✅ 编译状态
   - ✅ 版本号一致性
   - ✅ 样式参数（行距、颜色、边距等）
   - ✅ **标题文字一致性**（新增，使用 `compare_headings.py` 自动对比）

3. **像素级 PDF 对比验证**：
   - ⚠️ **必须使用 Word 导出的 PDF 作为基准**（QuickLook 预览或其他工具的渲染与 Word 不同）
   - 将 LaTeX 生成的 PDF 与 Word 打印的 PDF **叠加对比**
   - **检查每行的文字是否完全对齐**
   - **检查换行位置是否完全一致**
   - 使用工具：
     - Adobe Acrobat 的"比较文件"功能
     - 或手动叠加（将两个 PDF 导出为 PNG，使用图像编辑软件叠加）
     - 或使用脚本对比（如 `pdftoppm` + Pillow）

4. **微调与迭代**（最多 3 轮）：
   - 如发现换行不一致：微调字号 ±0.1pt 或字间距
   - 如发现位置偏移：微调边距或缩进 ±0.5pt
   - 如发现标题文字不一致：根据 `compare_headings.py` 报告修改 `main.tex` 中的标题
   - 每轮调整后重新编译验证
   - **使用验证脚本**：运行 `./scripts/validate.sh` 自动检查各项指标

5. **验收标准**（优先级从高到低）：
   - ✅ **第一优先级**：编译无错误和警告
   - ✅ **第二优先级**：样式参数与 Word 模板一致（行距、字号、颜色、间距等）
   - ✅ **第二优先级**：**标题文字与 Word 模板完全一致**
   - ✅ **第三优先级**：视觉上与 Word PDF 高度相似（考虑到字体渲染差异，允许轻微差异）
   - ⚠️ **第四优先级**：像素对比指标（仅作为辅助验证，非硬性要求）

---

#### AI 决策点 4：验证结果是否达标？

**输入**:
- 修改前的验证报告（如存在）
- 修改后的验证报告（`run_validators.py` 输出）

**判断逻辑**:
```python
# 伪代码
优先级1_通过 = 编译成功 and 无警告
优先级2_通过 = 样式参数一致 and 标题文字一致

if 优先级1_通过 and 优先级2_通过:
    返回 "完成"
elif 失败项减少:
    返回 "方向正确，继续微调"
elif 失败项增加:
    返回 "回滚修改，重新分析"
else:
    返回 "保持现状，人工判断"
```

**迭代策略**:
- 最多执行 3 轮迭代
- 每轮只调整 1-2 个参数
- 记录每轮的修改和结果

---

## 迭代优化闭环

本步骤实现全自动的"优化-对比-调整"循环，推荐在需要精细调整时使用。

### 一键启动

```bash
# 全自动迭代优化
python3 skills/make_latex_model/scripts/enhanced_optimize.py \
  --project NSFC_Young \
  --max-iterations 10 \
  --report
```

脚本会自动完成：
1. 预处理 main.tex（注释 `\input{}` 行）
2. 生成可靠 Word PDF 基准
3. 分析 PDF 样式参数
4. 迭代优化循环（最多 10 轮）
5. 恢复 main.tex
6. 生成详细报告

预计耗时：5-15 分钟（取决于迭代轮数）

### 迭代循环逻辑

```
WHILE 未达到收敛条件:
  1. 编译 LaTeX 项目（xelatex -> bibtex -> xelatex -> xelatex）
  2. 执行像素级 PDF 对比（compare_pdf_pixels.py）
  3. 检测是否收敛（convergence_detector.py）
  4. IF 未收敛:
       - 分析差异特征（intelligent_adjust.py）
       - 生成参数调整方案
       - 应用调整到 @config.tex（需 AI 介入）
  5. 记录本轮指标
  6. 保存或回滚配置
END WHILE
```

### 收敛条件（优先级从高到低）

| 条件 | 阈值 | 说明 |
|------|------|------|
| **编译失败** | - | 立即停止，需人工修复 |
| **像素差异收敛** | `changed_ratio < 0.03` | 达到像素级对齐 |
| **连续无改善** | 3 轮 | 指标不再优化，收敛 |
| **最大迭代** | 10 轮 | 强制停止 |

### 智能参数调整策略

脚本 `intelligent_adjust.py` 根据差异特征自动推断参数调整：

| 差异特征 | 推断参数 | 调整策略 |
|---------|---------|---------|
| 换行位置大面积差异 | 字间距/字号 | ±0.1pt |
| 文本垂直偏移 | 行距 | ±0.05 倍 |
| 颜色不一致 | RGB 值 | ±1 |
| 左右边距差异 | geometry | ±0.05cm |
| 标题位置偏移 | titleformat | 调整 spacing |

### 相关脚本

| 脚本 | 功能 |
|------|------|
| `enhanced_optimize.py` | 一键迭代优化入口 |
| `prepare_main.py` | 预处理/恢复 main.tex |
| `generate_baseline.py` | 生成 Word PDF 基准 |
| `convergence_detector.py` | 收敛检测与报告 |
| `intelligent_adjust.py` | 智能参数调整建议 |

---

## 输出规范

### 修改摘要
将变更记录有机地追加到 `projects/{project}/extraTex/@CHANGELOG.md`：

**记录原则**：
- 自然流畅，避免生硬套用模板
- 重点说明“为什么改”（Word 模板的变化）和“改了什么”（具体参数）
- 保留历史追溯性，方便后续版本对比

**记录内容**：
- 修改的文件（仅 `@config.tex`）
- 修改前后的参数对比（如字号从 14pt → 15pt）
- 优化理由（基于 Word 模板的哪个特征变化）
- 验证结果（是否达到像素级对齐）

**格式参考**：
```markdown
## [v1.0.1] - YYYY-MM-DD

### Changed（样式优化）
- **一级标题字号**：14pt → 15pt（Word 最新模板要求）
- **行距**：1.5 → 1.45（通过 PDF 叠加对比确定）
- **页边距**：调整上下边距为 2.54cm（与 Word 完全一致）

### Added（新增样式）
- 新增三级标题编号格式 1.1、1.2（Word 最新模板新增要求）

### Fixed（修复）
- 修复 MsBlue 颜色值误差（原 RGB 0,112,190 → 正确的 0,112,192）
```

### 代码变更
对 `@config.tex` 进行精确修改，保留：
- 原有注释
- 代码风格
- 条件判断结构（如 `\ifwindows`）
- **⚠️ 绝不触碰 `main.tex`**

### 验证清单

> **📋 完整验证清单**：参见第 6 节"验证清单（按优先级排序）"

**快速验证**（推荐）：
```bash
cd skills/make_latex_model
./scripts/validate.sh
```

这将自动检查：
- ✅ 编译状态
- ✅ 版本号一致性
- ✅ 样式参数（行距、颜色、边距等）
- ✅ 标题文字一致性（使用 `compare_headings.py`）

## 核心原则（底线）

### 绝对禁区
⚠️ **永不触碰 `main.tex` 中的正文段落内容**
- `main.tex` 中的 `\input{extraTex/*.tex}` 引用的正文内容文件
- `extraTex/*.tex` 文件中的用户撰写内容
- 正文段落、表格、图片、公式等内容

✅ **允许修改 `main.tex` 中的标题文本**
- `\section{标题文字}` 中的标题文字
- `\subsection{标题文字}` 中的标题文字
- 标题的编号格式、标点符号等
- **理由**：标题的文本结构也是模板样式的一部分，需要与 Word 模板对齐

⚠️ **边界示例**：
```latex
% ✅ 允许修改：标题文字
\section{{\bfseries（一）立项依据与研究内容}(建议8000字以内)：} % 修改为
\section{{\bfseries（一）研究依据与内容}(建议8000字以内)：}

% ❌ 禁止修改：正文内容
\input{extraTex/1.1.立项依据.tex}  % 不改变引用关系
% extraTex/1.1.立项依据.tex 中的具体内容不修改
```

### 轻量级修改优先
- ✅ 调整参数值（字号 pt 值、颜色 RGB 值、间距 em/cm 值）
- ✅ 新增自定义命令
- ❌ 删除或重命名现有命令
- ❌ 改变宏包加载顺序
- ❌ 重构条件判断结构

### 保真度与稳定性平衡
- **过度开发的风险**：引入 bug、破坏已有功能、增加维护成本
- **开发不足的风险**：样式不一致、不符合基金委要求
- **平衡策略**：
  - 默认使用 `moderate` 级别
  - 仅在必要时使用 `thorough` 级别
  - 保留老样式的核心架构

### 跨平台兼容性
- 保留 `\ifwindows` 条件判断
- 确保 Mac/Windows/Linux 都能正确编译
- 外挂字体路径保持不变（`./fonts/`）

## 验证清单（完成后自检，按优先级排序）

### 快速验证（推荐）
使用自动化验证脚本进行快速检查：
```bash
cd skills/make_latex_model
./scripts/validate.sh
```

这将自动检查：
- ✅ 编译状态
- ✅ 版本号一致性
- ✅ 样式参数（行距、颜色、边距等）
- ✅ 配置文件完整性

### 性能基准测试（可选）
运行性能基准测试,评估编译性能：
```bash
cd skills/make_latex_model
./scripts/benchmark.sh
```

这将输出：
- ⏱️ 平均编译时间
- 📄 PDF 文件大小
- 📊 性能报告 (JSON)

---

### 第一优先级：基础编译检查
- [ ] **编译检查**：`xelatex -> bibtex -> xelatex -> xelatex` 无错误
- [ ] **跨平台**：在至少两个操作系统上验证编译
- [ ] **向后兼容**：老用户的内容文件（`extraTex/*.tex`）无需修改即可使用

### 第二优先级：样式参数一致性
- [ ] **行距**：与 Word 模板一致（误差 < 0.1）
- [ ] **字号**：与 Word 模板一致（误差 < 0.5pt）
- [ ] **颜色**：与 Word 模板一致（RGB 误差 < 2）
- [ ] **边距**：与 Word 模板一致（误差 < 0.5mm）
- [ ] **标题样式**：缩进、间距、编号格式与 Word 一致
- [ ] **标题文字**：与 Word 模板完全一致
  - [ ] 一级标题文字完全匹配
  - [ ] 二级标题文字完全匹配
  - [ ] 标题编号格式、标点符号完全匹配

### 第三优先级：视觉相似度
- [ ] **视觉对比**：PDF 与 Word 模板高度相似（考虑到字体渲染差异）
- [ ] **每行字数**：与 Word 接近（允许 ±1 字差异）
- [ ] **换行位置**：与 Word 大致对齐（考虑到断行算法差异）

### 第四优先级：像素对比（辅助验证）
- [ ] **像素对比**（仅当使用 Word 打印 PDF 基准时）：
  - [ ] 叠加对比 PDF 无明显偏移
  - [ ] changed_ratio < 0.20（考虑到换行位置变化）
  - [ ] 重点检查"每行字数"和"换行位置"对齐
- ⚠️ **如使用 QuickLook 基准，跳过像素对比**

### 文档更新
- [ ] **文档更新**：如有新增命令或配置，在 `@config.tex` 顶部添加注释说明

## 常见问题

### Q1: 如何获取 Word PDF 基准？

A: **本技能支持用户已提供 PDF 或自动生成**

#### 方案 0：用户已提供 PDF（最快）

如果用户已经从 Word 模板导出了 PDF 文件，直接复制到工作空间即可：

```bash
# 复制用户提供的 PDF 到工作空间
cp /path/to/user/provided/word.pdf \
   skills/make_latex_model/workspace/{project}/baseline/word.pdf
```

**要求**：
- PDF 必须是 Word/LibreOffice 导出的，不能用 QuickLook 预览
- PDF 应包含完整的模板样式（标题、正文、列表等）

---

#### 方案 1：LibreOffice 命令行自动转换（主推）

如果用户只有 Word 模板文件（.doc/.docx），使用 LibreOffice 自动转换：

```bash
# 一键生成 Word PDF 基准
python3 skills/make_latex_model/scripts/generate_baseline.py \
  --project NSFC_Young \
  --template-year 2025
```

脚本会自动完成：
1. 定位 Word 模板文件
2. 使用 LibreOffice 无头模式转换为 PDF
3. 保存到工作空间
4. 生成高分辨率 PNG 用于像素对比

**环境准备**：
```bash
# macOS
brew install --cask libreoffice poppler

# Ubuntu/Debian
sudo apt-get install libreoffice poppler-utils
```

---

#### 方案 2：Microsoft Word COM 自动化（Windows 仅）

```bash
python3 skills/make_latex_model/scripts/generate_baseline.py \
  --project NSFC_Young \
  --template-year 2025 \
  --use-msword
```

---

#### 渲染引擎对比

| 渲染引擎 | 精度 | 自动化程度 | 推荐度 |
|---------|------|-----------|--------|
| **用户已提供 PDF** | 取决于来源 | 零操作 | ⭐⭐⭐⭐⭐ |
| LibreOffice | 高（与 Word 99% 一致） | 完全自动化 | ⭐⭐⭐⭐⭐ |
| Microsoft Word COM | 最高（100% Word 原生） | 自动化（Windows 仅） | ⭐⭐⭐⭐ |
| QuickLook 预览 | 低（断行/行距有差异） | 自动化但不准确 | ⚠️ 不推荐 |

#### 为什么不用 QuickLook？

1. **渲染引擎差异**：QuickLook 预览渲染引擎与 Word 本质不同（行距、字体渲染、断行算法都有差异）
2. **像素对比失真**：使用 QuickLook 基准会导致正确的样式修改反而显示像素对比指标恶化
3. **精确基准**：只有 LibreOffice 或 Word 导出的 PDF 才能准确反映模板的真实样式

#### 像素对比指标的陷阱

**问题场景**：修改行距从 1.8 倍 → 1.2 倍（更接近 Word 模板）
- **预期结果**：像素对比指标应该改善（changed_ratio 降低）
- **实际结果**：像素对比指标恶化（changed_ratio 从 0.1652 → 0.1829）

**原因分析**：
1. 行距减小后，每页容纳更多文本
2. 换行位置完全改变，导致大规模像素差异
3. 如果基准是 QuickLook 预览（而非 LibreOffice/Word PDF），差异会更加放大

**正确判断**：
- ✅ 样式参数正确（行距 1.2 倍与 Word 一致）
- ✅ 视觉上更接近 Word 模板
- ⚠️ 像素对比指标恶化是**副作用**，不代表修改错误

**行动建议**：
- 优先使用用户提供的 PDF 或 LibreOffice/Word 生成的 PDF 作为基准
- 如果只能用 QuickLook，应降低像素对比指标的权重
- 以样式参数正确性和视觉相似度为主要验收标准

### Q2: 修改后老用户的模板还能用吗？
A: 能。本技能仅修改样式定义（`@config.tex`），不改变内容文件的接口。

### Q3: 如何判断优化是否"过度"？
A: 参考以下标准：
- ✅ 参数调优（如 14pt → 15pt）：合理
- ✅ 新增命令：合理
- ⚠️ 删除命令：需谨慎，确保无引用
- ❌ 重构核心架构：过度

### Q4: Word 模板章节结构变化了怎么办？
A:
1. **样式配置层面**：在 `@config.tex` 中添加必要的样式定义
2. **内容层面**：提示用户自己在 `main.tex` 或 `extraTex/*.tex` 中添加新章节
3. **⚠️ 本技能不负责内容结构的调整**，那是用户的责任
