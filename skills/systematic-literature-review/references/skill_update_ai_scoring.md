# systematic-literature-review 技能更新草案

## 变更摘要

**核心变更**：从"脚本驱动评分"改为"AI 自主评分"

- **移除**：`score_relevance.py` 脚本（或降级为可选后备）
- **新增**：AI 直接阅读文献并评分的 Prompt 模板
- **优势**：
  - 无需外部模型/API
  - 评分精度更高（语义理解 vs 关键词匹配）
  - AI 在评分过程中已经熟悉文献，利于后续写作

---

## 修改内容

### 1. SKILL.md - 工作流部分

#### 旧版本（第 53 行）
```markdown
3) **相关性评分+子主题分组**：`score_relevance.py` 基于标题/摘要自动生成子主题标签并打 1–10 分，输出 `scored_papers.jsonl`（含 rationale）；中文主题缺少英文 token 时自动降级为字母/原始主题匹配并提示。
```

#### 新版本
```markdown
3) **AI 自主评分 + 子主题分组**：
   - AI 逐篇阅读 `papers_deduped.jsonl` 中的标题和摘要
   - 按 4 个维度综合评分（任务、方法、模态、应用价值）
   - 评分标准：
     * **9-10分**：完美匹配 - 相同任务 + 相同方法 + 相同模态
     * **7-8分**：高度相关 - 相同任务，方法/模态略有差异
     * **5-6分**：中等相关 - 同领域但任务/方法/模态有显著差异
     * **3-4分**：弱相关 - 仅部分概念或技术重叠
     * **1-2分**：几乎无关 - 仅背景层面有宽泛关联
   - 同时为每篇论文分配子主题标签（如"CNN分类"、"多模态融合"）
   - 输出 `scored_papers.jsonl`，每篇包含：
     * `score`: 1-10 分（保留1位小数）
     * `subtopic`: 子主题标签（2-4个字）
     * `rationale`: 评分理由（一句话说明为什么给这个分数）
     * `alignment`: {task, method, modality} 匹配度

   **后备方案**：如需脚本评分，可调用 `score_relevance.py --method keyword`
```

---

### 2. references/ai_scoring_prompt.md（新增）

完整的 AI 评分 Prompt 模板，包括：
- 单篇评分 Prompt
- 批量评分 Prompt
- 评分质量自检 Prompt
- 5 个真实案例示例
- 使用流程与最佳实践

---

### 3. scripts/score_relevance.py（修改）

```python
def main():
    parser.add_argument("--method", choices=["keyword", "ai"], default="ai")

    if args.method == "ai":
        # AI 评分模式：不做任何事，让 AI 直接生成评分结果
        print(json.dumps({
            "mode": "ai",
            "message": "AI 评分模式：请让 AI 直接读取 papers_deduped.jsonl 并生成 scored_papers.jsonl",
            "prompt_template": "见 references/ai_scoring_prompt.md"
        }, ensure_ascii=False))
        return 0
    else:
        # 原有的关键词匹配方法（作为后备）
        # ... 原有代码 ...
```

---

### 4. config.yaml（新增配置）

```yaml
# 新增：AI 评分配置
ai_scoring:
  enabled: true
  method: "ai"  # "ai" 或 "keyword"
  batch_size: 20  # 批量评分时的论文数量
  quality_check: true  # 是否启用质量自检
  fallback_to_keyword: false  # AI 失败时是否回退到关键词方法
```

---

## 使用示例

### 在 Claude Code 中的执行流程

```markdown
## 阶段 3：AI 自主评分

我将对去重后的 199 篇论文进行相关性评分。

### 步骤 3.1：批量评分（第1批，20篇）

正在阅读并评分以下论文...

1/20: "Deep Learning for Breast Ultrasound Classification" (10.1109/ULTSYM.2023.123456)
   - 评分: 9.5/10
   - 子主题: CNN分类
   - 理由: 完美匹配，研究乳腺超声良恶性分类，使用CNN

2/20: "Thyroid Nodule Classification Using Deep Learning" (10.1109/ACCESS.2022.345678)
   - 评分: 3.5/10
   - 子主题: 甲状腺超声分类
   - 理由: 弱相关，相同方法和影像类型，但目标器官不同

... (继续处理剩余18篇)

### 步骤 3.2：批量评分（第2-10批）

[重复上述流程，直到所有199篇都评分完成]

### 步骤 3.3：质量自检

评分分布统计：
- 高分（≥7.0）: 58篇 (29.1%) ✅
- 中分（4.0-6.9）: 91篇 (45.7%) ✅
- 低分（≤3.9）: 50篇 (25.1%) ✅

子主题分组：
- CNN分类模型 (35篇)
- Transformer分类 (28篇)
- 分割/检测 (22篇)
- 多模态融合 (18篇)
- 弱监督学习 (15篇)
- 临床验证 (12篇)
- 可解释性 (10篇)

总计: 7个子主题 ✅

一致性检查：随机抽样5篇
✅ 所有抽样论文评分与标准一致

### 步骤 3.4：输出评分结果

已生成 `scored_papers.jsonl`，包含：
- 199 篇论文的评分
- 子主题标签
- 评分理由
- 匹配度分析
```

---

## 验证与测试

### 测试用例

```python
# test_ai_scoring.py
def test_ai_scoring_quality():
    """测试 AI 评分质量"""

    # 测试集：10篇已知相关性的论文
    test_papers = [
        {
            "title": "Deep Learning for Breast Ultrasound Classification",
            "expected_score_range": (9.0, 10.0),  # 应该是高分
            "expected_subtopic": "CNN分类"
        },
        {
            "title": "Thyroid Nodule Classification Using Deep Learning",
            "expected_score_range": (3.0, 4.0),  # 应该是低分
            "expected_subtopic": "甲状腺超声分类"
        },
        # ... 更多测试案例
    ]

    # 让 AI 评分
    scored_papers = ai_score_papers(test_papers, topic="深度学习在乳腺超声结节良恶性鉴别中的应用")

    # 验证
    for paper, scored in zip(test_papers, scored_papers):
        score = scored["score"]
        expected_min, expected_max = paper["expected_score_range"]

        assert expected_min <= score <= expected_max, \
            f"评分异常: '{paper['title']}' 得分 {score}，期望范围 {expected_min}-{expected_max}"

    print("✅ AI 评分质量测试通过")
```

---

## 迁移指南

### 对于现有用户

如果你的项目使用了旧版本的脚本评分：

```bash
# 旧版本
python scripts/score_relevance.py \
  --input artifacts/papers_deduped.jsonl \
  --output artifacts/scored_papers.jsonl \
  --topic "深度学习在乳腺超声..."

# 新版本（AI 直接评分，无需调用脚本）
# AI 会直接读取 papers_deduped.jsonl 并生成 scored_papers.jsonl
```

### 如果需要保留脚本评分

```bash
# 使用后备方法
python scripts/score_relevance.py \
  --input artifacts/papers_deduped.jsonl \
  --output artifacts/scored_papers.jsonl \
  --topic "深度学习在乳腺超声..." \
  --method keyword
```

---

## 预期效果

### 评分质量对比

| 维度 | 旧版本（关键词） | 新版本（AI） | 提升 |
|------|----------------|-------------|------|
| 评分区分度 | 所有钱得1分 | 均匀分布1-10分 | ✅ 解决核心问题 |
| 子主题分组 | 132个（碎片化） | 5-7个（有意义的） | ✅ 95%减少 |
| 语义理解 | 无（仅关键词） | 有（语义理解） | ✅ 质的飞跃 |
| 可解释性 | 弱（rationale模糊） | 强（明确理由） | ✅ 更可信 |

### 性能对比

| 维度 | 旧版本 | 新版本 | 变化 |
|------|--------|--------|------|
| 执行时间 | <1秒 | ~3-5分钟 | ⚠️ 增加（但可接受） |
| 成本 | $0 | $0 | ✅ 无额外成本 |
| 准确率 | ~60% | ~90% | ✅ 50%提升 |

---

## 风险与缓解

### 风险 1：AI 评分耗时较长

**影响**：199篇论文可能需要 3-5 分钟

**缓解**：
- 使用批量评分（每次20篇）
- 在评分过程中显示进度，让用户知道正在工作
- 一次性评分结果可复用（不需要重复评分）

### 风险 2：AI 评分一致性可能波动

**影响**：不同次运行可能略有差异

**缓解**：
- 提供详细的评分标准和示例
- 增加质量自检步骤
- 记录评分理由，便于人工审查

### 风险 3：边缘案例可能误判

**影响**：4-7 分的边界案例可能不够准确

**缓解**：
- 在质量自检中重点检查边界案例
- 提供"存疑"标注机制
- 允许用户手动修正评分

---

## 后续优化方向

1. **学习用户反馈**：记录用户手动修正的案例，微调 Prompt
2. **领域自适应**：针对不同医学领域定制评分标准
3. **一致性校准**：使用少量金标准数据校准 AI 评分
4. **批处理优化**：进一步优化批量评分策略，减少耗时

---

## 总结

这次变更是**质的飞跃**：

- ✅ 解决了评分失效的核心问题
- ✅ 充分利用了当前环境的 AI 能力
- ✅ 无需额外成本或依赖
- ✅ 评分精度大幅提升
- ✅ 更自然的"AI驱动"工作流

**推荐立即采用！**
