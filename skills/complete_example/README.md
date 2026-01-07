# complete_example Skill - AI 增强版 LaTeX 示例智能生成器

## 简介

**complete_example** 是一个充分发挥 AI 优势的 LaTeX 示例智能生成器，实现 AI 与硬编码的有机融合。

**核心设计理念**：AI 做"语义理解"，硬编码做"结构保护"

## 功能特性

- 🧠 **AI 语义理解**：理解章节主题，智能判断需要什么类型的资源
- 🧠 **AI 智能推理**：推断资源与章节的相关性，并给出理由
- 🧠 **AI 连贯生成**：生成自然流畅的叙述性文本
- 🆕 **用户提示机制**：支持自定义叙事提示，指导 AI 生成特定风格的内容
- 🔧 **格式安全保护**：硬编码严格保护格式设置，哈希验证防篡改
- 🤝 **AI + 硬编码协作**：AI 提供智能 → 硬编码保障安全 → AI 优化质量

## 安装依赖

```bash
# Python 依赖
pip install anthropic openai pillow pyyaml jinja2

# LaTeX 依赖
# 确保系统已安装 xelatex
```

## 快速开始

### 1. 基本使用（AI 自动推断）

```python
from core.skill_controller import CompleteExampleSkill
import yaml

# 加载配置
with open("config.yaml", 'r') as f:
    config = yaml.safe_load(f)

# 创建 skill 实例
skill = CompleteExampleSkill(config)

# 执行
result = skill.execute(
    project_name="NSFC_Young",
    options={
        "content_density": "moderate",
        "output_mode": "preview",
        "target_files": ["extraTex/1.2.内容目标问题.tex"]
    }
)

# 查看结果
print(f"执行状态：{result['final_result']}")
print(f"运行目录：{result['run_dir']}")
```

### 2. 使用用户提示

```python
result = skill.execute(
    project_name="NSFC_Young",
    options={
        "narrative_hint": "生成一个关于深度学习在医疗影像分析中应用的示例，重点关注 CNN 架构和数据增强策略"
    }
)
```

### 3. 应用模式（直接修改文件）

```python
result = skill.execute(
    project_name="NSFC_Young",
    options={
        "output_mode": "apply",  # 注意：这会直接修改文件！
        "narrative_hint": "生成示例内容"
    }
)
```

## 参数说明

### content_density（内容密度）

| 值 | 资源数 | 字数 | 适用场景 |
|---|--------|------|----------|
| `minimal` | 2 | 200 | 快速填充，次要章节 |
| `moderate` | 4 | 300 | 平衡选择，大多数章节 |
| `comprehensive` | 6 | 500 | 详细示例，核心章节 |

### output_mode（输出模式）

| 值 | 说明 | 安全性 |
|---|------|--------|
| `preview` | 只显示预览，不修改文件 | ✅ 最安全 |
| `apply` | 直接修改文件（有备份） | ⚠️ 会修改文件 |
| `report` | 生成详细报告文件 | ✅ 安全 |

### narrative_hint（叙事提示）

支持用户自定义叙事提示，AI 根据提示编造合理的示例内容：

**示例场景**：
- 🏥 **医疗影像**：深度学习在医疗影像分析中的应用
- 🔬 **材料科学**：新型纳米材料合成与表征
- 🧪 **临床试验**：多中心临床试验设计
- 🤖 **传统 ML**：支持向量机分类方法

## 运行目录结构

所有运行输出都保存在 `runs/<run_id>/` 中：

```
runs/<run_id>/
├── backups/           # 备份文件
├── logs/              # 日志文件
│   ├── execution.log
│   ├── format_check.log
│   └── compile.log
├── analysis/          # AI 分析结果
│   └── section_themes.json
├── output/            # 生成内容
│   ├── preview/       # 预览模式输出
│   ├── applied/       # 应用模式输出
│   └── report/        # 报告模式输出
└── metadata.json      # 运行元数据
```

## 配置文件

配置文件 `config.yaml` 包含：

- LLM 配置（provider、model、temperature 等）
- 运行管理配置（runs_root、retention、backup 等）
- 资源扫描配置
- 内容生成配置
- 格式保护配置
- AI 提示词模板
- 质量评估标准

## 安全机制

### 格式保护

- **受保护的文件**：`extraTex/@config.tex`、`main.tex` 等
- **受保护的命令**：`\setlength`、`\geometry`、`\definecolor` 等
- **哈希验证**：计算关键格式文件的哈希值，防止篡改
- **自动备份**：修改前自动备份到 `runs/<run_id>/backups/`
- **自动回滚**：格式保护失败或编译失败时自动回滚

### 编译验证

- 修改文件后自动执行 `xelatex` 编译
- 编译失败则自动回滚
- 编译日志保存在 `runs/<run_id>/logs/compile.log`

## 测试

```bash
# 运行测试
cd skills/complete_example
python -m pytest tests/

# 运行基本示例
python examples/basic_usage.py

# 运行高级示例
python examples/advanced_usage.py
```

## 最佳实践

1. **优先使用预览模式**：首次使用时，建议使用 `output_mode: preview`
2. **充分利用用户提示**：通过 `narrative_hint` 指定研究主题
3. **选择合适的内容密度**：根据章节重要性选择密度
4. **定期清理运行记录**：使用 `auto_cleanup` 配置自动清理过期记录

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

## 故障排除

### 问题 1：格式被意外修改

**解决方案**：
1. 检查 `runs/<run_id>/logs/format_check.log`
2. 查看备份文件 `runs/<run_id>/backups/`
3. 手动恢复或调整提示后重试

### 问题 2：编译失败

**解决方案**：
1. 检查 `runs/<run_id>/logs/compile.log`
2. 查看具体错误信息
3. 调整 AI 温度参数或修改提示

### 问题 3：生成质量不理想

**解决方案**：
1. 使用更明确的 `narrative_hint`
2. 降低 `temperature` 参数
3. 使用更强大的 LLM 模型

## 更新日志

版本变更历史记录在项目根目录的 [CHANGELOG.md](../../CHANGELOG.md) 中。

## 许可证

与主项目保持一致。

---

**详细设计文档**：[plans/v202601071300.md](../../plans/v202601071300.md)
