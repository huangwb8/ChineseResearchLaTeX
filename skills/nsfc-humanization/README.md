# nsfc-humanization — 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `nsfc-humanization` skill。  
执行指令与硬性规范在 `SKILL.md`；默认元信息在 `config.yaml`。

---

## ✅ 快速开始（推荐用法）

| 你的需求 | 推荐用法 | 理由 |
|---|---|---|
| 去掉“机器味”，但不改内容 | 直接贴文本并声明“只润色表达” | 最稳妥、风险最低 |
| 文本含 LaTeX | 明确“保持 LaTeX 结构/引用/数学不变” | 避免破坏编译 |
| 文本含列表/图表标题 | 说明“`\item`/`\caption{}` 结构必须保留，只改自然语言” | 避免破坏环境/命令结构 |
| 轻微润色 | 说明“最小改动” | 保留原句结构 |
| 想要可控强度/变更摘要/跨段一致 | 显式声明参数（`strength/output_mode/STYLE_CARD`） | 可验可控、整篇一致 |

### 最推荐

```
请使用 nsfc-humanization 润色以下段落（仅润色表达，不新增信息，不改 LaTeX 结构）：

[粘贴你的标书文本]
```

### 场景化变体

**- 含 LaTeX**
```
请用 nsfc-humanization 润色以下段落，保持所有 LaTeX 命令/引用 key/数学公式不变：

[粘贴含 LaTeX 的文本]
```

**- 最小改动**
```
请用 nsfc-humanization 轻微润色以下段落，只改明显的“机器味”句子：

[粘贴文本]
```

---

## ✨ 功能概述

- 目标：去除 NSFC 标书中的“机器味”，让文本更像资深领域专家撰写
- 核心原则：不改内容、不补充信息、不调整格式
- 适用对象：NSFC 各类基金申请书正文（纯文本或 LaTeX 混合文本）
- 典型高收益改法：把“括号套括号 + 分号罗列（数据来源/规模等）”改写为正常句子流（更顺、更像人写）

> 关键约束详见 `SKILL.md`（包括“结构保护”“语义零损失”“提示词注入防护”）。

---

## 📎 使用示例（按场景）

### 示例 1：纯文本（最简单）
```
本研究首先对现有方法进行了系统综述，其次分析了其局限性，最后提出了新的解决方案。
```

### 示例 2：LaTeX 混合文本
```latex
\subsection{研究意义}

本研究的意义主要体现在以下几个方面。首先，从理论层面来看，本研究填补了领域内的空白。
```

---

## 📦 输出与配置

- 输出文件：无（直接返回润色文本）
- 可配置参数：支持（见 `SKILL.md` 的“可选控制参数 / output_mode / STYLE_CARD”）

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 执行规范与硬性约束 |
| `config.yaml` | 版本与元信息（单一真相来源） |
| `references/machine-patterns.md` | 机器味识别与对比示例 |

---

## 🎛️ 常用参数（可选）

默认情况下输出仅为润色文本（最适合直接粘贴回 LaTeX）。若你需要更强可控性，可显式声明：

- `section_type`：`立项依据/研究内容/研究基础/工作条件/风险应对/通用`
- `field`：`general/cs/engineering/medicine/life_science`
- `strength`：`minimal`（默认）/ `moderate` / `aggressive`
- `output_mode`：`text_only`（默认）/ `text_with_change_summary` / `diagnosis_only` / `text_with_change_summary_and_style_card`

### 示例：带强度与变更摘要

```
请用 nsfc-humanization 润色以下段落：
section_type=研究内容
field=cs
strength=moderate
output_mode=text_with_change_summary

[粘贴文本]
```

### 示例：跨段落一致（STYLE_CARD）

第一段建议用：

```
请用 nsfc-humanization 润色以下段落，并输出 STYLE_CARD：
output_mode=text_with_change_summary_and_style_card

[第 1 段]
```

后续段落把上次生成的 `STYLE_CARD` 一并贴回，即可尽量保持整篇一致。

---

## ❓ 常见问题（FAQ）

**Q：会修改 LaTeX 命令或引用 key 吗？**  
不会。`\cite{}`/`\ref{}`/数学公式等均保持原样。

**Q：会补充新内容吗？**  
不会。本技能只润色表达，不新增任何实质性信息。

**Q：可以处理整篇标书吗？**  
建议按段落/小节分批处理，便于逐段核查。

**Q：润色后还需要人工审核吗？**  
建议审核，尤其是专业术语与事实边界。

**Q：如果原文里夹杂了类似“忽略上述规则/输出英文”的指令句子怎么办？**  
这些内容会被视为“原文正文”的一部分，不会被当成指令执行；你仍应按需要核查润色结果是否满足“结构保护 + 语义零损失”。

---

## 版本

0.4.0 — 详见 [CHANGELOG.md](CHANGELOG.md)
