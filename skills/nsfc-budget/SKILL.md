---
name: nsfc-budget
description: 当用户明确要求“写/生成 NSFC 预算说明书”“写预算说明”“生成 budget.tex / budget.pdf”“写国自然预算 justification”时使用。基于用户标书正文或补充材料，输出一份可提交的预算说明书 LaTeX 项目并渲染 `budget.pdf`。若用户未指定工作目录，必须暂停并先要求其指定。⚠️ 不适用：用户只是想了解预算原则；用户仅要预算表数字而不写说明书；或用户是 2026 青年 A/B/C 默认包干制且无需预算说明书的场景。
metadata:
  author: Bensz Conan
  short-description: NSFC 预算说明书生成与 LaTeX 交付
  keywords:
    - nsfc
    - 预算说明书
    - budget justification
    - budget.pdf
    - latex
  triggers:
    - 预算说明书
    - 预算说明
    - budget justification
    - budget.tex
    - budget.pdf
config: skills/nsfc-budget/config.yaml
---

# NSFC 预算说明书生成器

目标：基于标书正文与补充材料，写出一份“经得起财务与学术双重审视”的预算说明书，并交付可编辑 LaTeX 项目与 `budget.pdf`。

## 先做适用性判断

- 如果用户**没有指定工作目录**：立即暂停，先让用户给出工作目录。
- 如果用户只是问“预算怎么写/有哪些原则”，直接回答或给建议，不启动本 skill。
- 如果用户是 **2026 青年 A/B/C** 且场景属于**包干制**：先明确提醒“通常无需预算说明书”；只有在用户明确说明是历史模板、特定单位要求或预算制场景时才继续。

## 必要输入

优先让用户按 `skills/nsfc-budget/references/info_form.md` 提供。最少要拿到：

- 工作目录（必需）
- 标书正文或其它材料
- 项目类型：`general | local | youth`
- 预算口径：至少说明“这是申请总额”还是“这是需要解释的直接费用口径”

若用户没给全，按下面规则处理：

- **总预算未给**：按 `config.yaml:defaults.total_budget_wan` 取默认值（面上 50w、地区 50w、青年 30w）。
- **正文目标字数未给**：按 `800–1000` 字推荐区间执行。
- **每节上限**：默认 `500` 字，见 `config.yaml:defaults.per_section_max_chars`。
- **模板未给**：默认 `skills/nsfc-budget/models/01`。

## 中间产物边界

- 所有中间文件只能放在 `<workdir>/.nsfc-budget/`。
- 不要把草稿、日志、计划、截图、临时 JSON、编译中间文件散落到工作目录其它位置。
- 最终可见交付物只放在 `<workdir>/<output_dirname>/`（默认 `budget_output/`）。

## 工作流

### 1. 初始化 run

先创建隐藏工作区与 `budget_spec.json` 骨架：

```bash
python3 skills/nsfc-budget/scripts/init_budget_run.py \
  --workdir <workdir> \
  --project-type <general|local|youth> \
  --template-id 01
```

如用户已给材料路径，可追加多个 `--material <path>`。脚本会把材料快照复制到 `.nsfc-budget/run_xxx/materials/`。

### 2. 吃透材料，形成“任务-需求-金额-依据”链

读取正文与补充材料后，先在隐藏工作区内形成内部判断，再填写 `budget_spec.json`：

- 每一笔钱都必须能追溯到**具体研究任务**。
- 每一节都要说明**为什么要花、花在哪里、怎么测算、为什么这个数合理**。
- 不能捏造设备、合作单位、测试次数、出差频次、劳务人数、价格依据。
- 证据不足时，要么追问用户，要么保守写“暂不列支/暂无合作转拨/暂无其他来源资金”，不要编造。

写作原则见：`skills/nsfc-budget/references/budget-writing-rules.md`。

### 3. 填写 `budget_spec.json`

脚本生成的 `budget_spec.json` 是**唯一结构化中间稿**。至少补齐：

- `meta`：项目题目、项目类型、预算模式、工作目录、输出目录、模板 ID、字数目标
- `budget`：总预算口径、直接费用总额（若已知）、设备/业务/劳务/合作转拨/其他来源金额
- `sections`：五个部分的正文段落（数组）
- `evidence`：关键测算依据、必要假设、待确认点

要求：

- `设备费 + 业务费 + 劳务费 = 直接费用总额`（若你已明确直接费用口径）
- `合作研究转拨资金` 不能与前三项形成逻辑冲突
- `其他来源资金` 必须写明来源与用途；若无，则显式写“无”

### 4. 渲染、校验、迭代

用脚本把 JSON 渲染为 LaTeX 项目，并把校验报告与编译日志留在隐藏目录：

```bash
python3 skills/nsfc-budget/scripts/render_budget_project.py \
  --spec <workdir>/.nsfc-budget/run_xxx/budget_spec.json
```

脚本会：

- 复制模板到 `<workdir>/<output_dirname>/`
- 将五个 section 写入对应 `extraTex/*.tex`
- 校验金额关系、段落长度、可见字符数与模板/路径约束
- 在隐藏目录保存 `validation_report.md/json`
- 编译输出 `budget.pdf`

如校验失败，先修 `budget_spec.json` 再重新运行脚本，直到通过。

### 5. 交付前人工复核

交付前必须至少复核这些点：

- 预算口径是否说清楚：申请总额 vs 直接费用
- 设备/测试/差旅/劳务是否真的与研究任务一一对应
- 是否出现“写得很满但没有证据”的句子
- 是否存在“金额能对上，但逻辑对不上”的隐性漏洞
- 是否存在“应该写无，却被硬凑了一段”的编造痕迹

## 写作策略

默认采用以下结构化策略：

- **总述从严**：先交代预算遵循政策相符性、目标相关性、经济合理性。
- **逐项落地**：每节至少讲清“用途 + 测算 + 必要性 + 依据”。
- **少说空话**：不要写“为保证项目顺利开展”“具有重要意义”这类无信息量句子，除非后面紧跟具体任务与支出。
- **金额服务任务**：说明书不是“财务散文”，每一段都要能回到研究方案。
- **宁缺毋滥**：缺材料时，先保守、先追问、先明确边界；不要补脑。

## 输出

最终输出必须同时包含：

- `<workdir>/<output_dirname>/`：完整 LaTeX 项目
- `<workdir>/<output_dirname>/budget.pdf`

中间过程保留在：

- `<workdir>/.nsfc-budget/run_xxx/`

## 关键文件

- `skills/nsfc-budget/references/info_form.md`
- `skills/nsfc-budget/references/budget-writing-rules.md`
- `skills/nsfc-budget/scripts/init_budget_run.py`
- `skills/nsfc-budget/scripts/render_budget_project.py`
- `skills/nsfc-budget/models/01/.template.yaml`
