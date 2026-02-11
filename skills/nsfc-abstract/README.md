# nsfc-abstract — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-abstract`。
执行指令与硬性规范以 `skills/nsfc-abstract/SKILL.md` 为准；默认参数见 `skills/nsfc-abstract/config.yaml`。

## 你会得到什么

- 标题建议：`推荐标题` + 默认 `5` 个候选标题（每条附理由；规则见 `skills/nsfc-abstract/references/title-rules.md`）
- 中文摘要：默认 ≤ `400` 字符，推荐“五句式”（重要性→科学问题→可行性证据→研究内容→意义）
- 英文摘要：默认 ≤ `4000` 字符；必须是中文的忠实翻译（不扩写、不新增信息/假设）
- 输出文件：写入**当前工作目录**下的 `NSFC-ABSTRACTS.md`（文件名与分段标题可在 `config.yaml` 调整）

## 什么时候用

当你希望 AI 帮你：

- 写/润色 NSFC 标书**中文摘要 + 英文摘要**
- 把中文摘要翻成**忠实不扩写**的英文摘要
- 生成“更像中标题目”的**标题建议**（推荐 + 候选 + 理由）
- 在最后用脚本做**确定性长度校验**（可复现、可自动化）

## 快速开始（推荐 Prompt）

> 仅建议使用 Claude Code + Claude Opus 4.6 thinking 或者 OpenAI Codex CLI + GPT-5.2 High 这两种模式来使用

### 1) 开发者推荐

先填好 `skills/nsfc-abstract/references/info_form.md`，然后用：

```text
请基于 nsfc-abstract skill 为我的标书生成中英文摘要和标题
```

### 2) 零散信息驱动（没空填表也能用）

```text
请为我的 NSFC 标书生成中英文摘要并给出标题建议，要求同上。

研究对象/场景：
领域痛点/科学缺口（一句话）：
前期发现/证据（1-2 条，尽量定量）：
科学假说/核心判断（一句话）：
研究内容（3-4 点；每点写清：做什么→怎么做→验证什么/判据是什么）：
预期意义（科学机制 + 方法/策略/应用潜力，避免空话）：
```

### 3) 已有中文摘要：生成英文忠实翻译

```text
请将以下中文摘要翻译为 NSFC 英文摘要（≤4000 字符），要求：
- 忠实翻译，不新增信息、不扩写、不引入新结果
- 术语一致、语法正确
- 输出前给出英文字符数统计

[粘贴中文摘要]
```

### 4) 已有中英草稿：只润色 + 严格控长

```text
请润色以下 NSFC 摘要（中英双语），要求：
- 中文 ≤400 字符、英文 ≤4000 字符（含标点；连续空白按一个空格计数）
- 不改变核心观点；优先删减空洞背景与修饰语，避免夸大表述
- 英文必须是中文的忠实翻译
- 末尾输出长度自检（中英文字符数）

[粘贴你的中英文摘要草稿]
```

## 输出文件

| 文件 | 默认路径 | 说明 |
|---|---|---|
| `NSFC-ABSTRACTS.md` | `./NSFC-ABSTRACTS.md` | 标题建议 + 中英文摘要 + 长度自检（写在**当前工作目录**） |

输出格式示例：

```text
# 标题建议
推荐标题：...
1) ... —— 理由：...
2) ... —— 理由：...
3) ... —— 理由：...
4) ... —— 理由：...
5) ... —— 理由：...

# 中文摘要
（正文内容，≤400字符）

# English Abstract
(Translation, ≤4000 characters)

## 长度自检
- 中文摘要字符数：N/400
- 英文摘要字符数：M/4000
```

## 关键约束（必须遵守）

- 英文必须是中文的忠实翻译：不扩写、不新增信息/假设、不引入新结果。
- 默认要求“标题建议”分段（是否必需由 `config.yaml:title.title_required` 决定）。
- 中文默认 5 句、研究内容默认 3-4 点；可在 `config.yaml:limits` 调整。
- 若你给的信息不完整：更稳妥的做法是让 AI 先追问缺口，而不是直接“补写事实”。

## 配置选项

以下参数可在 `skills/nsfc-abstract/config.yaml` 中调整：

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `limits.zh_max_chars` | 400 | 中文摘要最大字符数 |
| `limits.en_max_chars` | 4000 | 英文摘要最大字符数 |
| `limits.zh_recommended_sentences` | 5 | 中文摘要推荐句数（五句式） |
| `limits.content_points_min` | 3 | 研究内容点数下限 |
| `limits.content_points_max` | 4 | 研究内容点数上限 |
| `output.filename` | `NSFC-ABSTRACTS.md` | 输出文件名（写到当前工作目录） |
| `output.zh_heading` | `# 中文摘要` | 中文分段标题 |
| `output.en_heading` | `# English Abstract` | 英文分段标题 |
| `title.title_required` | `true` | 是否要求输出标题建议分段 |
| `title.title_candidates_default` | `5` | 默认标题候选数量 |
| `title.title_heading` | `# 标题建议` | 标题建议分段的 Markdown 标题 |

## 备选用法（脚本：确定性校验/写入）

当你需要“严格控长 + 可复现校验”时，用脚本做最终把关（更完整用法见 `skills/nsfc-abstract/scripts/README.md`）：

```bash
# 严格校验（超限返回 1；格式不对返回 2）
python3 skills/nsfc-abstract/scripts/validate_abstract.py NSFC-ABSTRACTS.md --strict

# 严格写入（超限返回 1；输入可为文件或 stdin）
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_abstract.txt --strict
```

## 提示词示例（完整示例）

### 示例 1：完整信息表（推荐）

```text
请根据以下信息生成 NSFC 标书中英文摘要，并给出标题建议：

研究对象：非小细胞肺癌患者
领域痛点：免疫治疗应答率低（约20%），缺乏可靠预测标志物
前期发现：
1. 回顾性队列(n=156)发现CT影像特征与PD-L1表达相关性(AUC=0.78)
2. 单细胞测序提示肿瘤间质比与T细胞浸润呈负相关(r=-0.62)
科学假说：CT影像组学特征可反映肿瘤免疫微环境状态，预测免疫治疗反应
研究内容：
1. 构建多中心CT影像组学队列（n≥500）
2. 结合病理与单细胞数据解析影像-免疫关联机制
3. 建立并验证影像组学预测模型
4. 开发自动化分析软件工具
预期意义：为非小细胞肺癌免疫治疗提供无创预测工具

要求：
- 推荐标题 + 5 个候选标题（每条附理由）
- 中文≤400字符，五句式结构
- 英文≤4000字符，英文忠实翻译
- 末尾输出长度自检（中英文字符数）
```

### 示例 2：从立项依据/正文提炼摘要

```text
请根据以下立项依据/正文提炼 NSFC 摘要，并给出标题建议：

[粘贴你的立项依据或研究内容正文]

要求：
- 提炼核心：重要性→问题→证据/假说→内容→意义
- 研究内容压缩为 3-4 点（每点都要有“判据/验证什么”）
- 中文≤400字符，英文≤4000字符（英文忠实翻译）
- 末尾输出长度自检
```

### 示例 3：仅润色（尽量保留原结构）

```text
请润色以下 NSFC 摘要，尽量保持原有结构，仅优化表达并校验长度：

[粘贴你的中英文摘要草稿]

要求：
- 中文≤400字符，英文≤4000字符
- 不改变核心观点与逻辑结构
- 去除“国际领先/填补空白”等夸大表达
- 英文忠实翻译
- 末尾输出长度自检
```

### 示例 4：只做英文忠实翻译

```text
请将以下中文摘要翻译为 NSFC 英文摘要（≤4000字符），要求忠实翻译、不新增信息，并输出英文字符数：

[粘贴中文摘要]
```

## 常见问题（FAQ）

### Q：输出写到哪里？

A：默认写到**你当前的工作目录**，文件名为 `NSFC-ABSTRACTS.md`。例如你在仓库根目录运行/触发，本文件就是 `./NSFC-ABSTRACTS.md`。

### Q：为什么中文默认只有 400 字符？

A：这是青年基金/地区基金常见限制。面上项目或其他项目类别可能不同：你可以在 `skills/nsfc-abstract/config.yaml` 调整 `limits.zh_max_chars` 与 `limits.en_max_chars`。

### Q：一定要用“五句式”吗？

A：五句式是**推荐结构**，不是硬性要求；但无论结构怎么变，都要覆盖“重要性、科学问题、证据/假说、研究内容、意义”五要素。

### Q：信息表必须完全填满吗？

A：不需要。信息越完整，摘要质量越高；如果缺关键信息（如核心假说、前期证据、研究内容判据），更建议让 AI 先追问你补齐，而不是直接“补写事实”。

### Q：如何写入 LaTeX 正文？

A：本技能默认输出 Markdown，通常用于你在系统/表单里直接粘贴与归档。若你需要 LaTeX 格式，可以在拿到摘要后再请求：

```text
请将上述摘要转换为 LaTeX 格式，使用 \\begin{abstract}...\\end{abstract} 包裹（只包裹中文或按我指定）。
```

## WHICHMODEL（可选）

如果你想要“按场景选模型/档位”的建议，见 `skills/nsfc-abstract/WHICHMODEL_section.md`（这类建议具有时效性，仅作参考）。

## 更多文档

- `skills/nsfc-abstract/SKILL.md` — 执行指令与硬性规范
- `skills/nsfc-abstract/config.yaml` — 默认参数与限制
- `skills/nsfc-abstract/references/info_form.md` — 信息表模板
- `skills/nsfc-abstract/references/title-rules.md` — 中标题目写作规则
- `skills/nsfc-abstract/scripts/README.md` — 脚本使用说明
- `skills/nsfc-abstract/examples/demo_output.txt` — 输出示例

