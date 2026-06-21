---
name: research-idea
description: 当用户提供任意研究资料、项目背景、实验结果、论文草稿、PR/仓库信息或自然语言线索，希望“提出科学问题”“凝练研究假设”“找创新点”“判断一个想法是否值得做”时使用。该 skill 通过 research-topic-extractor 与 research-literature-review 做查新，并用 parallel-vibe 默认 3 轮串行独立审查打磨多个“科学问题-可证伪假设”候选，最终输出 Research-Idea_{github仓库名}_{pr名}_{时间戳}.md。⚠️ 不适用：用户只需要完整实验方案/分析计划（优先 research-plan）、只要写文献综述正文（优先 research-literature-review）、或只要普通头脑风暴且不需要查新。
metadata:
  author: Bensz Conan
  short-description: 基于查新与多轮独立审查提出科学问题和可证伪假设
  keywords:
    - research-idea
    - 科学问题
    - 科学假设
    - 可证伪假设
    - 研究创新点
    - 查新
    - 文献调研
    - research question
    - falsifiable hypothesis
---

# Research Idea

## 定位

把任意资料转化为多个高价值、可查新、可证伪的“科学问题-科学假设”候选，并选出最值得推进的一对。

与相邻 skill 的边界：
- `research-topic-extractor`：只负责把资料提炼成可检索主题。
- `research-literature-review`：负责 Premium 查新和证据综述。
- `parallel-vibe`：负责默认 3 轮串行独立审查与打磨。
- `research-plan`：在已有科学问题和假设后，才用于实验设计或分析计划。

## 输入

- 必需：任意资料或信息，如文本、文件、文件夹、URL、论文线索、实验现象、代码仓库或 PR 背景。
- 可选：
- 输出路径：用户指定时遵从；未指定时放在当前项目根目录。
- 工作区：用户指定时遵从；未指定时为当前工作目录下 `.bensz-api/skills/research-idea/`。
- 轮次：默认 3 轮；用户指定时遵从。

## 输出

最终交付一个 Markdown 文件，默认命名：

```text
Research-Idea_{github仓库名}_{pr名}_{时间戳}.md
```

如果无法识别 GitHub 仓库名或 PR 名，使用当前目录名与当前分支名；仍无法识别时分别使用 `repo` 与 `manual`。

报告必须包含：
- 多个科学问题-科学假设对。
- 选择理由、最佳方案及原因。
- 查新摘要、证据缺口、可证伪路径和最小下一步。

报告不得暴露 `.bensz-api/skills/research-idea/`、`tests/research-idea/`、`parallel-vibe/`、`.parallel-vibe/`、`.parallel_vibe/`、`@main/summary.md`、manifest 或其他中间产物路径。

## 工作区

- 默认工作区：`{cwd}/.bensz-api/skills/research-idea/{yyyy-mm-dd-hh-mm}/`。
- 所有中间文件、查新记录、并行审查产物、草稿和日志都必须保存在隐藏工作区内；除最终 Markdown 外，不要写到项目根目录。
- 若用户显式指定工作区，目录名仍必须是隐藏目录（以 `.` 开头），并且位于当前工作目录内；输出目录不得位于隐藏工作区内。

初始化优先使用脚本：

```bash
python3 research-idea/scripts/init_workspace.py --input-label "{简短主题或资料名}" --cwd .
# 系统级安装后也可使用：
python3 ~/.codex/skills/research-idea/scripts/init_workspace.py --input-label "{简短主题或资料名}" --cwd .
python3 ~/.claude/skills/research-idea/scripts/init_workspace.py --input-label "{简短主题或资料名}" --cwd .
```

脚本会先检查 `research-topic-extractor`、`research-literature-review` 与 `parallel-vibe`；缺失时早失败。只在开发测试时传 `--with-test-dir` 创建测试区。

## 主流程

### 1. 初始化与资料归纳

1. 运行 `scripts/init_workspace.py` 创建隐藏工作区和 manifest。
2. 读取资料，只把摘要、结构化事实和必要引用写入隐藏工作区。
3. 用 `research-topic-extractor` 生成主题、5-10 个英文关键词、2-5 个核心问题；保存为 `theme/theme.json`，字段为 `topic`、`keywords`、`core_questions`。

### 2. 提出初始候选

基于用户资料与主题结果提出 3-7 个候选。每个候选必须包含：
- 科学问题：明确研究对象、机制/关系/边界条件。
- 可证伪假设：能被实验、数据或观察推翻。
- 关键预测：如果假设成立，应观察到什么。
- 反证路径：什么结果会推翻假设。
- 初始价值判断：新颖性、重要性、可行性和风险。

避免只写宽泛主题，例如“研究 X 的机制”。科学问题必须能被一个具体研究计划承接。

### 3. 逐对查新

逐一查新每个候选，形成候选池后再比较：

1. 用 `research-topic-extractor` 把该候选转换成查新主题、关键词和核心问题。
2. 将每个候选的主题提取结果保存到 `candidates/Cx/theme.json`。
3. 调用 `research-literature-review`，档位固定为 `Premium`，输出目录限定为 `.bensz-api/skills/research-idea/*/novelty/Cx/`。
4. 每个候选必须形成 `novelty/Cx/novelty-decision.json`，字段包括：
   - `novelty_status`：`未研究` / `部分研究但关键缺口存在` / `已充分研究`
   - `direct_answer`：已有研究是否直接回答该科学问题
   - `equivalent_hypothesis_tested`：是否已有等价假设被检验
   - `key_gap`：关键缺口
   - `decision`：保留 / 修改 / 淘汰

如果所有候选均为“已充分研究”，把查新结论作为反例证据，回到步骤 2 生成下一组候选。

### 4. 多轮独立打磨

对保留或需修改的候选，用 `parallel-vibe` 做默认 3 轮串行独立审查。`rounds=3` 是外层迭代轮数，`n=3` 是每轮独立 agent 数；必须执行 3 次 `parallel-vibe`，每次把上一轮汇总后的改写版本作为下一轮输入。

```text
科学问题-科学假设有没有什么缺陷？哪里可以改进？
```

执行要求：
- 默认 `rounds=3`、每轮 `n=3`，默认串行；用户明确要求并行时才并行。
- 每轮/每个 thread 独立读取当前候选、用户资料摘要和查新摘要。
- 每个独立 agent 输出缺陷、改进建议、风险和重写版本；汇总后优化当前候选，再进入下一轮。
- `parallel-vibe` 作为内部依赖运行；读取其 summary 后只抽取结论，不向用户交付其路径。

优先使用：

```bash
for round in 1 2 3; do
  python3 parallel-vibe/scripts/parallel_vibe.py \
    --prompt "{第 ${round} 轮审查指令}" \
    --n 3 \
    --out-dir "{workspace_dir}/parallel-vibe/round-${round}"
done
```

系统级安装时可改用 `~/.codex/skills/parallel-vibe/scripts/parallel_vibe.py` 或 `~/.claude/skills/parallel-vibe/scripts/parallel_vibe.py`。

### 5. 选择最佳方案

用同一套标准比较所有保留候选：科学重要性、新颖性、可证伪性、可行性、解释力、风险透明度。最佳方案应是综合价值、可证伪性和可推进性最强的一对，不一定是最宏大的问题。

### 6. 写最终报告并验证

按 `references/report-template.md` 写最终 Markdown。写完后运行：

```bash
python3 research-idea/scripts/validate_report.py --report "{最终报告路径}"
# 系统级安装后也可使用：
python3 ~/.codex/skills/research-idea/scripts/validate_report.py --report "{最终报告路径}"
python3 ~/.claude/skills/research-idea/scripts/validate_report.py --report "{最终报告路径}"
```

若校验失败，先修复报告再交付。

## 测试区

- 默认测试区：`./tests/research-idea`。
- 测试材料、验证日志和测试报告放入该目录；最终报告不得引用测试区路径。
- 普通用户运行初始化脚本时不创建测试区；开发测试时传 `--with-test-dir`。

## 质量要求

- 科学问题必须是问题，不是主题名。
- 假设必须可证伪，不写无法被推翻的价值判断。
- 查新结论必须区分“没有研究过”和“研究过但缺口仍在”。
- 不因查新成本高而跳过 Premium 文献调研。
- 不把文献综述正文当作最终输出；最终输出是研究想法报告。
- 不泄露隐藏工作区、中间文件、agent 内部指令或测试路径。
