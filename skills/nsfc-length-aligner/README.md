# nsfc-length-aligner

国自然标书“篇幅对齐”技能：基于内置（可配置）的篇幅预算，检查目标标书各部分篇幅，输出差距与针对性建议，并指导扩写/压缩到达标。

## 你会得到什么

- 一份可复现的篇幅报告（按文件/按章节统计）
- 差距总结（哪些部分偏短/偏长、偏差比例）
- 扩写/压缩的操作建议与校验闭环（改完再检查）

## 快速开始

依赖：

- Python 3
- `pyyaml`（用于读取 `config.yaml`）：`pip install pyyaml`

1) 把你的标书（通常是 `.tex` / `.md`）准备在一个目录里  
2) 运行检查：

```bash
python3 scripts/check_length.py --input /path/to/proposal --config config.yaml
```

默认会在 `/path/to/proposal/_artifacts/nsfc-length-aligner/` 生成报告（可用 `--out-dir` 自定义）。
如你希望避免覆盖旧报告，可加 `--fail-if-exists`。
如果你的 `--input` 目录不可写（例如你把模板仓库设为只读），请务必用 `--out-dir` 指向可写位置（例如 `/tmp/nsfc-length-aligner-report`）。

### 针对 NSFC_Young / NSFC_General 模板（推荐用法）

如果你的标书是基于这两套模板（项目根目录包含 `main.tex`）：

- 直接把 `--input` 指向项目根目录
- 脚本会自动沿着 `main.tex` 的 `\input/\include` 依赖树收集“实际会编译进 PDF 的文件”
  - 被注释掉的 `\input{...}` 不会被统计（避免把可选章节误计入篇幅）

可选：如果你已经用最终模板编译出了 PDF（页数是 2026+ 的硬约束），可以把 PDF 也传入做页数统计：

```bash
python3 scripts/check_length.py --input /path/to/proposal --config config.yaml --pdf /path/to/proposal.pdf
```

3) 根据报告提示扩写/压缩后再次运行检查，直到达标

## 配置篇幅标准

编辑 `config.yaml` 的 `length_standard`，把示例口径改成你当年模板的真实要求（尤其是 `length_standard.pages` 的页数硬约束）。

说明：默认只统计 `.tex`（见 `config.yaml:checker.include_globs`），避免把同目录的 README/笔记等 Markdown 误计入篇幅；如确实需要统计 Markdown，可自行把 `*.md` / `*.markdown` 加回 include globs。
