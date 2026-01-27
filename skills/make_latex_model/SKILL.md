---
name: make_latex_model
version: 2.9.0
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
      purpose: Word 标题提取（兼容旧流程，可选）
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
last_updated: 2026-01-27
changelog: ../../CHANGELOG.md
---

# NSFC LaTeX 模板高保真优化器

## 你应该先读什么

- 详细工作流（含命令与决策点）：`skills/make_latex_model/docs/WORKFLOW.md`
- Word PDF 基准制作：`skills/make_latex_model/docs/BASELINE_GUIDE.md`
- 脚本用法全集：`skills/make_latex_model/scripts/README.md`
- 常见问题：`skills/make_latex_model/docs/FAQ.md`

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

## 执行模式（简述）

本技能采用“硬编码工具 + AI 决策”的混合模式：
- 脚本负责确定性工作（提取/对比/验证/落盘产物）
- AI 负责启发式决策（调哪个参数、调多少、是否回滚/继续迭代）

工作空间（产物默认落在 `projects/{project}/.make_latex_model/`）与更多脚本细节见：
- `skills/make_latex_model/docs/WORKFLOW.md`
- `skills/make_latex_model/scripts/README.md`

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

## 快速开始（推荐路径）

1) 预检查：

```bash
python3 skills/make_latex_model/scripts/check_state.py projects/{project}
```

2) 验证（脚本会解析 `--project`，支持 `NSFC_Young` 或 `projects/NSFC_Young`）：

```bash
cd skills/make_latex_model
./scripts/validate.sh --project projects/{project}
```

3) 需要精细对齐时，跑迭代闭环：
- `python3 skills/make_latex_model/scripts/enhanced_optimize.py --project projects/{project} --max-iterations 30 --report`

---

## 迭代优化闭环

本步骤实现全自动的"优化-对比-调整"循环，推荐在需要精细调整时使用。

### 一键启动

```bash
# 全自动迭代优化
python3 skills/make_latex_model/scripts/enhanced_optimize.py \
  --project projects/NSFC_Young \
  --max-iterations 30 \
  --report
```

如需启用“Analyzer → Reasoner → Executor → Memory”的 AI 优化闭环（最小可用版），可加：

```bash
python3 skills/make_latex_model/scripts/enhanced_optimize.py \
  --project projects/NSFC_Young \
  --max-iterations 30 \
  --ai --ai-mode heuristic
```

> 说明：当前脚本内部默认使用启发式决策；如需“宿主 AI 全程参与”，使用 `--ai-mode manual_file`（会生成 `projects/<project>/.make_latex_model/iterations/iteration_XXX/ai_request.json`，等待写入 `ai_response.json` 后再继续）。

### 收敛条件（优先级从高到低）

| 条件 | 阈值 | 说明 |
|------|------|------|
| **编译失败** | - | 立即停止，需人工修复 |
| **像素差异收敛** | `changed_ratio < 0.01` | 达到像素级对齐 |
| **连续无改善** | 5 轮 | 指标不再优化，收敛 |
| **最大迭代** | 30 轮 | 强制停止 |

### 相关脚本

| 脚本 | 功能 |
|------|------|
| `enhanced_optimize.py` | 一键迭代优化入口 |
| `prepare_main.py` | 预处理/恢复 main.tex |
| `generate_baseline.py` | 生成 Word PDF 基准 |
| `convergence_detector.py` | 收敛检测与报告 |
| `run_ai_optimizer.py` | AI 优化器（单轮调试入口） |
| `intelligent_adjust.py` | 智能参数调整建议（旧版启发式，作为回退路径保留） |

---

## 输出规范

### 修改记录（Single Source of Truth）
- 所有可追溯的变更历史记录在仓库根 `CHANGELOG.md`
- 在 `@config.tex` 内只保留必要的解释性注释（不要维护版本历史）

### 代码变更
- 对 `projects/{project}/extraTex/@config.tex` 进行精确修改，保留：
  - 原有注释
  - 代码风格
  - 条件判断结构（如 `\ifwindows`）
- 允许改 `projects/{project}/main.tex` 的标题文本（只改花括号内文字，不动 `\input{}`）

**快速验证**（推荐）：
```bash
cd skills/make_latex_model
./scripts/validate.sh --project projects/{project}
```

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

## 验收清单（按优先级）

1) 基础编译：`xelatex -> bibtex -> xelatex -> xelatex` 无错误  
2) 样式参数：行距/字号/颜色/边距在容忍度内（以 `skills/make_latex_model/config.yaml` 为准）  
3) 标题文字：与 Word 模板完全一致（文本/标点/编号/加粗位置）  
4) 像素对比：仅作为辅助；基准必须来自 Word/LibreOffice（不要用 QuickLook）

## FAQ

见：`skills/make_latex_model/docs/FAQ.md`
