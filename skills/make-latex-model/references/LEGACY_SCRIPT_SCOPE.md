# Legacy 脚本边界

`make-latex-model` 现在既有当前四产品线工作流，也保留了一批旧版 NSFC 辅助脚本。为了减少误用，这里明确它们的边界。

## 可作为通用辅助工具的脚本

- `scripts/check_state.py`
  用于识别项目产品线、检查初始化标记、基线与官方构建入口。
- `scripts/analyze_pdf.py`
  用于提取 PDF 基线参数，不限定产品线。
- `scripts/compare_headings.py`
  用于标题文本/格式比对。
- `scripts/compare_pdf_pixels.py`
  用于像素级 PDF 对比。

## 默认视为 NSFC legacy 的脚本

- `scripts/validate.sh`
- `scripts/validate.bat`
- `scripts/optimize.sh`
- `scripts/optimize.bat`
- `scripts/optimize.py`
- `scripts/enhanced_optimize.py`
- `scripts/run_ai_optimizer.py`
- `scripts/intelligent_adjust.py`
- `scripts/sync_config.py`
- `templates/nsfc/*.yaml`

这些入口仍有价值，但只适合下列场景：

1. 目标明确是 `NSFC_*` 项目。
2. 用户确实需要旧版 `@config.tex` 调参式工作流。
3. 当前官方产品线脚本无法覆盖的补充分析任务。

## 不应做的事

- 不要拿 `validate.sh` 替代 `paper_project_tool.py`、`thesis_project_tool.py` 或 `cv_project_tool.py`。
- 不要把 thesis / paper / cv 强行解释成“只要改 `@config.tex` 就行”的问题。
- 不要在 `SKILL.md` 中重复展开这份清单，保持它是可替换的参考层。
