# nsfc-abstract — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-abstract` skill。
执行指令与硬性规范在 [SKILL.md](SKILL.md)；默认参数在 [config.yaml](config.yaml)。

---

## 快速开始

### 开发者

简单一句话足矣：

```
基于./projects/NSFC_Young/extraTex 的正文内容， 使用 nsfc-abstract 这个skill写摘要。
```

### 最推荐：信息表驱动

请先填写 [信息表模板](references/info_form.md)，然后用以下 Prompt 让 AI 生成摘要：

```
请根据以下信息表生成 NSFC 标书中英文摘要，要求：
- 中文≤400字符，英文≤4000字符
- 五句式结构（重要性→科学问题→可行性证据→研究内容→意义）
- 英文是中文的忠实翻译

[粘贴信息表内容]
```

### 备选：从零散信息生成

如果你没有填写完整信息表，也可以直接描述：

```
请为我的 NSFC 标书生成中英文摘要。

研究对象：[你的研究对象]
领域痛点：[一句话概括当前瓶颈]
前期发现：[1-2条定量证据]
科学假说：[一句话]
研究内容：[3-4点，每点写清做什么/怎么做/验证什么]
预期意义：[一句话]
```

### 润色现有摘要

如果已有草稿需要润色：

```
请润色以下 NSFC 摘要，要求：
- 中文控制在400字符内，英文控制在4000字符内
- 优化学术表达，去除夸大用语
- 调整为五句式结构
- 确保英文是中文的忠实翻译

[粘贴你的中英文摘要]
```

---

## 功能概述

**核心价值**：给出“更像中标题目”的标题候选（默认 1 个推荐标题 + 5 个备选标题及理由），并写出"评审一眼读懂"的五句式摘要，做到**重要性**、**科学问题**、**可行性证据**、**研究内容**、**科学意义**五个要素齐全；输出与之一致的英文忠实翻译。

**工作原理**：
1. AI 收集关键信息（通过信息表或问答）
2. 基于历年立项题目共性生成标题候选（规则见 `references/title-rules.md`）
3. 按"五句式"结构组织中文摘要
4. 生成英文忠实翻译（不扩写、不新增假设）
5. 输出到 `NSFC-ABSTRACTS.md` 并自动校验长度（含标题建议检查）

**与其他技能的配合**：
- [nsfc-justification-writer](../nsfc-justification-writer/)：撰写立项依据
- [nsfc-research-content-writer](../nsfc-research-content-writer/)：撰写研究内容
- [nsfc-research-foundation-writer](../nsfc-research-foundation-writer/)：撰写研究基础

---

## 提示词示例

### 示例 1：完整信息表（推荐）

```
请根据以下信息生成 NSFC 标书中英文摘要：

项目题目：肺癌免疫治疗反应预测的多模态影像组学研究

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
- 中文≤400字符，英文≤4000字符
- 五句式结构，英文忠实翻译
```

### 示例 2：从立项依据提炼摘要

```
请根据以下立项依据提炼 NSFC 摘要（400字/4000字符）：

[粘贴你的立项依据正文]

要求：
- 提炼核心：重要性→问题→假说→内容→意义
- 研究内容压缩为3-4点
- 生成中英文双语版本
```

### 示例 3：仅润色不重组（保留原结构）

```
请润色以下 NSFC 摘要，保持原有结构，仅优化表达并校验长度：

[粘贴你的摘要]

要求：
- 不改变核心观点与逻辑结构
- 优化学术用语，去除"国际领先/填补空白"等夸大表达
- 确保英文是中文的忠实翻译
- 输出字符数统计
```

### 示例 4：翻译现有中文摘要

```
请将以下中文摘要翻译为 NSFC 英文摘要（≤4000字符），要求：
- 忠实翻译，不新增信息
- 术语一致，语法正确
- 符合学术表达习惯

[粘贴中文摘要]
```

---

## 输出文件

| 文件 | 路径 | 说明 |
|------|------|------|
| **标题+摘要** | `NSFC-ABSTRACTS.md` | 工作目录下的输出文件，包含标题建议、中英文摘要与长度自检 |

### 输出格式

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

---

## 配置选项

以下参数可在 [config.yaml](config.yaml) 中调整：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `limits.zh_max_chars` | 400 | 中文摘要最大字符数 |
| `limits.en_max_chars` | 4000 | 英文摘要最大字符数 |
| `limits.zh_recommended_sentences` | 5 | 中文摘要推荐句数（五句式） |
| `limits.content_points_min/max` | 3/4 | 研究内容点数范围 |
| `output.filename` | `NSFC-ABSTRACTS.md` | 输出文件名 |
| `output.zh_heading` | `# 中文摘要` | 中文标题 |
| `output.en_heading` | `# English Abstract` | 英文标题 |
| `title.title_required` | `true` | 是否要求输出标题建议分段 |
| `title.title_candidates_default` | `5` | 默认标题候选数量 |
| `title.title_heading` | `# 标题建议` | 标题分段的 Markdown 标题 |

---

## 备选用法（脚本调用）

如果需要确定性写入或校验，可以使用以下脚本：

### 长度校验

```bash
# 校验摘要长度
python3 skills/nsfc-abstract/scripts/validate_abstract.py NSFC-ABSTRACTS.md

# 严格模式（超限返回退出码1）
python3 skills/nsfc-abstract/scripts/validate_abstract.py NSFC-ABSTRACTS.md --strict

# 从管道读取
cat NSFC-ABSTRACTS.md | python3 skills/nsfc-abstract/scripts/validate_abstract.py -

# 机器可读 JSON 输出（包含 exceeded 差值）
python3 skills/nsfc-abstract/scripts/validate_abstract.py NSFC-ABSTRACTS.md --json --diff

# 如需向后兼容旧输出（不要求标题分段）
python3 skills/nsfc-abstract/scripts/validate_abstract.py NSFC-ABSTRACTS.md --no-title
```

### 写入文件

```bash
# 将摘要内容写入 NSFC-ABSTRACTS.md
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_abstract.txt

# 严格模式（超限不写入）
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_abstract.txt --strict

# 从管道读取
cat your_abstract.txt | python3 skills/nsfc-abstract/scripts/write_abstracts_md.py -

# 超限自动压缩（占位：当前版本不执行压缩，仅提示并返回 1）
python3 skills/nsfc-abstract/scripts/write_abstracts_md.py your_abstract.txt --auto-compress
```

**退出码**：
- `0`：成功（严格模式下未超限）
- `1`：超限
- `2`：格式错误

---

## 常见问题（FAQ）

### Q：为什么中文只有 400 字符？

A：这是 NSFC 青年基金/地区基金的官方限制。面上项目可能有不同要求，可通过 [config.yaml](config.yaml) 调整 `limits.zh_max_chars`。

### Q：英文 4000 字符怎么这么长？

A：英文单词数与中文字符数不等价。4000 字符约 600-700 单词，与中文 400 字符的信息量相当。

### Q：一定要用"五句式"吗？

A：五句式是**推荐结构**，不是硬性要求。如果你的内容更适合其他结构，可以灵活调整，但必须确保五个要素齐全。

### Q：信息表必须完全填满吗？

A：不需要。信息越完整，摘要质量越高；但部分空白不影响生成，AI 会用合理推断填充。

### Q：如何写入 LaTeX 正文？

A：本技能默认输出 Markdown。如需 LaTeX 格式，可以请求 AI：

```
请将上述摘要转换为 LaTeX 格式，使用 \begin{abstract}...\end{abstract} 环境包裹。
```

### Q：英文摘要不够地道怎么办？

A：可以分两步：
1. 先用本技能生成结构完整的初稿
2. 再用"润色以下英文摘要"请求优化表达（同时要求保持结构不变）

---

## WHICHMODEL - 模型选择最佳实践

**最后更新**：2026-02-03

### 披露信息

- **覆盖厂商**：Anthropic, OpenAI, 国产模型（DeepSeek等）（3/9 ≈ 33%）
- **来源构成**：社区讨论 50%, 官方文档 20%, 学术研究 15%, 博客 15%
- **数据时效**：2024-06 至 2026-02
- **局限性**：未涵盖 Meta/Mistral 等厂商；国产模型证据主要来自中文社区；未进行独立测试验证

### 场景化建议

#### 场景 1：首次生成 NSFC 摘要（完整信息表）

**触发条件**：首次使用，有完整信息表，预算中等

| 项目 | 建议 |
|------|------|
| **推荐模型** | Claude Sonnet 4.5 |
| **推理强度** | medium |
| **预期成本** | ¥2-5/次 |

**理由**：Sonnet 在学术写作中性价比高，社区反馈显示其"写作和分析质量更好，更具学术性" [来源：Reddit 讨论](https://www.reddit.com/r/ClaudeAI/comments/1ntox7v/sonnet_45_vs_opus_41_for_academic_writing/)

**避免**：极端复杂的科学假说、需要深度领域知识

#### 场景 2：高质量摘要（评审优先）

**触发条件**：标书质量优先，预算充足，需要顶级学术表达

| 项目 | 建议 |
|------|------|
| **推荐模型** | Claude Opus 4.5 |
| **推理强度** | high |
| **Thinking 模式** | 开 |
| **预期成本** | ¥8-15/次 |

**理由**：Opus 在约 81% 的任务中表现优于 Sonnet，摘要推理能力更强 [来源：DataStudios 对比](https://www.datastudios.org/post/claude-opus-4-5-vs-claude-sonnet-4-5-full-report-and-comparison-of-features-performance-pricing-a)

**避免**：成本敏感、需要多次迭代

#### 场景 3：润色现有摘要（快速优化）

**触发条件**：已有草稿，仅需润色表达、校验长度

| 项目 | 建议 |
|------|------|
| **推荐模型** | Claude Haiku 4.5 或 DeepSeek-V3 |
| **推理强度** | low |
| **预期成本** | ¥0.5-2/次 |

**理由**：Haiku 响应快速，成本最低；DeepSeek 对中文科学写作理解优秀 [来源：CSDN/知乎社区](https://zhuanlan.zhihu.com/p/21450843232)

**避免**：从零生成、复杂科学内容

#### 场景 4：中英双语摘要生成

**触发条件**：需要中英文双语版本，英文要求忠实翻译

| 项目 | 建议 |
|------|------|
| **推荐模型** | Claude Sonnet 4.5 或 GPT-4o |
| **推理强度** | medium |
| **预期成本** | ¥3-8/次 |

**理由**：Claude 在双语翻译语义边界控制上表现优秀；GPT-4o 在跨语言任务中表现稳定

**避免**：极度专业的术语翻译（需人工校验）

#### 场景 5：中文语境优先（国产模型推荐）

**触发条件**：纯中文摘要，需要理解中国科研语境

| 项目 | 建议 |
|------|------|
| **推荐模型** | DeepSeek-V3 或 DeepSeek-R1 |
| **推理强度** | medium-high |
| **预期成本** | ¥0.1-1/次 |

**理由**：DeepSeek 在 MMLU 基准上达 90.8%，对中文科学写作理解优秀，且推理透明 [来源：腾讯云开发者](https://cloud.tencent.com/developer/article/2504192)

**避免**：英文摘要翻译（建议用 Claude/GPT-4）

### 对比总结

| 模型 | 最适合 | 最不适合 | 相对成本 | 推荐度 |
|------|-------|---------|---------|-------|
| Opus | 高质量摘要、评审优先 | 成本敏感 | $$$$ | ⭐⭐⭐⭐ |
| Sonnet | 标准摘要、首次生成 | 极端复杂 | $$ | ⭐⭐⭐⭐⭐ |
| Haiku | 快速润色、长度校验 | 从零生成 | $ | ⭐⭐⭐ |
| DeepSeek | 中文语境、成本敏感 | 英文翻译 | $ | ⭐⭐⭐⭐ |
| GPT-4o | 双语翻译、通用任务 | 纯中文优化 | $$$ | ⭐⭐⭐⭐ |

### 通用原则

1. **先试 Sonnet**：性价比最高，90% 场景够用
2. **质量优先升级 Opus**：评审关键标书时值得投入
3. **中文考虑 DeepSeek**：成本低，中文科学写作理解好
4. **双语验证**：生成后务必人工校验英文忠实度
5. **长度校验**：无论用哪个模型，最后都用脚本校验字符数

### ⚠️ 争议点：Sonnet vs Opus

| 观点 | 支持者 | 理由 |
|------|-------|------|
| **应该用 Sonnet** | Reddit 社区 | 性价比更高，写作质量"更具学术性" |
| **应该用 Opus** | Anthropic 官方 | 最强推理能力，约 81% 任务表现更好 |

**建议**：首次生成/预算有限用 Sonnet；评审优先/预算充足用 Opus

---

## 更多文档

- [SKILL.md](SKILL.md) — 执行指令与硬性规范
- [config.yaml](config.yaml) — 配置参数
- [references/info_form.md](references/info_form.md) — 信息表模板
- [scripts/README.md](scripts/README.md) — 脚本使用说明
- [examples/demo_output.txt](examples/demo_output.txt) — 输出示例
