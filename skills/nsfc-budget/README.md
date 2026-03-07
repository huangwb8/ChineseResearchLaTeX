# nsfc-budget — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-budget` skill。

执行规范与硬约束以 `skills/nsfc-budget/SKILL.md` 为准；默认参数见 `skills/nsfc-budget/config.yaml`。

## 这是什么

`nsfc-budget` 用于根据你的 NSFC 标书正文或补充材料，生成一份预算说明书 LaTeX 项目，并渲染出 `budget.pdf`。

它特别适合这些场景：

- 你已经写完或基本写完正文，现在要补预算说明书
- 你有零散材料，希望先沉淀成规范的预算说明书项目
- 你希望所有中间文件都隐藏在工作目录下的 `.nsfc-budget/`，不污染根目录

## 先注意

- **必须提供工作目录**。如果你没给，skill 会先停下来问你。
- **2026 青年 A/B/C** 通常是**包干制**，往往**不需要预算说明书**；如果你是这类场景，请先确认单位是否仍要求你写预算说明。
- 所有中间文件默认进入 `<workdir>/.nsfc-budget/`。
- 最终交付默认输出到 `<workdir>/<output_dirname>/`，当前默认值以 `skills/nsfc-budget/config.yaml` 为准。
- `template_id`、`output_dirname` 与模板元数据中的输出路径都只接受**相对安全路径**，不能写绝对路径、`.` 或 `..`。
- 输出目录不能写成工作目录根路径，也不能与 `.nsfc-budget/` 重叠。

## 你需要准备什么

最少准备：

- 工作目录
- 标书正文或其它材料
- 项目类型：面上 / 地区 / 青年

建议再补充：

- 预算口径：这是“申请总额”还是“需要解释的直接费用”
- 总预算
- 目标字数（若不提供，默认推荐区间见 `skills/nsfc-budget/config.yaml`）
- 合作单位、其他来源资金、关键价格依据

可直接按 `skills/nsfc-budget/references/info_form.md` 填。

另外建议同时明确：

- 预算模式：合法值见 `skills/nsfc-budget/config.yaml`
- 预算口径：合法值见 `skills/nsfc-budget/config.yaml`

## 快速开始

### 最短 Prompt

```text
请使用 nsfc-budget skill，工作目录是 ./projects/my-proposal。
材料包括：正文 main.tex 和我补充的实验计划。
项目类型：面上。
总预算：50w。
```

### 更稳妥的 Prompt

```text
请使用 nsfc-budget 为我生成预算说明书。
工作目录：./projects/NSFC_General
项目类型：general
预算模式：budget_based
总预算口径：申请总额
总预算：50w
正文目标字数：900 左右
材料：
- ./projects/NSFC_General/main.tex
- ./notes/budget_notes.md
要求：
- 中间文件全部放到 ./.nsfc-budget
- 最终输出 LaTeX 项目 + budget.pdf
- 不要捏造需求，不确定的地方先问我
```

## 默认行为

如果你没有给全参数，skill 会按 `skills/nsfc-budget/config.yaml` 中的默认值启动；重点包括：

- 模板 ID
- 面上 / 地区 / 青年默认预算额
- 推荐总字数区间与默认中心值
- 每部分上限
- 输出目录名与隐藏中间目录名

## 工作流会做什么

### 1) 初始化隐藏工作区

脚本：`skills/nsfc-budget/scripts/init_budget_run.py`

会创建：

- `<workdir>/.nsfc-budget/run_xxx/`
- `<workdir>/.nsfc-budget/run_xxx/budget_spec.json`
- `<workdir>/.nsfc-budget/run_xxx/materials/`

### 2) 形成结构化预算稿

skill 会把预算说明书拆成 5 段：

- 设备费
- 业务费
- 劳务费
- 合作研究转拨资金
- 其他来源资金

每段都要求讲清：

- 这笔钱为什么需要
- 对应哪个研究任务
- 怎么测算出来
- 为什么这个数合理

### 3) 渲染并校验

脚本：`skills/nsfc-budget/scripts/render_budget_project.py`

会输出：

- `<workdir>/<output_dirname>/`：最终 LaTeX 项目
- `<workdir>/<output_dirname>/budget.pdf`
- `<workdir>/.nsfc-budget/run_xxx/validation_report.md`
- `<workdir>/.nsfc-budget/run_xxx/validation_report.json`

并额外强制检查：

- `budget_spec.json` 仍位于 `<workdir>/.nsfc-budget/`
- `budget.*_wan` 与 `sections.*.amount_wan` 一致
- 输出目录和模板路径不存在越界写入风险
- 输出目录不会落到工作目录根路径，也不会与隐藏工作区重叠
- 常见特殊字符（如 `%`、`#`、`&`、`_`）会在写入 LaTeX 前自动转义

## 目录结构

典型输出如下：

```text
<workdir>/
├── .nsfc-budget/
│   └── run_20260307120000/
│       ├── budget_spec.json
│       ├── materials/
│       ├── build/
│       ├── logs/
│       ├── validation_report.md
│       └── validation_report.json
└── <output_dirname>/
    ├── budget.tex
    ├── budget.pdf
    ├── extraTex/
    ├── fonts/
    └── template/
```

## 命令行示例

初始化：

```bash
python3 skills/nsfc-budget/scripts/init_budget_run.py \
  --workdir ./projects/NSFC_General \
  --project-type general \
  --material ./projects/NSFC_General/main.tex
```

渲染：

```bash
python3 skills/nsfc-budget/scripts/render_budget_project.py \
  --spec ./projects/NSFC_General/.nsfc-budget/run_20260307120000/budget_spec.json
```

## 常见问题

### 为什么一定要工作目录？

因为这个 skill 会把所有中间过程隔离在 `<workdir>/.nsfc-budget/` 下；没有工作目录，就无法保证不污染你的其它目录。

### 为什么还要我确认“预算口径”？

因为“申请总额”和“需要解释的直接费用”不是一回事。预算说明书主要解释直接费用，若口径不清，很容易导致金额能对上、逻辑却对不上。

### 为什么要同时填 `budget.*_wan` 和 `sections.*.amount_wan`？

前者便于结构化校验，后者直接驱动正文段落；现在脚本会强制两者一致，避免“数字改了一处、另一处忘了改”。

### 如果没有合作研究或其他来源资金怎么办？

直接写“无”，不要硬凑。这个 skill 默认会为零金额场景写出规范的“无”型表述。

### 能不能只生成 LaTeX，不编译 PDF？

可以，脚本支持 `--skip-compile`。但正式交付前建议至少编译一次，确保 `budget.pdf` 可用。

### 如果输出目录已存在怎么办？

- 若目录非空，渲染时加 `--force` 才会覆盖。
- 若目录为空，脚本现在会直接复用，不再因为“目录已存在”而失败。

### 正文里有 `%`、`#`、`&`、`_` 这类符号怎么办？

可以直接写。脚本会在渲染阶段自动转义这些常见 LaTeX 特殊字符；若你主动写了允许的 `\linebreak{}` 或 `\BudgetBold{}`，也会保留。

## 相关文件

- `skills/nsfc-budget/SKILL.md`
- `skills/nsfc-budget/config.yaml`
- `skills/nsfc-budget/references/info_form.md`
- `skills/nsfc-budget/references/budget-writing-rules.md`
- `skills/nsfc-budget/scripts/README.md`
