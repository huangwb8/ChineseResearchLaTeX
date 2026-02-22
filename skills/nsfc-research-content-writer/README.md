# nsfc-research-content-writer

用于 NSFC 标书正文 `（二）研究内容` 的写作/重构，并**同时编排**：

- `2.2 特色与创新`
- `2.3 年度研究计划`

目标是形成“研究内容 → 创新点 → 年度计划”的一致闭环。

## 参数（建议显式提供）

- `project_root`：标书项目根目录（如 `projects/NSFC_Young`）
- `output_mode`（默认 `apply`）
  - `preview`：只输出三段可复制的 LaTeX 草稿，不写文件
  - `apply`：仅写入三份目标文件（不触碰其他文件）

## 推荐用法（Prompt 模板）

```
请使用 nsfc-research-content-writer：
project_root：projects/NSFC_Young
信息表：请按 skills/nsfc-research-content-writer/references/info_form.md 提供
输出：写入 extraTex/2.1.研究内容.tex、extraTex/2.2.特色与创新.tex、extraTex/2.3.年度研究计划.tex
output_mode：apply（默认）/ preview（只预览不写入）
研究类型：基础研究 / 应用研究（用于选择更贴合的组织框架；不确定时按“问题→目标→内容→路线→验证”通用主线组织）
篇幅目标（推荐）：研究内容 12–15 页（含图表），纯文字约 12000–15000 字；以“页数控制”为主，不要以字数为导向
额外要求：子目标编号 S1–S4；每个子目标必须写清 指标+对照+数据来源；2.2/2.3 标注回溯到对应 Sx
禁止改动：不要改 main.tex、extraTex/@config.tex、任何 .cls/.sty
```

## 篇幅与图表（写作提醒）

- 研究内容推荐页数：12–15 页（含图表），约占标书总页数（≤28 页）的 50%
- 研究内容推荐字数：12000–15000 字（纯文字部分）
- 评审标准已从“字数控制”转向“页数控制”，建议先按页数规划结构，再用图表提质
- 技术路线图建议放在研究内容开头：可使用 `nsfc-roadmap` skill 生成
- 参考：`skills/nsfc-research-content-writer/references/page_budget.md`

## 推荐工作流（先预览再写入）

1. `output_mode=preview` 生成三份草稿（用于审阅口径与结构）
   - 可参考 `skills/nsfc-research-content-writer/references/output_skeletons.md` 的最小结构骨架快速起草
2. 人工确认后切换 `output_mode=apply` 写入三份 `extraTex/2.*.tex` 文件

## 验收自检

- 按 `skills/nsfc-research-content-writer/references/dod_checklist.md` 快速自检（重点看 2.2 可回溯、2.3 覆盖 S1–S4）
- 可选脚本自检（只读）：`python3 skills/nsfc-research-content-writer/scripts/check_project_outputs.py --project-root projects/NSFC_Young`
  - 更严格（将“首次/领先”等绝对化措辞视为错误）：`python3 skills/nsfc-research-content-writer/scripts/check_project_outputs.py --project-root projects/NSFC_Young --fail-on-risk-phrases`
  - 一键执行（先校验 skill 再自检输出）：`python3 skills/nsfc-research-content-writer/scripts/run_checks.py --project-root projects/NSFC_Young --fail-on-risk-phrases`

## 开发者：一致性校验与可追溯测试会话

- 校验（必需）：`python3 skills/nsfc-research-content-writer/scripts/validate_skill.py`
- 创建 A/B 轮会话骨架（在本 skill 目录下执行）：
  - A轮：`python3 scripts/create_test_session.py --kind a --id vYYYYMMDDHHMM --create-plan`
  - B轮：`python3 scripts/create_test_session.py --kind b --id vYYYYMMDDHHMM --create-plan`
