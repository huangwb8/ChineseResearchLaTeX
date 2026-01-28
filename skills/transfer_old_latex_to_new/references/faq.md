# FAQ（常见问题）

## 1) 我到底该传哪个目录给 `--old/--new`？

传 **LaTeX 项目根目录**（必须包含 `main.tex`）。如果你传的是 `extraTex/` 或某个子目录，会被判定为“缺少 main.tex”。

## 2) 迁移会不会把新模板改坏？

默认不会。本技能有写入白名单：

- ✅ 仅允许写：`extraTex/*.tex`（排除 `extraTex/@config.tex`）、`references/*.bib`、以及 runs 目录
- ❌ 禁止写：`main.tex`、`extraTex/@config.tex`、`.cls`、`.sty`

触碰到禁止文件会直接报错并中止。

## 3) 为什么有些章节没有自动迁移？

通常是“低置信度/需人工”的映射任务。你可以：

- 查看 `runs/<run_id>/deliverables/unmapped_old_content.md`
- 或谨慎使用 `apply --allow-low` 执行低置信度任务

## 4) 我怎么确保 runs 产物不污染仓库？

两种方式：

- 运行时指定：`--runs-root /path/to/runs`（推荐，测试/批处理必用）
- 或在配置里修改 `workspace.runs_dir`（不如 `--runs-root` 直观）

## 5) 编译失败怎么办？

先看：`runs/<run_id>/logs/latex_aux/main.log`。

如果提示 `command not found: xelatex/bibtex`，说明系统缺少 TeX 环境，需要先安装 TeX Live / MacTeX。

## 6) 我想先检查配置有没有问题再跑迁移

运行配置校验：

```bash
python skills/transfer_old_latex_to_new/scripts/validate_config.py
```

它会检查常见的类型/范围/组合错误，并对“非推荐 4 步法编译序列”给出警告。

