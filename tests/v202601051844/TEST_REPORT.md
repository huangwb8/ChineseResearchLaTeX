# 测试报告：make_latex_model（v202601051844）

## 结论摘要

- 已建立隔离测试副本 `tests/v202601051844/NSFC_Young`，并完成第一轮 `@config.tex` 参数迭代与像素对比产物留存。
- 由于当前环境缺少 Office/LibreOffice，**无法生成“Word 打印 PDF”基准**；本轮使用 macOS QuickLook 缩略图作为近似基准，指标可用于趋势观察，但不足以宣称“像素级对齐达标”。

## 测试环境

- XeLaTeX：`XeTeX 3.141592653-2.6-0.999996 (TeX Live 2024)`（`xelatex --version`）
- Python：系统 `python3`
- 依赖：已安装 `pillow`（用于 PNG 像素差）

## 输入与产物

### Word 基准（近似）

- Word 模板：`tests/v202601051844/artifacts/baseline/word.doc`
- QuickLook 预览：`tests/v202601051844/artifacts/baseline/word_preview.html`
- QuickLook 缩略图：`tests/v202601051844/artifacts/baseline/word.png`

### LaTeX 输出

- 回归编译（不改 `main.tex`）：`tests/v202601051844/artifacts/baseline/latex.pdf`
- 回归缩略图：`tests/v202601051844/artifacts/baseline/latex.png`
- 对齐验证（内容对照 Word 模板的测试驱动）：`tests/v202601051844/NSFC_Young/compare_2026.tex`
  - baseline：`tests/v202601051844/artifacts/compare2026_baseline/latex.pdf`
  - iter1：`tests/v202601051844/artifacts/compare2026_iter1/latex.pdf`
  - iter2：`tests/v202601051844/artifacts/compare2026_iter2/latex.pdf`

### 像素对比

- 对比脚本：`tests/v202601051844/scripts/compare_images.py:1`
- Word vs LaTeX（回归 main）：
  - diff：`tests/v202601051844/artifacts/baseline/diff.png`
  - 指标：`tests/v202601051844/artifacts/baseline/diff.json`
- Word vs LaTeX（compare_2026）：
  - baseline 指标：`tests/v202601051844/artifacts/compare2026_baseline/diff.json`
  - iter1 指标（含 crop 上半页）：`tests/v202601051844/artifacts/compare2026_iter1/diff_crop.json`
  - iter2 指标（含 crop 上半页）：`tests/v202601051844/artifacts/compare2026_iter2/diff.json`

## 执行过程

1. 复制隔离副本：`projects/NSFC_Young` → `tests/v202601051844/NSFC_Young`
2. 生成 Word 基准（QuickLook）：HTML 预览 + PNG 缩略图
3. 编译 LaTeX：
   - `main.tex`：`xelatex -> bibtex -> xelatex -> xelatex`
   - `compare_2026.tex`：`xelatex -> xelatex`
4. 输出缩略图（QuickLook）并做像素差对比（Pillow）
5. 在测试副本中仅修改 `extraTex/@config.tex` 做两次迭代（iter1/iter2），每次重编译 compare_2026 并记录 diff

## 关键指标（第一轮）

### 1) 回归 main.tex vs Word（内容不一致，指标仅供参考）

- `changed_ratio`：约 `0.1691`（见 `tests/v202601051844/artifacts/baseline/diff.json`）

### 2) compare_2026 vs Word（更接近模板提纲，适合作为样式对齐信号）

- baseline：`changed_ratio ≈ 0.1629`
- iter1：`changed_ratio ≈ 0.1637`（上半页 crop `≈ 0.1447`）
- iter2：`changed_ratio ≈ 0.1652`（上半页 crop `≈ 0.1442`）

> 注：QuickLook 缩略图存在渲染差异与缩放误差；更可靠的“像素级对齐”需要 Word 打印/导出 PDF 作为基准。

## 本轮修改点（仅测试副本）

文件：`tests/v202601051844/NSFC_Young/extraTex/@config.tex`

- 页面边距：左右尝试对齐 Word 预览的 `padding-left/right ≈ 90pt`（约 1.25in）
- `\section` 样式：尝试加粗与缩进参数
- 字号与行距：将字号命令的 baselineskip 显式设为 `1.2x`，以贴近 Word 预览的 `line-height:120%`

## 编译告警（已记录，未阻断）

日志中存在若干字体/宏包 warning（例如 `fontspec`/`xeCJK`/`caption`），见：

- `tests/v202601051844/xelatex1.log`
- `tests/v202601051844/compare2026_xelatex1.log`

本轮优先建立对齐链路与可重复产物，下一轮再集中消除 warning（尤其是字体回退与脚本缺失相关项）。

## 阻塞与下一步建议（决定是否进入“像素级达标”迭代）

### 阻塞

- 缺少 Word 打印/导出 PDF：QuickLook 预览并不等价于 Word 打印 PDF，无法作为“形式审查级”基准。
- 缺少 PDF 级对比工具链（`diff-pdf`/`poppler`/ImageMagick）：本轮通过 QuickLook + Pillow 近似替代。

### 建议的下一步输入（优先级从高到低）

1. 由你在 Word 中将 `2026年最新word模板-青年科学基金项目（C类）-正文.doc` **导出/打印为 PDF**，放到 `tests/v202601051844/artifacts/baseline/word.pdf`（或同目录任意命名），我将改用 PDF→PNG（逐页）做严格对比。
2. 若可安装 LibreOffice（`soffice`），可在命令行将 `.doc` 转 PDF，形成可重复基准。
3. 若你接受，仅在测试副本中进一步创建“与 Word 完全一致的填充文本”，以减少内容差异对指标的干扰（正式项目仍保持不动）。

