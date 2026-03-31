# paper-explain-figures

本 README 面向**使用者**：如何触发并正确使用 `paper-explain-figures` skill。
执行指令与硬性规范在 [SKILL.md](SKILL.md)；默认参数在 [config.yaml](config.yaml)。

旧名 `explain-figures` 已停用；请统一改用 `paper-explain-figures`。

## 用法

### 常规 Prompt（最推荐用法）

```text
请使用 paper-explain-figures skill 解读论文 Figure
输入：1 个或多个 figure 文件的绝对路径（如 /abs/path/to/figure.png）
输出：当前目录下生成 paper-explain-figures_report.md（高可读性解读报告）
```

### 进阶 Prompt（带参数约束）

```text
请使用 paper-explain-figures skill 解读论文 Figure
输入：
- figure 文件绝对路径：/abs/path/to/figure1.png, /abs/path/to/figure2.pdf
- 人工解读（可选）：这些图是关于 xxx 的分析

另外，还有下列参数约束：
- 并行模式：启用（加速多图处理）
- Runner：codex（默认）
```

## 设计理念

### 核心价值

paper-explain-figures 是你的"论文 Figure 解读老师"——不只是描述图片内容，而是**教会你如何读懂这张图**。

**三大理解维度**：
| 维度 | 来源 | 作用 |
|------|------|------|
| 视觉理解 | 从 jpg/原图直接读图 | 识别图表类型、布局、关键元素 |
| 源代码理解 | 自动检索生成该图的代码 | 以代码为准，揭示图的真实含义 |
| 人工解读 | 用户提供的背景/关注点 | 帮助推测用户关心什么 |

### 工作原理（简化版）

```
你提供 figure 路径
    ↓
自动转换为 jpg（用于视觉理解）
    ↓
在 figure 附近检索源代码（.R/.py/.ipynb 等）
    ↓
启动独立进程（codex exec / claude -p）解读
    ↓
合并为高可读性报告
```

### 只读原则

**全程只读，零风险**：
- 不会修改你的 figure 文件
- 不会修改你的源代码文件
- 中间产物只写入当前目录下 `.paper-explain-figures/`
- runner 与图片转换器的 `HOME/TMP/XDG` 运行时辅助文件也会被重定向到 `.paper-explain-figures/`

## 使用示例

### 示例 1：单图解读（最简单）

```bash
python3 paper-explain-figures/scripts/paper_explain_figures.py \
  --fig /Users/xxx/paper/figures/result_plot.png
```

输出：`paper-explain-figures_report.md`

### 示例 2：多图批量解读

```bash
python3 paper-explain-figures/scripts/paper_explain_figures.py \
  --fig /Users/xxx/paper/figures/fig1.png \
  --fig /Users/xxx/paper/figures/fig2.pdf \
  --fig /Users/xxx/paper/figures/fig3.jpg
```

### 示例 3：带人工解读（帮助模型聚焦）

```bash
python3 paper-explain-figures/scripts/paper_explain_figures.py \
  --fig /Users/xxx/paper/figures/result_plot.png \
  --note "这是关于 xxx 实验的结果，主要关注 y 轴的趋势变化"
```

### 示例 4：指定源代码路径

```bash
python3 paper-explain-figures/scripts/paper_explain_figures.py \
  --fig /Users/xxx/paper/figures/result_plot.png \
  --code-path /Users/xxx/paper/scripts/plot_results.R
```

### 示例 5：并行加速（多图场景）

```bash
python3 paper-explain-figures/scripts/paper_explain_figures.py \
  --fig /Users/xxx/paper/figures/fig1.png \
  --fig /Users/xxx/paper/figures/fig2.pdf \
  --fig /Users/xxx/paper/figures/fig3.jpg \
  --parallel \
  --max-parallel 3
```

## 输出文件

运行后，当前目录会生成：

| 文件 | 说明 |
|------|------|
| `paper-explain-figures_report.md` | 最终解读报告（你主要看这个） |
| `.paper-explain-figures/` | 中间产物目录（日志、转换图、单图解读等） |

### 报告结构（每张图）

```markdown
## Figure: xxx.png

> 文件位置： /abs/path/to/xxx.png
> 源代码： plot.R 第10-40行

### 图表核心含义
（一句话概括这张图在回答什么问题）

### 变量定义
| 元素 | 定义 |
|------|------|
| x 轴 | 时间（天） |
| y 轴 | 表达量（log2） |

### 解读要点
1. 第一个关键点
2. 第二个关键点
3. 第三个关键点

### 解释
（像教人读图一样的详细解释）

### 科学价值
（这张图能支持什么结论；有哪些误读风险）
```

## 配置选项

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--fig` | （必填） | Figure 文件绝对路径（可重复） |
| `--note` | "" | 人工解读/关注点（可重复） |
| `--code-path` | "" | 源代码文件绝对路径（可重复） |
| `--out` | `paper-explain-figures_report.md` | 报告输出路径 |
| `--parallel` | 否 | 启用并行处理 |
| `--max-parallel` | 3 | 并发上限 |
| `--runner` | codex | Runner 类型（codex/claude/local） |
| `--profile` | deep | 推理深度（default/fast/deep） |
| `--timeout-seconds` | 0 | 单图超时（0=不超时） |

### 配置文件（config.yaml）

如需修改默认行为，编辑 [config.yaml](config.yaml)：

```yaml
defaults:
  execution: "serial"      # serial|parallel
  max_parallel: 3          # 并发上限
  runner_type: "codex"     # codex|claude|local
  runner_profile: "deep"   # default|fast|deep
```

### Runner 隔离说明

- `shell` runner 已禁用：它无法对“.paper-explain-figures 之外绝不泄露中间文件”提供严格保证
- `codex` / `claude` / `local` 会在 job 目录下执行，并把 HOME、TMP、XDG cache/state/config 等运行时目录重定向进 `.paper-explain-figures/`
- 脚本结束前会审计当前工作目录；若发现 `.paper-explain-figures/` 外新增了非结果文件，会自动清理并报错/告警

## 源代码检索机制

技能会自动在 figure 附近检索生成该图的源代码：

**检索范围**：
- Figure 所在目录
- 向上 N 层父目录（默认 2 层，可在 config.yaml 调整）

**支持的代码文件类型**：
`.R` `.Rmd` `.qmd` `.py` `.ipynb` `.jl` `.m` `.tex` `.sh`

**匹配策略**：
- 强匹配：代码中出现完整文件名（如 `result_plot.png`）
- 弱匹配：代码中出现文件名主干（如 `result_plot`，需 ≥8 字符）

## 清理中间文件

如需清理中间产物：

```bash
rm -rf .paper-explain-figures
```

## 常见问题

### Q：为什么需要绝对路径？

A：技能在独立进程中运行，相对路径可能导致找不到文件。绝对路径确保无论进程从哪里启动都能正确定位。

### Q：源代码检索失败怎么办？

A：可能原因：
1. 代码文件不在检索范围内 → 使用 `--code-path` 显式指定
2. 代码中未出现 figure 文件名 → 正常情况，报告会显示"源代码：NULL"
3. 文件名太短（<8 字符）→ 弱匹配被禁用，只使用完整文件名匹配

### Q：并行模式安全吗？

A：默认串行更稳定（减少 API 限流风险）。如需并行，建议并发上限 ≤3。

### Q：支持哪些 figure 格式？

A：常见格式都支持（png/jpg/pdf/tiff 等）。技能会自动转换为 jpg 用于视觉理解；转换失败时会保留原图并说明。

### Q：解读质量不高怎么办？

A：尝试以下方法：
1. 提供更具体的人工解读（`--note`）
2. 显式指定源代码路径（`--code-path`）
3. 使用更深的推理 profile（`--profile deep`，已是默认）

## 不适用场景

本技能**不适用**于：
- 只想改图尺寸/裁剪/改格式 → 使用图片处理工具
- 要求直接修改图片/源代码 → 本技能全程只读
- 非论文/学术图表 → 通用图片理解应使用其他工具

## 相关文档

- [SKILL.md](SKILL.md) — AI 执行规范
- [config.yaml](config.yaml) — 默认配置
- [CHANGELOG.md](CHANGELOG.md) — 版本历史
