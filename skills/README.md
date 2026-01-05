# Skills 开发规范

本目录包含项目的 AI 技能（skills）定义文件，每个技能都是一个独立的功能模块。

## 目录结构

```
skills/
├── README.md                      # 本文件：Skills 开发规范
├── make_latex_model/             # LaTeX 模板优化技能
│   ├── SKILL.md                  # 技能定义文档
│   ├── config.yaml               # 技能配置文件
│   ├── scripts/                  # 技能专用脚本
│   │   ├── README.md            # 脚本使用说明
│   │   ├── validate.sh          # 自动化验证脚本
│   │   ├── benchmark.sh         # 性能基准测试
│   │   ├── extract_headings.py  # 标题提取工具
│   │   └── compare_headings.py  # 标题对比工具
│   └── tests/                   # 测试用例目录
└── transfer_old_latex_to_new/    # LaTeX 内容迁移技能
    └── SKILL.md
```

## 当前技能列表

- **make_latex_model**：基于最新 Word 模板，高保真优化 LaTeX 样式
  - 仅修改 `projects/{project}/extraTex/@config.tex`
  - 修改 `main.tex` 中的标题文本（不触碰正文内容）
  - 支持标题文字对齐和样式参数对齐

- **transfer_old_latex_to_new**：将旧标书内容迁移到新模板
  - 充当顶尖科学家的角色
  - AI 自主规划迁移策略
  - 严格遵守新模板格式

## Skill 文件规范

每个 skill 目录必须包含以下文件：

### 1. SKILL.md（必需）

技能定义文档，遵循以下规范：

**YAML 前置元数据**（必需）：
```markdown
---
name: skill_name
version: 1.0.0
description: 技能简短描述
category: normal | experimental
---
```

**核心章节**：
- 0.5) 深度参考：参考的文档和规范
- 0) 核心目标：技能要解决的问题
- 1) 触发条件：何时使用该技能
- 2) 输入参数：参数定义和默认值
- 3) 执行流程：详细的工作步骤
- 4) 输出规范：输出格式和内容要求
- 5) 核心原则：边界和约束
- 6) 验证清单：验收标准
- 7) 常见问题：FAQ
- 8) 变更日志：指向根级 CHANGELOG.md

**⚠️ 重要：版本历史维护规则**

- **SKILL.md 中不应记录详细的版本历史**
- 版本变更记录在根级 [CHANGELOG.md](../CHANGELOG.md) 中
- SKILL.md 仅保留当前版本号和简要的变更指引

```markdown
## 8) 变更日志

**技能版本历史**记录在根级 [CHANGELOG.md](../CHANGELOG.md) 中。

查看最新变更：
```bash
cat ../CHANGELOG.md | grep -A 10 "skill_name"
```

**当前版本**：v1.0.0
```

### 2. config.yaml（可选）

技能配置文件，定义：
- 技能元信息（名称、版本、描述）
- 输入参数schema
- 默认配置值
- 验证规则

### 3. scripts/（可选）

技能专用的自动化脚本：
- 验证脚本：`validate.sh`
- 测试脚本：`benchmark.sh`
- 工具脚本：Python/Bash 工具
- 文档：`scripts/README.md`

### 4. tests/（可选）

测试用例目录，结构：
```
tests/
├── Auto-Test-01/          # 测试会话
│   ├── config.yaml        # 测试配置
│   ├── run_test.sh        # 测试执行脚本
│   ├── workspace/         # 测试工作目录
│   └── FINAL_REPORT.md    # 测试报告
└── vYYYYMMDDHHMM/         # 时间戳命名的测试会话
```

## CHANGELOG 维护规范

### 根级 CHANGELOG.md

记录所有 skill 的版本变更：

```markdown
## [Unreleased]

### Added（新增）- Skills

- **skill_name v1.0.0** - 简短描述
  - 新增功能 XXX
  - 修复问题 YYY
  - 改进优化 ZZZ

### Changed（变更）- Skills

- **skill_name v1.x.x**
  - 修订功能 XXX
  - 优化性能 YYY

### Deprecated（废弃）- Skills

- **skill_name** - 废弃原因
```

### Skill 级变更记录

当修改 skill 时：

1. **更新根级 CHANGELOG.md**（必需）
2. **更新 SKILL.md 中的版本号**（必需）
3. **更新 config.yaml 中的版本号**（如存在）
4. **SKILL.md 中不记录详细变更历史**（避免重复）

### 版本号规则

遵循语义化版本（Semantic Versioning）：

- **主版本号（Major）**：不兼容的 API 变更
- **次版本号（Minor）**：向下兼容的功能新增
- **修订号（Patch）**：向下兼容的问题修复

示例：
- `1.0.0` → `1.0.1`：修复 bug
- `1.0.1` → `1.1.0`：新增功能
- `1.1.0` → `2.0.0`：重大架构变更

## 开发工作流

### 创建新 Skill

1. 创建 skill 目录：
   ```bash
   mkdir skills/your_skill
   cd skills/your_skill
   ```

2. 创建 SKILL.md：
   ```bash
   # 从现有 skill 参考格式
   cp ../make_latex_model/SKILL.md ./SKILL.md

   # 填写技能定义
   vim SKILL.md
   ```

3. 创建 config.yaml（如需要）：
   ```bash
   vim config.yaml
   ```

4. 更新根级 CHANGELOG.md：
   ```markdown
   ### Added（新增）- Skills
   - **your_skill v1.0.0** - 简短描述
   ```

### 更新现有 Skill

1. 修改 SKILL.md 和/或 config.yaml
2. 更新版本号
3. 在根级 CHANGELOG.md 中追加变更记录
4. 测试验证

### 测试 Skill

参考 [Prompts.md](../Prompts.md) 中的测试流程。

## 常见问题

### Q: 版本历史应该记在哪里？

A:
- **根级 CHANGELOG.md**：所有 skill 的版本变更（权威记录）
- **SKILL.md**：仅保留当前版本号和简要的变更指引
- **config.yaml**：当前版本号（与 SKILL.md 同步）

### Q: 为什么不把版本历史放在 SKILL.md 中？

A:
- 避免重复维护
- 便于跨 skill 查看变更历史
- 统一的项目级变更追踪
- 符合"单一事实来源"（Single Source of Truth）原则

### Q: 如何查看某个 skill 的完整变更历史？

A:
```bash
# 方法 1：查看根级 CHANGELOG
cat CHANGELOG.md | grep -A 20 "make_latex_model"

# 方法 2：使用 git log
git log --oneline --all -- skills/make_latex_model/

# 方法 3：查看 SKILL.md 中的版本号
grep "version:" skills/make_latex_model/SKILL.md
```

## 参考资源

- [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)
- [Semantic Versioning](https://semver.org/lang/zh-CN/)
- [项目 CLAUDE.md](../CLAUDE.md)
- [项目 Prompts.md](../Prompts.md)
