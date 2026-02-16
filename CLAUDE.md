# 中国科研常用 LaTeX 模板集 - Claude Code 项目指令

## 核心指令

@./AGENTS.md

## Claude Code 特定说明

### 文件引用规范

在 Claude Code 中引用文件时，使用 markdown 链接语法：
- **文件**：`[filename.md](路径/filename.md)`
- **特定行**：`[filename.md:42](路径/filename.md#L42)`
- **行范围**：`[filename.md:42-51](路径/filename.md#L42-L51)`
- **目录**：`[目录名/](路径/目录名/)`

### 任务管理

- 使用 TodoWrite 工具跟踪复杂任务的进度
- 完成任务后及时标记为 completed
- 拆分大任务为可管理的小步骤

### 代码变更规范

- 修改代码前先使用 Read 工具阅读文件
- 优先使用 Edit 工具进行精确修改
- 避免不必要的格式化或重构

### 与 AGENTS.md 的关系

- **AGENTS.md**：跨平台通用项目指令（Single Source of Truth）
- **CLAUDE.md**：通过 `@./AGENTS.md` 自动引用 + Claude Code 特定适配
- **维护流程**：
  1. 修改 AGENTS.md（唯一需要手动维护的项目指令文件）
  2. CLAUDE.md 会自动读取最新的 AGENTS.md 内容
  3. 无需运行任何同步命令
- **参考文档**：
  - AGENTS.md 标准：https://agents.md/
  - Claude Code @ 引用语法：https://github.com/anthropics/claude-code/issues/990

**提示**：修改 AGENTS.md 后，请立即在 `CHANGELOG.md` 中记录变更。这是项目管理的强制性要求，不是可选项。
