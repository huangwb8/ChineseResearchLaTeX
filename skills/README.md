# Skills - 项目专用技能

本目录存放本项目专用的 skill，与 `/Users/bensz/Nutstore Files/PythonCloud/Agents/pipelines/skills` 中开发的 skill 遵循相同的开发规范。

## Skill 结构规范

每个 skill 应包含以下文件：

```
your-skill/
├── SKILL.md          # 必需：技能主文档
├── config.yaml       # 必需：技能配置文件
├── README.md         # 可选：技能说明文档
└── scripts/          # 可选：脚本文件
```

## SKILL.md 模板

```markdown
# Your Skill Name（你的技能名称）

## 目标

简述技能的功能和用途。

## 触发条件

用户在以下场景触发本技能：
- 场景 1
- 场景 2

## 输入参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| param1 | string | 是 | 参数说明 |
| param2 | boolean | 否 | 参数说明 |

## 执行流程

1. 步骤 1
2. 步骤 2
3. 步骤 3

## 输出规范

描述输出格式和内容。

## 验证清单

- [ ] 检查项 1
- [ ] 检查项 2
```

## config.yaml 模板

```yaml
# 技能配置文件

skill_info:
  name: your-skill
  version: 1.0.0
  description: 技能描述

# 参数配置
parameters:
  param1:
    type: string
    required: true
    default: null
  param2:
    type: boolean
    required: false
    default: false

# 验证规则
validation:
  max_attempts: 3
  timeout: 30
```

## 本项目专用技能示例

### latex-compiler
自动编译 LaTeX 项目，处理依赖关系，清理辅助文件。

### nsfc-template-helper
国自然科学基金模板辅助工具，帮助填写标准章节。

### bibliography-manager
参考文献管理工具，验证 BibTeX 格式，生成引用列表。

## 开发新技能

1. 创建技能目录：`mkdir skills/your-skill`
2. 创建 `SKILL.md` 和 `config.yaml`
3. 在本 README.md 中注册新技能
4. 遵循 skill 开发规范（参考 `skill开发技巧.md`）

## 注意事项

- 技能名称使用小写字母和连字符
- 配置文件使用 YAML 格式
- 保持技能专注单一职责
- 提供清晰的触发条件说明
