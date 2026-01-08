# nsfc-research-content-writer

用于 NSFC 2026 新模板正文 `（二）研究内容` 的写作/重构，并**同时编排**：

- `2.2 特色与创新`
- `2.3 年度研究计划`

目标是形成“研究内容 → 创新点 → 年度计划”的一致闭环。

## 推荐用法（Prompt 模板）

```
请使用 nsfc-research-content-writer：
目标项目：projects/NSFC_Young
信息表：<按 references/info_form.md 提供>
输出：写入 extraTex/2.1.研究内容.tex、extraTex/2.2.特色与创新.tex、extraTex/2.3.年度研究计划.tex
额外要求：每个子目标必须写清 指标+对照+数据来源
```

