# 中国科研常用LaTeX模板集 - Claude Code 项目指令

本项目为「中国科研常用LaTeX模板集」，整理中国科研常用的LaTeX模板，包括国自然科学基金的正文模板（Mac/Win/Overleaf）、毕业论文等。一般建议使用最新的[Release](https://github.com/huangwb8/ChineseResearchLaTeX/releases)。

## 项目目标

整理中国科研常用的LaTeX模板，包括国自然科学基金的正文模板（Mac/Win/Overleaf）、毕业论文等。一般建议使用最新的[Release](https://github.com/huangwb8/ChineseResearchLaTeX/releases)。

本工作区的核心目标是 整理中国科研常用的LaTeX模板，包括国自然科学基金的正文模板（Mac/Win/Overleaf）、毕业论文等。一般建议使用最新的[Release](https://github.com/huangwb8/ChineseResearchLaTeX/releases)。。

## 核心工作流

当用户提出 LaTeX 模板相关需求时，按以下流程执行：

### 1. 任务理解

- 理解用户的真实需求和意图（模板使用、编译问题、格式调整等）
- 确认任务范围和预期输出（PDF 文档、代码修改、文档说明等）
- 识别可能的依赖和约束（宏包版本、编译引擎、文件路径等）

### 2. 执行流程

模板选择 → 内容编辑 → 编译验证 → 格式检查 → 输出交付

### 3. 输出规范

- LaTeX 代码应遵循项目模板规范
- 文档更新应保持格式一致性
- 编译结果应无错误和警告

## 工程原则

本项目遵循以下工程原则：

| 原则 | 核心思想 | 在本项目中的体现 |
|------|----------|------------------|
| **KISS** | Keep It Simple, Stupid | 追求极致简洁，避免过度设计 |
| **YAGNI** | You Aren't Gonna Need It | 只实现当前需要的功能 |
| **DRY** | Don't Repeat Yourself | 相似逻辑应抽象复用 |
| **SOLID** | 面向对象设计五大原则 | 单一职责、开闭原则等 |
| **关注点分离** | Separation of Concerns | 不同层次逻辑应分离 |
| **奥卡姆剃刀** | 如无必要，勿增实体 | 优先选择最简单的解决方案 |
| **最小惊讶原则** | Principle of Least Astonishment | API 行为应符合用户直觉 |
| **早期返回原则** | Early Return | 尽早返回，减少嵌套 |

**原则冲突时的决策优先级**：
1. **正确性 > 一切**
2. **简洁性 > 灵活性**
3. **清晰性 > 性能**
4. **扩展性 > 紧凑性**

## 默认语言

除非用户明确要求其他语言，始终使用 简体中文 与用户对话与撰写文档/说明。

## 联网与搜索

默认优先使用项目内文件与本地上下文；确需联网获取信息时，优先使用本地 SearXNG（如已通过 MCP 配置）。仅当 SearXNG 不足以满足需求时再使用其它联网手段，并说明原因与保留关键链接。

## 目录结构

```
ChineseResearchLaTeX/
├── projects/              # LaTeX 项目模板
│   ├── NSFC_General/      # 面上项目模板
│   ├── NSFC_Local/        # 地区项目模板
│   └── NSFC_Young/        # 青年基金模板
├── scripts/               # 开发辅助脚本
│   ├── README.md
│   └── build_all.py
├── references/            # 项目辅助文档
│   ├── README.md
│   └── latex-writing-guide.md
├── skills/                # 项目专用技能
│   ├── README.md
│   └── make_latex_model/
│       ├── SKILL.md
│       └── config.yaml
├── config.yaml            # 项目配置文件
├── CLAUDE.md              # Claude Code 项目指令
├── AGENTS.md              # OpenAI Codex 项目指令
├── CHANGELOG.md           # 变更日志
├── README.md              # 项目说明
└── license.txt            # 许可证
```

## Claude Code 特定说明

### 文件引用规范

在 Claude Code 中引用文件时，使用 markdown 链接语法：
- 文件：`[filename.md](路径/filename.md)`
- 特定行：`[filename.md:42](路径/filename.md#L42)`
- 行范围：`[filename.md:42-51](路径/filename.md#L42-L51)`
- 目录：`[目录名/](路径/目录名/)`

### 任务管理

- 使用 TodoWrite 工具跟踪复杂任务的进度
- 完成任务后及时标记为 completed
- 拆分大任务为可管理的小步骤

### 代码变更规范

- 修改代码前先使用 Read 工具阅读文件
- 优先使用 Edit 工具进行精确修改
- 避免不必要的格式化或重构

### LaTeX 标题换行控制

对于需要精确控制换行长度的标题（如 NSFC 申请书的括号提示语）：

**推荐方案：使用 `\linebreak{}`**

```latex
% 示例：控制长标题的换行位置
\subsection{2. 工作条件（包括已具备的实验条件，尚缺少的实验条件和拟\linebreak{}解决的途径，包括利用国家实验室...）}
```

| 方法 | 优势 | 适用场景 |
|------|------|----------|
| `\linebreak{}` | 建议换行，保留 LaTeX 微调空间 | **推荐**：标题断行控制 |
| `\\` | 强制换行，不允许调整 | 仅用于必须强制换行的场景 |

**使用原则：**
- 优先使用 `\linebreak{}` 而非 `\\`，以保持排版灵活性
- 在需要断行的字符后添加 `\linebreak{}`
- 避免使用 `\tolerance` 等全局参数调整，改用 `\linebreak{}` 精确控制

## 变更边界

- 仅修改与当前任务直接相关的文件
- 不主动添加用户未要求的功能
- 保持现有代码风格和结构

## 变更记录规范

**核心原则**：项目中的任何更新都必须在根级 [CHANGELOG.md](CHANGELOG.md) 中记录，避免在分散的文档中维护重复的版本历史。

### 适用范围

所有可能产生版本历史的文档：
- **计划文档**（`plans/*.md`）：不记录版本更新历史，仅在末尾注明"变更历史记录在 CHANGELOG.md"
- **Skill 文档**（`skills/*/*/SKILL.md`）：不记录版本更新历史，版本号与 CHANGELOG.md 同步
- **项目指令**（`CLAUDE.md`、`AGENTS.md`）：不记录版本更新历史
- **配置文件**（`skills/*/*/config.yaml`）：版本号与 CHANGELOG.md 同步

### 记录流程

当修改任何项目文件时：
1. **更新 CHANGELOG.md**（必需）：记录变更内容、版本号、日期
2. **更新相关文件版本号**（如适用）：与 CHANGELOG.md 保持一致
3. **不在其他文档中记录变更历史**（避免重复和维护负担）

### 记录格式

```markdown
## [版本号] - YYYY-MM-DD

### Added（新增）
- 新增了 XXX 功能/章节：用途是 YYY

### Changed（变更）
- 修改了 XXX 章节：原因是 YYY，具体变更内容是 ZZZ

### Fixed（修复）
- 修复了 XXX 问题：表现是 YYY，修复方式是 ZZZ
```

---

## 有机更新原则

当需要更新本文档时：

### 1. 理解意图

首先理解用户需求背后的意图和在工作流中的本质作用

### 2. 定位生态位

每条规则/要求都应找到其在整个文档结构中的"生态位"——它与其他内容的关系、它服务的目标、它影响的其他部分

### 3. 协调生长

更新一个部分时，检查并同步更新相关部分：
- 更新工作流步骤时，同步更新示例和验证清单
- 更新输出规范时，同步更新引用该规范的其他章节
- 更新术语定义时，全局统一替换

### 4. 保持呼吸感

文档应该像生物体一样有"呼吸感"——章节之间有逻辑流动，而非割裂的清单

### 5. 定期修剪整合

当某个章节变得过于臃肿时，主动重构

---

**提示**：修改本文档后，请同步更新 `CHANGELOG.md` 记录变更历史。

