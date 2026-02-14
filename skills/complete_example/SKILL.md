---
name: complete-example
description: 当用户明确要求"填充示例内容""生成示例""补充 LaTeX 示例"时使用。AI 增强版 LaTeX 示例智能生成器，实现 AI 与硬编码的有机融合：AI 做"语义理解"（分析章节主题、推理资源相关性、生成连贯叙述），硬编码做"结构保护"（格式验证、哈希校验、访问控制）。
metadata:
  short-description: AI 增强版 LaTeX 示例智能生成器
  keywords:
    - latex
    - 示例生成
    - AI 增强
    - 格式保护
    - 语义理解
    - 资源整合
    - nsfc
  triggers:
    - 填充示例
    - 生成示例
    - complete example
    - 补充示例内容
config: skills/complete_example/config.yaml
---

# complete_example Skill - AI 增强版 LaTeX 示例智能生成器

## 简介

**complete_example** 是一个充分发挥 AI 优势的 LaTeX 示例智能生成器，实现 AI 与硬编码的有机融合。

**核心设计理念**：AI 做"语义理解"，硬编码做"结构保护"

## 功能特性

### 核心能力

| 能力维度 | 说明 |
|---------|------|
| **语义理解** | AI 理解章节主题，智能判断需要什么类型的资源 |
| **智能推理** | AI 推断资源与章节的相关性，并给出理由 |
| **连贯生成** | AI 生成自然流畅的叙述性文本，而非模板拼接 |
| **上下文感知** | 根据上下文调整描述风格 |
| **自我优化** | AI 自我审查并优化生成内容 |
| **格式安全** | 🔒 硬编码严格保护格式设置，哈希验证防篡改，访问控制 |

### 用户提示机制

支持用户自定义叙事提示（`narrative_hint`），AI 根据提示编造合理的示例内容：

- 🏥 **医疗影像**：深度学习在医疗影像分析中的应用
- 🔬 **材料科学**：新型纳米材料合成与表征
- 🧪 **临床试验**：多中心临床试验设计
- 🤖 **传统 ML**：支持向量机分类方法

## 使用方法

### 基本语法

```
/complete_example <project_name> [options]
```

### 参数说明

#### 必需参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `project_name` | string | 项目名称（如 `NSFC_Young`）或项目路径 |

#### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--content-density` | string | `moderate` | 内容密度：`minimal`(2资源/200字) / `moderate`(4资源/300字) / `comprehensive`(6资源/500字) |
| `--output-mode` | string | `preview` | 输出模式：`preview`(预览) / `apply`(应用) / `report`(报告) |
| `--target-files` | array | `null` | 目标文件列表（如 `["extraTex/2.1.研究内容.tex"]`），null 表示自动检测 |
| `--narrative-hint` | string | `null` | 用户自定义叙事提示，指导 AI 生成特定风格的示例内容 |

### 使用示例

#### 示例 1：基本使用（AI 自动推断）

```
/complete_example NSFC_Young --content-density moderate --output-mode preview
```

#### 示例 2：使用用户提示

```
/complete_example NSFC_Young --narrative-hint "生成一个关于深度学习在医疗影像分析中应用的示例，重点关注 CNN 架构和数据增强策略"
```

#### 示例 3：材料科学场景

```
/complete_example NSFC_Young --narrative-hint "创建一个关于新型纳米材料合成与表征的示例，包括 XRD、SEM 等表征方法"
```

#### 示例 4：临床试验场景

```
/complete_example NSFC_Young --narrative-hint "模拟一个多中心临床试验的设计与分析流程，重点描述随机化和盲法实施"
```

## 输出说明

### 运行目录结构

所有运行输出都保存在 **目标项目的隐藏目录** `{project_path}/.complete_example/<run_id>/` 中，不污染项目目录：

```
{project_path}/.complete_example/<run_id>/
├── backups/           # 备份文件
├── logs/              # 日志文件
├── analysis/          # AI 分析结果
├── output/            # 生成内容
└── metadata.json      # 运行元数据
```

**设计原理**：
- ✅ **项目隔离**：每个项目都有独立的 `.complete_example` 目录
- ✅ **隐藏保护**：使用点号前缀（`.`）使目录在常规文件列表中隐藏
- ✅ **硬编码保证**：所有中间文件路径都通过硬编码方式确保存放在此目录中
- ✅ **可追溯性**：每次运行都有唯一的 `run_id`（格式：`v{timestamp}_{hash}`）
- ✅ **便于清理**：可直接删除 `.complete_example` 目录清理所有中间文件

### 质量报告

AI 会自动评估生成内容的质量，包括：
- 连贯性评分（0-1）
- 学术风格评分（0-1）
- 资源整合评价
- 改进建议

## 工作流程

```
1. 🔍 扫描阶段
   └─ 扫描 figures/、code/、references/ 资源

2. 🧠 分析阶段
   └─ AI 分析章节主题、关键概念、写作风格

3. 💡 推理阶段
   └─ AI 推理资源相关性并给出理由

4. ✍️ 生成阶段
   └─ AI 生成连贯的叙述性内容（支持用户提示）

5. 🎨 包装阶段
   └─ 硬编码包装为 LaTeX 代码

6. 🔍 优化阶段
   └─ AI 自我审查和优化

7. ✅ 验证阶段
   └─ 格式验证、编译验证

8. 📊 报告阶段
   └─ 生成质量报告
```

## 架构设计

### AI 与硬编码职责分工

| 任务类型 | AI 负责 | 硬编码负责 |
|---------|--------|-----------|
| 文件扫描 | - | ✅ 文件系统操作、元数据提取 |
| 语义分析 | ✅ 章节主题理解、关键概念提取 | - |
| 资源选择 | ✅ 推理相关性、给出理由 | ✅ 评分排序、Top-K 选择 |
| 文本生成 | ✅ 叙述性内容生成 | - |
| LaTeX 包装 | - | ✅ 语法正确性、格式规范 |
| 格式保护 | ✅ 解释修改意图、诊断问题 | ✅ 严格验证、哈希校验 |

### 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                        用户接口层                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  CLI 命令    │  │  Skill 调用  │  │  Python API  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                     AI 增强工作流层                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │  CompleteExampleSkill (主控制器)                │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   AI 智能层（Semantic Layer）             │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ SemanticAnalyzer │  │ AIContentGenerator│            │
│  └──────────────────┘  └──────────────────┘            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                 硬编码保护层（Structure Layer）           │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  ResourceScanner │  │   FormatGuard    │            │
│  └──────────────────┘  └──────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

## 配置文件

配置文件位于 `skills/complete_example/config.yaml`，包含：

- LLM 配置（provider、model、temperature 等）
- 参数定义（content_density、output_mode 等）
- 运行管理配置（runs_root、retention、backup 等）
- 资源扫描配置
- 内容生成配置
- 格式保护配置
- AI 提示词模板
- 质量评估标准

## 安全机制

### 🔒 分层安全保护

#### Layer 1: 系统文件保护（黑名单）

**绝对禁止修改的文件**：
- `main.tex` - 项目入口文件
- `extraTex/@config.tex` - 格式配置文件
- `@config.tex` - 格式配置文件（别名）

**保护机制**：
- ✅ 黑名单访问控制：任何对系统文件的修改尝试都会被拒绝
- ✅ SHA256 哈希校验：检测文件是否被外部篡改
- ✅ 自动初始化：首次运行时自动生成哈希指纹

```python
# 示例：尝试修改系统文件会抛出异常
try:
    skill.generate_content("main.tex", "...")
except SystemFileModificationError as e:
    print(e)  # 🚨 禁止访问系统文件：main.tex
```

#### Layer 2: 章节层级规范（结构保护）

**核心规则**：不同文件类型使用不同的章节层级

| 文件类型 | 允许的层级 | 禁止的层级 |
|---------|-----------|-----------|
| `main.tex` | `\section`、`\subsection` | - |
| `extraTex/*.tex`（input 类） | `\subsubsection`、`\subsubsubsection` | `\section`、`\subsection` |

**双层级生成要求**：

每个正文类的 input tex 文件必须同时使用两个层级：

```yaml
generation_requirement:
  require_both_levels: true  # 必须同时使用两个层级
  min_subsubsection: 1       # 每个文件至少 1 个 subsubsection
  min_subsubsubsection: 1    # 每个 subsubsection 下至少 1 个 subsubsubsection
```

**示例结构**：
```latex
\subsubsection{研究背景}
\subsubsubsection{国内研究现状}
...内容...
\subsubsubsection{国外研究现状}
...内容...

\subsubsection{研究意义}
\subsubsubsection{理论意义}
...内容...
\subsubsubsection{实践意义}
...内容...
```

**设计原理**：
- `main.tex` 作为项目入口，负责顶层结构（section/subsection）
- `input` 类 tex 文件作为内容模块，使用 subsubsection + subsubsubsection 双层级
- 这种分离确保结构清晰、层次丰富、职责明确

**检查模式**：
```yaml
enforcement:
  enabled: true
  mode: "strict"  # strict: 拒绝违规 / warn: 警告但允许 / off: 关闭
  auto_fix: false  # 是否自动修正（建议关闭）
```

#### Layer 3: 用户内容文件保护（白名单）

**允许编辑的文件模式**：
```yaml
editable_patterns:
  - "^extraTex/\\d+\\.\\d+.*\\.tex$"  # 1.1.xxx.tex, 2.3.xxx.tex 等
  - "^references/reference\\.tex$"
```

**保护机制**：
- ✅ 白名单模式匹配：只允许编辑符合正则表达式的文件
- ⚠️ 警告机制：编辑白名单之外的文件会触发警告

#### Layer 4: 内容安全扫描

**格式注入检测**：
- 扫描生成内容中的格式关键词（如 `\geometry`、`\setlength`）
- 自动注释掉危险行（可选）
- 二次验证确保清理成功

**黑名单关键词**：
```yaml
format_keywords_blacklist:
  - "\\geometry{"
  - "\\setlength{"
  - "\\definecolor{"
  - "\\setCJKfamilyfont"
  - "\\setmainfont"
  - "\\titleformat{"
  - "\\usepackage{"
  - "\\documentclass"
```

### 格式保护

- **受保护的文件**：`extraTex/@config.tex`、`main.tex` 等
- **受保护的命令**：`\setlength`、`\geometry`、`\definecolor` 等
- **哈希验证**：计算关键格式文件的 SHA256 哈希值，防止篡改
- **自动备份**：修改前自动备份到 `.complete_example/<run_id>/backups/`
- **自动回滚**：格式保护失败或编译失败时自动回滚
- **访问控制**：黑名单 + 白名单双重保护
- **格式注入扫描**：自动检测并清理危险的格式指令

### 编译验证

- 修改文件后自动执行 `xelatex` 编译
- 编译失败则自动回滚
- 编译日志保存在 `.complete_example/<run_id>/logs/compile.log`

## 依赖要求

### Python 依赖

```
- anthropic (Claude API)
- openai (OpenAI API)
- PIL (图片元数据提取)
- pyyaml (配置文件解析)
- jinja2 (模板引擎)
```

### LaTeX 依赖

```
- xelatex (编译引擎)
- ctex (中文支持)
- listings (代码清单)
- graphicx (图片支持)
```

## 最佳实践

### 1. 优先使用预览模式

首次使用时，建议使用 `--output-mode preview` 查看生成效果：

```
/complete_example NSFC_Young --output-mode preview
```

### 2. 充分利用用户提示

通过 `--narrative-hint` 指定研究主题，可以获得更符合预期的示例：

```
/complete_example NSFC_Young --narrative-hint "生成一个关于 XXX 的示例"
```

### 3. 选择合适的内容密度

根据章节重要性选择密度：
- `minimal`：快速填充，适合次要章节
- `moderate`：平衡选择，适合大多数章节
- `comprehensive`：详细示例，适合核心章节

### 4. 定期清理运行记录

使用 `--auto-cleanup` 配置自动清理过期运行记录：

```yaml
run_management:
  retention:
    max_runs: 50
    max_age_days: 30
    auto_cleanup: true
```

## 故障排除

### 问题 1：格式被意外修改

**原因**：AI 生成内容时破坏了格式定义

**解决方案**：
1. 检查 `.complete_example/<run_id>/logs/format_check.log`
2. 查看备份文件 `.complete_example/<run_id>/backups/`
3. 手动恢复或调整提示后重试

### 问题 2：编译失败

**原因**：生成的 LaTeX 代码有语法错误

**解决方案**：
1. 检查 `.complete_example/<run_id>/logs/compile.log`
2. 查看具体错误信息
3. 调整 AI 温度参数或修改提示

### 问题 3：生成质量不理想

**原因**：AI 理解偏差或温度参数过高

**解决方案**：
1. 使用更明确的 `--narrative-hint`
2. 降低 `temperature` 参数
3. 使用更强大的 LLM 模型

## 许可证

与主项目保持一致。

---

**提示**：详细的设计文档请参考 [plans/v202601071300.md](../../plans/v202601071300.md)
