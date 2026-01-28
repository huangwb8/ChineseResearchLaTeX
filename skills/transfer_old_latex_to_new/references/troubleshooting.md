# Troubleshooting（故障排除）

## 1) 提示“缺少 main.tex”

现象：`旧项目缺少 main.tex` / `新项目缺少 main.tex`

处理：
- 确认 `--old/--new` 传入的是**项目根目录**（包含 `main.tex` 的那层）
- 若你的入口不是 `main.tex`，请先按模板约定调整项目结构

## 2) 提示“禁止写入系统文件 / 不在白名单”

现象：`禁止写入系统文件: .../main.tex` 或 `写入路径不在白名单中`

解释：
- 本技能只允许写入：`extraTex/*.tex(排除@config.tex)`、`references/*.bib`、以及 runs 目录

处理：
- 检查你的迁移计划是否指向了模板文件（应当修正映射/计划）

## 3) compile 失败 / command not found

现象：
- `command not found: xelatex` / `bibtex`
- `compile_summary.success=false`

处理：
- 先安装 TeX Live / MacTeX，并确认 `xelatex --version` / `bibtex --version` 可用
- 查看日志：`runs/<run_id>/logs/latex_aux/main.log`

## 4) 迁移后内容为空/不完整

处理：
- 查看结构差异：`runs/<run_id>/analysis/structure_diff.json`
- 查看未映射内容清单：`runs/<run_id>/deliverables/unmapped_old_content.md`
- 如存在大量 `low_confidence`，可考虑：
  - 手动调整映射后再 apply
  - 或使用 `--allow-low`（谨慎）

