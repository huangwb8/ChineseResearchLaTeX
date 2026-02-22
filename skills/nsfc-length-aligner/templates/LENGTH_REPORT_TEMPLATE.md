# 篇幅对齐报告

生成时间：{{generated_at}}

单位：{{unit}}

## 总览

- 统计文件数：{{file_count}}
- 文件发现模式：{{discovery_mode}}
- 主入口（main.tex，若适用）：{{main_tex}}
- 总篇幅（{{unit}}）：{{total_value}}
- 总篇幅（cjk_chars / chars）：{{total_cjk_chars}} / {{total_chars}}
- PDF（可选）：{{pdf_path}}
- PDF 页数（可选）：{{page_count}}
- 页数预算（建议 max / 硬上限 hard_max）：{{page_budget_max}} / {{page_budget_hard_max}}
- 页数偏差：{{page_delta}}
- 页数备注：{{page_notes}}
- 总预算（target）：{{overall_budget}}
- 总预算（min~max）：{{overall_bounds}}
- 总预算偏差：{{overall_delta}}
- 未匹配预算的文件：{{unmatched_files}}
  - 提醒：页数是硬约束（尤其 2026+）；字符预算是可复检的代理指标。本报告使用的 `length_standard` 默认为“示例口径”，请按当年指南/模板校对后再使用；不要通过缩小字体/行距“挤页数”。

## 文件级差距

{{file_table}}

## 章节级（如启用）

{{section_table}}

## 建议（由 AI 生成）

1. 偏短部分：优先补“证据链/可验证指标/风险应对”
2. 偏长部分：优先删“泛背景/重复论证”，用要点化压缩段落
