---
name: make_latex_model
version: 2.1.1
author: ChineseResearchLaTeX Project
maintainer: project-maintainers
status: stable
category: normal
description: LaTeX 模板高保真优化器，支持任意 LaTeX 模板的样式参数对齐、标题文字对齐和像素级 PDF 对比验证
tags:
  - latex
  - template
  - optimization
  - nsfc
  - pdf-analysis
  - style-alignment
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
last_updated: 2026-01-05
changelog: ../../CHANGELOG.md
---

# NSFC LaTeX 模板高保真优化器

## 0.5) 深度参考
- 本项目的 [CLAUDE.md](../../CLAUDE.md) 和 [skills/README.md](../README.md) 规范
- 现有某个 project 的 `@config.tex` 的样式定义模式
- ⚠️ **关于 `main.tex` 的参考范围**：
  - ✅ **允许参考**：`main.tex` 中的 `\section{}`、`\subsection{}` 标题文本
  - ❌ **禁止参考**：`main.tex` 中的 `\input{}` 引用的正文内容文件

## 0) 核心目标
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

### ⚠️ 关键 1：标题文字对齐（新增）
- **标题的文字内容必须与 Word 完全相同**
- **标题的编号格式必须与 Word 完全相同**（如"1." vs "1．"）
- **标点符号必须与 Word 完全相同**（如全角/半角符号）
- 例如：Word 是"1. 项目的立项依据"，LaTeX 必须完全一致

### ⚠️ 关键 2：每行字数对齐
- **每行的字数必须与 Word 完全相同**
- **换行位置必须与 Word 完全一致**
- 这需要精确调整：字号、字间距、行距、段间距

## 1) 触发条件
用户在以下场景触发本技能：
- NSFC 发布了新的年度 Word 模板（如 2026 年版）
- 当前 LaTeX 模板与 Word 模板存在明显样式差异
- 用户主动要求“对齐 Word 样式”“更新模板格式”

## 2) 输入参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `project` | string | 是 | 项目名称（如 `NSFC_Young`、`NSFC_General`） |
| `word_template_year` | string | 是 | Word 模板年份（如 `2026`） |
| `optimization_level` | string | 否 | 优化级别：`minimal`（最小改动）\|`moderate`（中等）\|`thorough`（彻底），默认 `moderate` |
| `dry_run` | boolean | 否 | 预览模式，不实际修改文件，默认 `false` |

## 3) 执行流程

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

#### 2.1 生成 Word PDF 基准
1. 定位 `projects/{project}/template/{word_template_year}年最新word模板-*.doc*`（可能是 .doc 或 .docx）
2. ⚠️ **必须使用 Word 打印 PDF 进行精确测量**：
   - 在 Microsoft Word 中打开模板（.doc 或 .docx 皆可）
   - 填充示例文本（与 main.tex 相同）
   - **导出/打印为 PDF**（这是关键！）
   - 使用 PDF 测量工具（如 Adobe Acrobat 的"测量工具"）精确测量
   - **替代方案**：如无 Word，可使用 LibreOffice 命令行转换：
     ```bash
     soffice --headless --convert-to pdf --outdir . "template/2026年最新word模板-*.doc*"
     ```
3. ⚠️ **为什么必须用 Word 打印 PDF**（关键！）：
   - **QuickLook 预览渲染引擎与 Word 不同**：QuickLook 生成的缩略图在行距、字体渲染、断行算法上与 Word 有本质差异
   - **像素级对齐需要精确基准**：只有 Word 导出的 PDF 才能准确反映模板的真实样式
   - **避免误导性对比**：使用 QuickLook 基准会导致正确的样式修改反而显示像素对比指标恶化（见 Q2 深度解析）
   - **结论**：如果只能使用 QuickLook 基准，应降低像素对比指标的权重，以样式参数正确性为主要验收标准

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

#### 2.3 手动测量（备用方案）
如果无法使用自动化工具，可手动测量以下要素（精度要求 ±0.5pt）：
- **页面**：边距（上、下、左、右）、版心尺寸
- **正文**：字号（pt）、行距（倍数或 pt 值）、首行缩进（字符或 cm）
- **一级标题**：字号、字体、颜色、加粗、缩进、段前段后间距
- **二级标题**：同上
- **三级标题**：编号格式、字号、缩进、与正文间距
- **四级标题**：编号格式（如（1））、缩进
- **列表**：编号格式、左缩进、悬挂缩进、项间距
- **字间距**：中文字间距、英文词间距（如需微调换行）

### 步骤 2.5：提取标题结构（⚠️ 新增）

**自动化工具**：使用 `compare_headings.py` 自动对比标题文字

1. **安装依赖**（首次使用）：
   ```bash
   pip install python-docx
   ```

2. **自动对比 Word 和 LaTeX 标题**：
   ```bash
   # 生成 HTML 可视化报告
   python3 skills/make_latex_model/scripts/compare_headings.py \
     projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.docx \
     projects/NSFC_Young/main.tex \
     --report heading_report.html
   ```

3. **查看报告**：
   - 打开 `heading_report.html` 查看可视化对比结果
   - 报告会显示：
     - ✅ 完全匹配的标题（绿色）
     - ⚠️ 有差异的标题（黄色，并排显示 Word 和 LaTeX 内容）
     - ❌ 仅在一方的标题（红色）

4. **如果 Word 是 .doc 格式**，先转换为 .docx：
   ```bash
   soffice --headless --convert-to docx --outdir . template.doc
   ```

5. **手动提取标题**（备用方案）：
   - 打开 Word 模板，复制所有标题文本
   - 打开 LaTeX 的 `main.tex`，复制 `\section{}` 和 `\subsection{}` 中的标题
   - 人工对比差异

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
   - 使用注释标记新增内容：`% 2026年模板新增`

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
   - ✅ **第二优先级**：**标题文字与 Word 模板完全一致**（新增）
   - ✅ **第三优先级**：视觉上与 Word PDF 高度相似（考虑到字体渲染差异，允许轻微差异）
   - ⚠️ **第四优先级**：像素对比指标（仅作为辅助验证，非硬性要求）

## 4) 输出规范

### 4.1 修改摘要
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
## [v1.0.1] - 2026-01-XX

### Changed（样式优化）
- **一级标题字号**：14pt → 15pt（Word 2026 模板要求）
- **行距**：1.5 → 1.45（通过 PDF 叠加对比确定）
- **页边距**：调整上下边距为 2.54cm（与 Word 完全一致）

### Added（新增样式）
- 新增三级标题编号格式 1.1、1.2（Word 2026 新增要求）

### Fixed（修复）
- 修复 MsBlue 颜色值误差（原 RGB 0,112,190 → 正确的 0,112,192）
```

### 4.2 代码变更
对 `@config.tex` 进行精确修改，保留：
- 原有注释
- 代码风格
- 条件判断结构（如 `\ifwindows`）
- **⚠️ 绝不触碰 `main.tex`**

### 4.3 验证清单（按优先级排序）

**第一优先级：基础编译检查**
- [ ] **编译无错误和警告**
- [ ] 字体加载正常（跨平台）
- [ ] 参考文献样式正确
- [ ] 表格和图片位置正确

**第二优先级：样式参数一致性**
- [ ] **行距与 Word 一致**（如 1.2 倍）
- [ ] **字号与 Word 一致**（如 14pt）
- [ ] **颜色与 Word 一致**（如 MsBlue RGB 0,112,192）
- [ ] **页边距一致**（误差 < 0.5mm）
- [ ] **标题样式一致**（缩进、间距、编号格式）
- [ ] **⚠️ 标题文字与 Word 一致**（新增）
  - [ ] 一级标题文字完全相同
  - [ ] 二级标题文字完全相同
  - [ ] 标题编号格式完全相同（如"1." vs "1．"）

**第三优先级：视觉相似度**
- [ ] **PDF 与 Word 模板视觉高度相似**
- [ ] **每行字数与 Word 接近**（允许 ±1 字差异）
- [ ] **换行位置与 Word 大致对齐**

**第四优先级：像素对比（辅助验证）**
- [ ] **像素对比指标**（仅当使用 Word 打印 PDF 基准时）
  - [ ] changed_ratio < 0.20（考虑到换行位置变化）
  - [ ] 重点检查"每行字数"和"换行位置"对齐
- ⚠️ **如使用 QuickLook 基准，跳过像素对比**

## 5) 核心原则（底线）

### 5.0 绝对禁区（修订）
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

### 5.1 轻量级修改优先
- ✅ 调整参数值（字号 pt 值、颜色 RGB 值、间距 em/cm 值）
- ✅ 新增自定义命令
- ❌ 删除或重命名现有命令
- ❌ 改变宏包加载顺序
- ❌ 重构条件判断结构

### 5.2 保真度与稳定性平衡
- **过度开发的风险**：引入 bug、破坏已有功能、增加维护成本
- **开发不足的风险**：样式不一致、不符合基金委要求
- **平衡策略**：
  - 默认使用 `moderate` 级别
  - 仅在必要时使用 `thorough` 级别
  - 保留老样式的核心架构

### 5.3 跨平台兼容性
- 保留 `\ifwindows` 条件判断
- 确保 Mac/Windows/Linux 都能正确编译
- 外挂字体路径保持不变（`./fonts/`）

## 6) 验证清单（完成后自检，按优先级排序）

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
- [ ] **⚠️ 标题文字**：与 Word 模板完全一致（新增）
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

## 7) 常见问题

### Q1: Word 模板是二进制格式，如何准确提取样式？
A: 采用多策略：
1. 基金委提供的模板可能是 .doc 或 .docx，两者都通过 Microsoft Word 打开测量
2. **必须导出/打印 PDF**：QuickLook 预览或其他工具的渲染引擎与 Word 不同，会导致测量误差
3. 对比历史模板的变化趋势
4. 用户手动提供样式信息（截图、测量值）

### Q1.1: 如何获取 Word 打印 PDF（最佳实践）？
A: **⚠️ 必须使用 Word 打印 PDF，绝对不能使用 QuickLook 预览**

**为什么必须用 Word 打印 PDF？**
- QuickLook 预览渲染引擎与 Word 本质不同（行距、字体渲染、断行算法都有差异）
- 使用 QuickLook 基准会导致正确的样式修改反而显示像素对比指标恶化
- **只有 Word 导出的 PDF 才能准确反映模板的真实样式**

**方法 1：Microsoft Word（强烈推荐）**
```bash
# 1. 在 Microsoft Word 中打开模板文件
# 2. 选择"文件" → "导出" → "创建 PDF"
# 3. 保存为 artifacts/baseline/word.pdf
```
- **优点**：最精确，完全符合 Word 渲染效果
- **缺点**：需要 Microsoft Word 许可证

**方法 2：LibreOffice（免费替代）**
```bash
# 安装 LibreOffice（macOS）
brew install --cask libreoffice

# 转换 .doc/.docx 为 PDF
soffice --headless --convert-to pdf \
  --outdir artifacts/baseline \
  "projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文.doc"

# 将 PDF 转换为高分辨率 PNG（用于像素对比）
pdftoppm -png -r 150 -singlefile \
  artifacts/baseline/word.pdf \
  artifacts/baseline/word
```
- **优点**：免费、跨平台、命令行自动化
- **缺点**：渲染效果与 Word 可能有细微差异（但远好于 QuickLook）

**方法 3：在线转换（临时方案）**
- 使用 CloudConvert、Zamzar 等在线服务
- **注意**：不适合处理敏感内容

**验证 PDF 质量**：
```bash
# 检查 PDF 信息
pdfinfo artifacts/baseline/word.pdf

# 检查页面尺寸（应与 A4 纸一致：595 x 842 pt）
```

**⚠️ 绝对禁止的做法**：
- ❌ 使用 `qlmanage -t` 生成 QuickLook 缩略图作为基准
- ❌ 使用 macOS 预览应用打开 .doc 文件截图
- ❌ 使用任何非 Word/LibreOffice 的渲染工具

### Q2: 为什么像素对比指标变差了，但样式却是正确的？
A: 这是正常现象，主要原因：
1. **基准问题**：如果使用 QuickLook 缩略图作为基准，像素对比会失真（QuickLook 渲染与 Word 不同）
2. **换行位置**：样式修改（如行距）会导致换行位置变化，像素差异会增加
3. **验收标准**：应以"样式参数是否与 Word 一致"和"视觉是否相似"为准，像素对比仅作为辅助参考

**深度解析：像素对比指标的陷阱**

- **问题场景**：修改行距从 1.8 倍 → 1.2 倍（更接近 Word 模板）
- **预期结果**：像素对比指标应该改善（changed_ratio 降低）
- **实际结果**：像素对比指标恶化（changed_ratio 从 0.1652 → 0.1829）
- **原因分析**：
  1. 行距减小后，每页容纳更多文本
  2. 换行位置完全改变，导致大规模像素差异
  3. 如果基准是 QuickLook 预览（而非 Word 打印 PDF），差异会更加放大
- **正确判断**：
  - ✅ 样式参数正确（行距 1.2 倍与 Word 一致）
  - ✅ 视觉上更接近 Word 模板
  - ⚠️ 像素对比指标恶化是**副作用**，不代表修改错误
- **行动建议**：
  - 优先使用 Word 打印 PDF 作为基准
  - 如果只能用 QuickLook，应降低像素对比指标的权重
  - 以样式参数正确性和视觉相似度为主要验收标准

### Q3: 修改后老用户的模板还能用吗？
A: 能。本技能仅修改样式定义（`@config.tex`），不改变内容文件的接口。

### Q4: 如何判断优化是否"过度"？
A: 参考以下标准：
- ✅ 参数调优（如 14pt → 15pt）：合理
- ✅ 新增命令：合理
- ⚠️ 删除命令：需谨慎，确保无引用
- ❌ 重构核心架构：过度

### Q5: Word 模板章节结构变化了怎么办？
A:
1. **样式配置层面**：在 `@config.tex` 中添加必要的样式定义
2. **内容层面**：提示用户自己在 `main.tex` 或 `extraTex/*.tex` 中添加新章节
3. **⚠️ 本技能不负责内容结构的调整**，那是用户的责任

## 8) 变更日志

**技能版本历史**记录在根级 [CHANGELOG.md](../../CHANGELOG.md) 中。

查看最新变更：
```bash
# 查看完整变更历史
cat ../../CHANGELOG.md

# 查看 make_latex_model 的变更
grep -A 10 "make_latex_model" ../../CHANGELOG.md
```

**当前版本**：v2.1.0

**项目变更日志**：
- 每次样式优化后，变更记录将追加到 `projects/{project}/extraTex/@CHANGELOG.md`
- 包括：样式参数调整、新增样式定义、Word 模板变化对应的内容、验证结果
- 这是项目级别的变更记录，与技能版本历史分离
