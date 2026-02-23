# nsfc-code

根据 NSFC 标书正文内容，结合 `skills/nsfc-code/references/nsfc_code_recommend.toml`，输出 5 组申请代码推荐（每组包含主代码/次代码）及理由，并保存为 `NSFC-CODE-vYYYYMMDDHHmm.md`。

## 适用场景

- 你有一份 NSFC 标书正文（LaTeX/Markdown/纯文本），需要选择申请代码。
- 你希望推荐结果可追溯到“标书要点”和“代码库的推荐描述”。

## 快速开始

1) 在仓库根目录执行候选粗排（只读）：

```bash
python3 skills/nsfc-code/scripts/nsfc_code_rank.py --input projects/NSFC_Young --top-k 50
```

如果你明确知道申请代码的学部/门类前缀（例如只可能是 `A`），建议加过滤降低跨学科噪声：

```bash
python3 skills/nsfc-code/scripts/nsfc_code_rank.py --input projects/NSFC_Young --top-k 50 --prefix A
```

2) 让 AI 基于粗排结果与正文语义，产出 5 组 `申请代码1/2` 推荐，并写入：

- 默认：`NSFC-CODE-vYYYYMMDDHHmm.md`
- 或按你的文件名/目录约定

可选：先用脚本生成“带时间戳 + 固定结构”的报告骨架，再填充内容（避免手误）：

```bash
python3 skills/nsfc-code/scripts/nsfc_code_new_report.py --output-dir ./
```

## 约束与注意事项

- 只读：不修改任何 `.tex/.bib/.cls/.sty`
- 不编造代码：只输出 overrides TOML 中存在的代码 key
