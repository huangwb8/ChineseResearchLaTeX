# 核心功能模块

本目录包含 `transfer-old-latex-to-new` 技能的三大核心功能模块。

## 📊 WordCountAdapter - 字数自动适配器

自动适配旧版本内容到新版本字数要求。

### 功能特点

- **版本支持**：2024→2025、2025→2026 的字数要求映射
- **智能适配**：自动扩展或精简内容到目标字数范围
- **AI 集成**：通过 `AIIntegration` 统一入口（未接入真实 AI 时自动回退）
- **中文字数统计**：准确统计中文字符，排除 LaTeX 命令

### 使用示例

```python
from core.ai_integration import AIIntegration
from core.word_count_adapter import WordCountAdapter

adapter = WordCountAdapter(config, ".")
ai = AIIntegration(enable_ai=False)  # 默认优雅降级（不依赖外部 AI 客户端）

# 获取字数报告
report = adapter.generate_word_count_report(content, "立项依据", "2025_to_2026")
print(f"当前字数: {report['current_count']}")
print(f"新版本要求: {report['new_requirement']}")
print(f"是否需要适配: {report['needs_adaptation']}")

# 执行适配（async，版本范围 → 以中位数为目标）
result = await adapter.adapt_content_by_version_pair(content, "立项依据", "2025_to_2026", ai_integration=ai)
print(result["status"])

# 或：直接指定目标字数
target = 2200
result2 = await adapter.adapt_content(content, "立项依据", target, ai_integration=ai)
print(result2["action"])
```

### 版本字数要求

| 章节 | 2024→2025 | 2025→2026 |
|------|-----------|-----------|
| 立项依据 | 1500-2000 | 2000-2500 |
| 研究内容 | 800-1000 | 1000-1200 |
| 研究目标 | 500-800 | 600-900 |
| 研究方案 | 1000-1500 | 1200-1500 |
| 研究基础 | 1000-1500 | 1500-2000 |

---

## 🔒 ReferenceGuardian - 引用强制守护者

保护 LaTeX 引用不被 AI 破坏。

### 功能特点

- **全面保护**：支持 `\ref{}`、`\cite{}`、`\includegraphics{}` 等 8 种引用类型
- **占位符机制**：AI 处理前替换为唯一占位符，处理后恢复原始引用
- **完整性验证**：自动检查引用是否丢失或被破坏
- **修复功能**：尝试修复被部分破坏的引用

### 使用示例

```python
from core.reference_guardian import ReferenceGuardian

guardian = ReferenceGuardian({"reference_protection": {"enabled": True}})

content = r"参见\ref{fig1}和\cite{author2024}的研究。"

# 第一步：保护引用
protected, ref_map = guardian.protect_references(content)
# protected: "参见__REF_REF_xxx__和__REF_CITE_xxx__的研究。"
# ref_map: {"__REF_REF_xxx__": r"\ref{fig1}", ...}

# 第二步：AI 处理 protected 内容
processed_by_ai = await ai_process(protected)

# 第三步：恢复引用
restored = guardian.restore_references(processed_by_ai, ref_map)

# 第四步：验证引用完整性
original_refs = guardian._extract_all_references(content)
validation = guardian.validate_references(restored, original_refs)
if not validation["valid"]:
    print(f"缺失引用: {validation['missing']}")
```

### 支持的引用类型

| 类型 | 命令 | 示例 |
|------|------|------|
| 交叉引用 | `\ref{}` | `\ref{fig:results}` |
| 文献引用 | `\cite{}` | `\cite{author2024}` |
| 文献引用 | `\citep{}` | `\citep{author2023}` |
| 文献引用 | `\citet{}` | `\citet{author2023}` |
| 公式引用 | `\eqref{}` | `\eqref{eq:method}` |
| 标签定义 | `\label{}` | `\label{sec:intro}` |
| 图片插入 | `\includegraphics{}` | `\includegraphics{fig.pdf}` |
| 代码引用 | `\lstinputlisting{}` | `\lstinputlisting{code.py}` |

---

## ✨ ContentOptimizer - AI 内容智能优化器

自动识别并优化内容质量问题。

### 功能特点

- **AI 分析**：智能识别冗余、逻辑、证据、清晰度、结构等问题
- **类型化优化**：针对不同问题类型使用专门的优化策略
- **引用保护**：优化过程自动保护 LaTeX 引用
- **启发式回退**：AI 调用失败时使用规则引擎

### 使用示例

```python
from core.content_optimizer import ContentOptimizer

optimizer = ContentOptimizer(config, ".")

# 生成优化报告（不执行优化）
report = optimizer.generate_optimization_report(content, "立项依据")
print(f"发现问题: {report['total_issues']} 个")
for issue in report['issues']:
    print(f"- [{issue['type']}] {issue['description']}")

# 执行优化（async）
goals = {
    "remove_redundancy": True,
    "improve_logic": True,
    "add_evidence": False
}

result = await optimizer.optimize_content(content, "立项依据", goals)
print(f"改进评分: {result['improvement_score']}")
print(f"引用保护: {result['reference_validation']['valid']}")

# 查看优化日志
for log in result['optimization_log']:
    print(f"- {log['action']}: {log['description']}")
```

### 优化类型

| 类型 | 说明 | 示例问题 |
|------|------|----------|
| `redundancy` | 删除冗余表述 | 词语重复、语义重复 |
| `logic` | 改进逻辑连贯性 | 段落间缺乏过渡 |
| `evidence` | 补充证据支持 | 缺乏数据/案例支撑 |
| `clarity` | 提高表述清晰度 | 复杂句式、模糊表述 |
| `structure` | 重组段落结构 | 段落顺序不合理 |

---

## 🔧 集成方式

### 完整工作流

```python
import asyncio
from core.ai_integration import AIIntegration
from core.word_count_adapter import WordCountAdapter
from core.reference_guardian import ReferenceGuardian
from core.content_optimizer import ContentOptimizer

async def migrate_section(content: str, section_title: str) -> str:
    """迁移单个章节到新版本"""

    ai = AIIntegration(enable_ai=False)

    # 1. 字数适配
    adapter = WordCountAdapter(config, ".")
    adapt_result = await adapter.adapt_content(content, section_title, target_word_count=2000, ai_integration=ai)
    adapted_content = adapt_result.get("adapted_content", content)

    # 2. 内容优化
    optimizer = ContentOptimizer(config, ".")
    goals = {"remove_redundancy": True, "improve_logic": True}
    opt_result = await optimizer.optimize_content(adapted_content, section_title, goals, ai_integration=ai)

    # 3. 验证引用完整性
    if not opt_result['reference_validation']['valid']:
        print("⚠️ 引用可能被破坏，请检查")

    return opt_result['optimized_content']

# 使用
new_content = asyncio.run(migrate_section(old_content, "立项依据"))
```

---

## ⚙️ 配置选项

### config.yaml

```yaml
word_count_adaptation:
  enabled: true
  auto_expand: true        # 自动扩展字数不足的内容
  auto_compress: true      # 自动精简字数过多的内容
  target_tolerance: 50     # 目标字数容差（字）

reference_protection:
  enabled: true
  validation_mode: "strict"  # strict | loose
  auto_repair: true         # 自动尝试修复被破坏的引用
  log_violations: true      # 记录引用违规

content_optimization:
  enabled: true
  auto_apply: true
  min_improvement_threshold: 0.1  # 最低改进阈值
  optimization_types:
    - redundancy
    - logic
    - evidence
    - clarity
    - structure
  preserve_references: true
  max_optimization_passes: 3
```

---

## 🧪 测试

```bash
# 运行演示
python demo_core_features.py

# 运行测试
python run_tests.py
```

---

## 📝 注意事项

### AI 集成

- 所有 AI 调用统一通过 `scripts/core/ai_integration.py` 的 `AIIntegration` 入口
- 未接入真实 AI responder 时，自动回退到启发式/不改写策略（保证流程可用）

### Async API

- `WordCountAdapter.adapt_content()` 是 async 方法
- `WordCountAdapter.adapt_content_by_version_pair()` 是 async 方法（兼容旧接口）
- `ContentOptimizer.optimize_content()` 是 async 方法
- `ReferenceGuardian` 所有方法都是同步的

### 性能考虑

- 字数统计使用正则表达式，对长文本可能有性能影响
- AI 调用有 `max_tokens` 限制，超长内容会被截断
- 建议对大文档分章节处理
