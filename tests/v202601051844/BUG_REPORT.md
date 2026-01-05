# Bug报告: make_latex_model skill

## 问题概述
- **测试时间**: 2026-01-05
- **测试环境**: macOS, XeTeX 3.141592653-2.6-0.999996 (TeX Live 2024)
- **测试实例**: `tests/v202601051844/NSFC_Young`
- **问题总数**: 6
- **严重程度分布**: P0(1), P1(2), P2(2), P3(1)

## 问题清单

### 问题 #1: 行距系统冲突导致不一致
**严重程度**: High
**优先级**: P0
**状态**: Open

**问题描述**:
- **现象**: LaTeX 配置中存在行距设置冲突
  - 全局 `\baselinestretch` 设置为 `1.5`
  - 字号命令（如 `\sihao`）的 baselineskip 设置为 `1.2x`（即 16.8pt）
  - Word 2026 模板显示行距为 120%（1.2倍）
- **实际行为**: 由于 `\baselinestretch` 的全局乘数效应，实际行距约为 `1.5 × 1.2 = 1.8` 倍，与 Word 的 1.2 倍严重不符
- **期望行为**: 行距应与 Word 模板保持一致，即 1.2 倍（120%）
- **影响范围**: 所有正文文本的行距，直接影响每行字数和换行位置的对齐

**根因分析**:
- 问题根源: `\baselinestretch` 是一个全局乘数，会作用于所有字号命令的 baselineskip
- 相关代码: `@config.tex:91` (`\renewcommand{\baselinestretch}{1.5}`)
- 为什么出现: 历史配置可能基于早期 Word 模板（1.5倍行距），但 2026 年模板已改为 1.2 倍

**修复建议**:
- **推荐方案**: 将 `\baselinestretch` 从 `1.5` 改为 `1.0`（禁用全局乘数），完全依赖字号命令中的 baselineskip 参数
- **替代方案**: 将字号命令的 baselineskip 调整为 `1.0x`，保留 `\baselinestretch{1.2}`
- **预期效果**: 行距统一为 1.2 倍，与 Word 模板一致

**验证方法**:
- 修改 `@config.tex:91` 为 `\renewcommand{\baselinestretch}{1.0}`
- 重新编译 `compare_2026.tex`
- 测量 PDF 中相邻两行的基线距离，应约为字号 × 1.2
- 预期: 14pt 字号的行距应为 16.8pt

---

### 问题 #2: 页边距与 Word 模板不完全匹配
**严重程度**: High
**优先级**: P1
**状态**: Open

**问题描述**:
- **现象**: 当前页边距设置为 `left=3.175cm, right=3.175cm`
- **实际行为**: Word 2026 模板的左右边距显示为约 90pt（1.25in = 3.175cm），但 QuickLook 预览显示的 padding-left/right 约为 90pt
- **期望行为**: 边距应精确匹配 Word 模板的 3.20cm（左）和 3.14cm（右）
- **影响范围**: 所有页面的版心位置和每行字数

**根因分析**:
- 问题根源: 当前配置使用了对称边距（3.175cm），但 Word 2026 模板的左右边距不对称
- 相关代码: `@config.tex:21` (`\geometry{left=3.175cm,right=3.175cm,...}`)
- 为什么出现: 简化配置时未注意到 Word 模板的细微差异

**修复建议**:
- **推荐方案**: 修改为 `\geometry{left=3.20cm,right=3.14cm,top=2.54cm,bottom=2.54cm}`
- **预期效果**: 版心位置与 Word 模板精确对齐

**验证方法**:
- 修改 `@config.tex:21`
- 重新编译并测量 PDF 左右边距
- 预期: 左边距 3.20cm，右边距 3.14cm（误差 < 0.5mm）

---

### 问题 #3: Section 标题缩进可能与 Word 不一致
**严重程度**: Medium
**优先级**: P1
**状态**: Open

**问题描述**:
- **现象**: Section 标题使用 `\hspace{2.5em}` 作为左缩进
- **实际行为**: Word 2026 模板的 section 标题缩进约为 21pt + 14pt（首行缩进）= 35pt ≈ 2.5em（14pt 字号）
- **期望行为**: 缩进应精确匹配 Word 模板的约 1.45em（根据 config.yaml）
- **影响范围**: 一级标题的位置

**根因分析**:
- 问题根源: `\hspace{2.5em}` 可能与 Word 的实际缩进有细微差异
- 相关代码: `@config.tex:160` (`\titleformat{\section}...{\hspace{2.5em}}`)
- 配置参考: `config.yaml:102` 定义 `indent: "1.45em"`

**修复建议**:
- **推荐方案**: 调整为 `\hspace{1.45em}`，与 config.yaml 保持一致
- **替代方案**: 使用 `\titleformat` 的 `indent` 参数而非 `\hspace`
- **预期效果**: Section 标题位置与 Word 对齐

**验证方法**:
- 修改 `@config.tex:160` 为 `{\hspace{1.45em}}`
- 重新编译并测量标题左侧到版心左边的距离
- 预期: 约 1.45em（14pt × 1.45 ≈ 20.3pt）

---

### 问题 #4: 字号系统可能需要微调
**严重程度**: Medium
**优先级**: P2
**状态**: Open

**问题描述**:
- **现象**: 当前字号命令使用标准字号（如 `\sihao` = 14pt）
- **实际行为**: QuickLook 预览显示 Word 模板的字号与标准值可能有细微差异
- **期望行为**: 字号应精确匹配 Word 模板（误差 < 0.1pt）
- **影响范围**: 所有文本的大小和行距

**根因分析**:
- 问题根源: Word 模板的字号定义可能与 LaTeX 标准字号不完全一致
- 相关代码: `@config.tex:46-58`（字号命令定义）
- 为什么出现: 需要精确测量 Word 模板的实际字号

**修复建议**:
- **推荐方案**: 通过 Word 打印 PDF 进行精确测量，必要时微调字号 ±0.1pt
- **预期效果**: 字号与 Word 模板像素级对齐

**验证方法**:
- 在 Word 中打印 PDF，使用 Adobe Acrobat 测量工具测量字号
- 对比 LaTeX PDF 的字号
- 如差异 > 0.1pt，调整字号命令

---

### 问题 #5: 基准 PDF 缺失导致像素对比不精确
**严重程度**: Medium
**优先级**: P2
**状态**: Open

**问题描述**:
- **现象**: 当前使用 QuickLook 缩略图作为基准，而非 Word 打印 PDF
- **实际行为**: QuickLook 渲染与 Word 打印存在差异，导致像素对比不够精确
- **期望行为**: 使用 Word 打印/导出的 PDF 作为基准
- **影响范围**: 所有像素对比指标的准确性

**根因分析**:
- 问题根源: 测试环境缺少 Microsoft Word 或 LibreOffice
- 为什么出现: macOS 的 QuickLook 是可用的近似替代方案

**修复建议**:
- **推荐方案**: 用户在 Word 中将 `2026年最新word模板-青年科学基金项目（C类）-正文.doc` 导出为 PDF，放置到 `artifacts/baseline/word.pdf`
- **替代方案**: 安装 LibreOffice（`soffice`），使用命令行转换 `.doc` → PDF
- **预期效果**: 获得精确的 Word 打印 PDF 基准

**验证方法**:
- 将 Word PDF 转换为 PNG（使用 `pdftoppm` 或 `ImageMagick`）
- 重新运行像素对比脚本
- 预期: diff 指标更准确反映真实差异

---

### 问题 #6: 列表样式细节可能需要调整
**严重程度**: Low
**优先级**: P3
**状态**: Open

**问题描述**:
- **现象**: 当前列表配置基于早期 Word 模板
- **实际行为**: 2026 Word 模板的列表样式可能有细微变化（编号格式、缩进、间距）
- **期望行为**: 列表样式与 Word 模板完全一致
- **影响范围**: 所有编号列表的显示

**根因分析**:
- 问题根源: 未对 2026 Word 模板的列表样式进行详细测量
- 相关代码: `@config.tex:106-115` (`\setlist[enumerate]{...}`)

**修复建议**:
- **推荐方案**: 对 Word 模板的列表样式进行精确测量，必要时调整参数
- **预期效果**: 列表样式与 Word 对齐

**验证方法**:
- 在 `compare_2026.tex` 中添加测试列表
- 对比 Word 和 LaTeX 的列表显示
- 调整参数直到对齐

## 优先级总结

### 立即修复（本轮迭代）
- ✅ **问题 #1** (P0): 行距系统冲突 - 修改 `\baselinestretch` 为 1.0
- ✅ **问题 #2** (P1): 页边距不对称 - 修改为 `left=3.20cm,right=3.14cm`
- ✅ **问题 #3** (P1): Section 缩进 - 调整为 1.45em

### 下轮迭代
- **问题 #4** (P2): 字号微调 - 需要精确测量
- **问题 #5** (P2): 基准 PDF - 需要用户提供
- **问题 #6** (P3): 列表样式 - 可选优化

## 参考数据

### 当前像素对比指标
- **changed_ratio**: 0.1652（约 16.5% 像素差异）
- **上半页 crop changed_ratio**: 0.1442（约 14.4% 像素差异）
- **mean_abs_diff**: 19.62（平均灰度差异）

### 目标指标
- **changed_ratio**: < 0.05（5% 以下，考虑到 QuickLook 基准的局限性）
- **mean_abs_diff**: < 10（平均灰度差异减半）

## 附录

### 测试环境
- **操作系统**: macOS (Darwin 25.2.0)
- **XeLaTeX**: XeTeX 3.141592653-2.6-0.999996 (TeX Live 2024)
- **Python**: 系统 python3
- **依赖**: Pillow（像素对比）

### 测试文件
- **测试驱动**: `tests/v202601051844/NSFC_Young/compare_2026.tex`
- **样式配置**: `tests/v202601051844/NSFC_Young/extraTex/@config.tex`
- **对比脚本**: `tests/v202601051844/scripts/compare_images.py`

### 已有测试产物
- **baseline**: `tests/v202601051844/artifacts/compare2026_baseline/`
- **iter1**: `tests/v202601051844/artifacts/compare2026_iter1/`
- **iter2**: `tests/v202601051844/artifacts/compare2026_iter2/`
