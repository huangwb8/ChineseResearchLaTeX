# GXNSF General Template Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 新增可独立构建、可发布、可在 Overleaf 使用的广西自然科学基金面上项目报告正文模板，并严格以 issue #52 提供的精简 DOCX 为版式与正文提纲基线。

**Architecture:** 新建项目层独立模板 `projects/GXNSF_General/`，宏与构建入口统一使用 `GXNSF` 前缀，仅复用 `packages/bensz-fonts/` 的字体资源，不接入或修改 `packages/bensz-nsfc/`。同时让 VS Code 同步、README 自动模板列表和 Release/Overleaf 打包显式识别该项目，并用 TDD 与既有 GDNSF/NSFC 回归证明隔离性。

**Tech Stack:** XeLaTeX、ctex/xeCJK/fontspec、Python 3、pytest、LibreOffice/Pandoc/Poppler、现有 Release 与 VS Code 同步脚本。

**Minimal Change Scope:** 允许新增 `projects/GXNSF_General/`、GXNSF 专属测试与 VS Code 模板，并修改 `scripts/sync_vscode_configs.py`、`scripts/update_readme_template_list.py`、`scripts/pack_release.py`、`scripts/vscode/README.md`、`README.md`、`projects/README.md`、`CHANGELOG.md`；禁止修改 `packages/bensz-nsfc/`、`packages/bensz-fonts/`、`projects/NSFC_*` 与 `projects/GDNSF_General/`。

**Success Criteria:** 提纲文本、顺序、局部字重、A4 页面、3.175 cm 左右边距、2.54 cm 上下边距、16 pt 字号、28.3 pt 固定行距和两字符首行缩进与 DOCX 一致；项目 wrapper、VS Code、标准 zip、Overleaf zip 均可用；相关自动化测试通过；GDNSF 与三套 NSFC 构建无回归；受保护路径 diff 为空。

**Verification Plan:** 在 `tests/issue-52/` 下运行目标 pytest；构建并检查 `GXNSF_General`；生成标准/Overleaf zip 后在隔离副本中构建；用 `pdfinfo`、`pdftotext`、逐页 PNG 和像素差异报告对比 Word→PDF 基线；回归构建 `GDNSF_General`、`NSFC_General`、`NSFC_Local`、`NSFC_Young`；运行 `python scripts/sync_vscode_configs.py --check`。

---

### Task 1: 锁定官方资料与验收口径

**Files:**
- Reference: `tests/issue-52/source/广西面上模板.docx`
- Reference: `tests/issue-52/rendered/广西面上模板.pdf`
- Create: `projects/GXNSF_General/template/广西自然科学基金面上项目-报告正文.docx`
- Create: `projects/GXNSF_General/template/广西自然科学基金面上项目-报告正文.pdf`

**Steps:**
1. 核对 DOCX XML 的页面、字体、行距、缩进与局部粗体参数。
2. 核对官方附件四与精简 DOCX 的差异，确定 PDF 模板严格采用 issue 附件，README 明示它不替代当年度申报须知。
3. 把精简 DOCX 与可信转换 PDF 保存为项目基线。

### Task 2: 先写 GXNSF 集成失败测试（RED）

**Files:**
- Create: `scripts/test_sync_vscode_configs.py`
- Modify: `scripts/test_update_readme_template_list.py`
- Modify: `scripts/test_install_architecture.py`
- Create: `scripts/test_gxnsf_build.py`

**Steps:**
1. 测试 `GXNSF_General -> gxnsf` VS Code profile 与专属 wrapper 配置。
2. 测试 README 独立广西分类、项目链接和标准/Overleaf Release 链接。
3. 测试 Release kind、最小字体集合、标准 zip/Overleaf zip 文件边界与无 `bensz-nsfc` 依赖。
4. 测试 wrapper 的缺文件、首轮失败、两轮成功复制 PDF 与 clean 行为。
5. 在 `tests/issue-52/` 工作目录运行测试并确认新增断言先失败。

### Task 3: 实现独立 GXNSF 项目（GREEN）

**Files:**
- Create: `projects/GXNSF_General/main.tex`
- Create: `projects/GXNSF_General/extraTex/@config.tex`
- Create: `projects/GXNSF_General/extraTex/*.tex`
- Create: `projects/GXNSF_General/scripts/gxnsf_build.py`
- Create: `projects/GXNSF_General/README.md`
- Create: `projects/GXNSF_General/figures/.gitkeep`

**Steps:**
1. 用 `GXNSF*` 专属宏表达标题、楷体一级提纲、仿宋条目标题/说明及内容插槽。
2. 实现系统方正字体优先、`bensz-fonts` 稳定字体回退、Overleaf 本地字体回退三层策略。
3. 实现两轮 XeLaTeX wrapper，中间文件只进入 `.latex-cache/`，根目录只复制最终 PDF。
4. 构建目标项目并让 wrapper 测试转绿。

### Task 4: 接入 VS Code、README 与 Release

**Files:**
- Modify: `scripts/sync_vscode_configs.py`
- Create: `scripts/vscode/gxnsf.settings.json`
- Modify: `scripts/vscode/README.md`
- Modify: `scripts/update_readme_template_list.py`
- Modify: `scripts/pack_release.py`
- Modify: `README.md`
- Modify: `projects/README.md`
- Modify: `CHANGELOG.md`

**Steps:**
1. 新增 `gxnsf` VS Code profile，并用同步脚本生成 workspace/settings/Lua launcher。
2. 新增广西独立 README 分类与静态 TemplateSpec，通过自动脚本刷新根 README 区块。
3. 把 GDNSF/GXNSF 共性收敛为省基金项目层字体运行时逻辑，同时保持既有 GDNSF API/行为兼容。
4. 生成标准包与 Overleaf 包并让集成测试转绿。

### Task 5: 高保真验收与全回归

**Files:**
- Output: `tests/issue-52/final/`
- Log: `.bensz-api/skills/awesome-code/2026-07-16-17-04/log/`

**Steps:**
1. 比较 GXNSF PDF 与 Word→PDF 基线的页面、文本、字体语义、分页与像素差异。
2. 在空 TEXMFHOME 的解包目录中构建 Overleaf 包，证明字体与入口自包含。
3. 回归构建 GDNSF 与三套 NSFC，并运行相关 pytest、VS Code check、包结构校验。
4. 审查 diff，修复所有 Critical/Important 问题并重跑受影响验证。

