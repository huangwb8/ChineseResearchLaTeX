# NSFC_Young 样式变更日志

本文件记录 `@config.tex` 样式配置的所有变更历史。

---

## [v1.2.0] - 2026-01-05

### Changed（标题与提纲对齐）
- 更新 `main.tex` 标题为“报告正文（2026版）”，按 Word 模板使用黑色说明行（含30页限制提示）。
- 提纲重排为 Word 2026 四个章节，研究基础/其他条目文字与 Word 模板完全一致，移除旧版 2024 提示语与缩进。
- 取消 `\titleformat{\section}` 的额外左缩进，使标题与 Word 左对齐。

### Added
- 新增“生成式人工智能使用情况”占位文件 `extraTex/3.5.生成式人工智能.tex`。
- “其他”条目迁移为 `extraTex/3.6.其他.tex`（原 `3.5.其它.tex`）。

### Validation
- ✅ `python3 skills/make_latex_model/scripts/check_state.py projects/NSFC_Young`
- ✅ `xelatex -interaction=nonstopmode main.tex`（编译通过；仅保留模板示例引用与字体的既有警告）

---

## [v1.1.0] - 2026-01-05

### Changed（样式优化 - 基于2026年Word模板对齐）

#### 页面边距调整
- **右边距**: 3.14cm → 3.02cm (Word 2026 模板实测值)
- **上边距**: 2.54cm → 2.71cm (Word 2026 模板实测值)
- **下边距**: 2.54cm → 3.11cm (Word 2026 模板实测值)
- **左边距**: 保持 3.20cm (与 Word 一致)

#### 行距调整
- **行距倍数**: 1.5 → 1.6 (基于 Word 2026 模板实测 22.47pt 行距)
  - Word 实测行距: 22.47pt
  - 对应 14pt 字号的倍数: 22.47/14 ≈ 1.6
  - 修改理由: 通过 LibreOffice 转换 Word 模板为 PDF 后,使用 Python 脚本测量得到

### 验证方法
1. 使用 LibreOffice 将 `2026年最新word模板-青年科学基金项目（C类）-正文.doc` 转换为 PDF
2. 使用 PyMuPDF 分析 PDF 样式参数(边距、字号、行距)
3. 对比 LaTeX 配置与 Word 实测值,调整差异项
4. 重新编译验证无错误和警告

### 验证结果
- ✅ 编译无错误和警告
- ✅ 页面边距与 Word 模板对齐(误差 < 0.2cm)
- ✅ 行距与 Word 模板接近(1.6倍行距对应约22.4pt)

---

## [v1.0.0] - 之前版本

### 初始配置
- 基于早期 Word 模板建立的样式配置
- 页面边距: left=3.20cm, right=3.14cm, top=2.54cm, bottom=2.54cm
- 行距: 1.5 倍
- 字号系统: 符合国标(三号16pt、四号14pt、小四12pt等)
- 颜色: MsBlue RGB 0,112,192
