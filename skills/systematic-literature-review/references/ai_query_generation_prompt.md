# AI 多查询生成 Prompt 模板

> **用途**：让 AI 根据研究主题特性自主生成查询变体（通常 5-15 组），用于多源文献检索。

---

## Prompt 模板

```markdown
你是学术文献检索专家，精通多个领域（医学、计算机科学、工程、社会科学）的检索策略。请为以下研究主题生成查询变体，用于在 OpenAlex、PubMed、IEEE Xplore 等学术数据库中进行系统性检索。

**查询组数自主规划原则**：
- 根据主题复杂度、领域特性、术语标准化程度自主决定组数
- **标准领域**（术语标准化）：6-10 组
- **跨学科/新兴领域**：10-15 组
- **罕见病/小众研究**：可扩展到 15-20 组
- 避免过度冗余（>25 组）或覆盖不足（<5 组）

## 研究主题

**主题**: {topic}
**领域**: {domain}
**时间范围**: {time_range}
**目标参考文献数**: {target_refs}

---

## 查询生成原则

### 1. 同义词与术语变体

同一概念可能有多种表述方式，请生成涵盖这些变体的查询：

**示例**（主题：深度学习在乳腺超声结节良恶性鉴别中的应用）：
- breast ultrasound ↔ breast ultrasonography ↔ ultrasonography
- benign/malignant classification ↔ lesion differentiation ↔ cancer detection
- deep learning ↔ neural network ↔ CNN ↔ deep neural network

### 2. 邻近概念扩展

从核心主题向外扩展，包括：
- **更宽泛的概念**：如从 "CNN 分类" 扩展到 "深度学习分类"
- **更细分的概念**：如从 "深度学习" 细分到 "ResNet"、"Transformer"
- **相关领域**：如从 "乳腺超声" 关联到 "医学影像"、"计算机辅助诊断"

### 3. 限定词变体

添加/移除常见限定词，生成不同粒度的查询：
- **宽泛检索**：不加限定词
- **综述类**：添加 "review", "systematic review", "meta-analysis", "survey"
- **研究类型**：添加 "clinical trial", "cohort", "validation", "comparative study"

### 4. 方法论变体

如果主题涉及特定技术，生成该技术的不同表述：
- **架构名称**：CNN, ResNet, VGG, U-Net, Transformer, ViT
- **学习策略**：transfer learning, weakly-supervised, semi-supervised, data augmentation
- **应用方式**：classification, detection, segmentation, diagnosis

### 5. 年份切片（如果指定时间范围）

将时间范围分段，确保覆盖早期经典文献和最新研究：
- **近期焦点**：最近 2-3 年
- **中期覆盖**：中间年份段
- **早期经典**：早期重要文献

---

## 输出格式

请以 **JSON 数组** 格式输出查询列表：

```json
{
  "queries": [
    {
      "query": "<查询字符串，英文，适合 OpenAlex/PubMed 检索>",
      "rationale": "<简述生成此查询的理由，如：核心查询、同义词变体、限定词变体等>"
    },
    ...
  ]
}
```

---

## 输出质量要求

1. **数量**：根据领域特性灵活调整（详见"查询组数自主规划原则"）
2. **多样性**：查询之间应有明确差异，避免重复
3. **精准度**：平衡召回率（recall）和精确率（precision）
4. **领域适配**：
   - **临床医学**：优先使用 MeSH 术语、疾病标准名称
   - **计算机科学**：优先使用技术标准名称、架构名称
   - **工程**：优先使用行业标准术语
   - **社会科学**：优先使用理论名称、方法论术语

---

## 示例输出

**输入主题**：深度学习在乳腺超声结节良恶性鉴别中的应用

**输出**：
```json
{
  "queries": [
    {
      "query": "deep learning breast ultrasound benign malignant classification",
      "rationale": "核心查询：涵盖主题的核心要素"
    },
    {
      "query": "convolutional neural network breast lesion classification ultrasound",
      "rationale": "方法变体：用 CNN 替代 deep learning"
    },
    {
      "query": "computer-aided diagnosis breast ultrasound deep learning",
      "rationale": "邻近概念：CAD 系统相关"
    },
    {
      "query": "ResNet DenseNet breast ultrasonography cancer detection",
      "rationale": "细分方法：具体架构名称"
    },
    {
      "query": "\"breast ultrasound\" \"deep learning\" review systematic review",
      "rationale": "限定词变体：添加 review 限定词"
    },
    {
      "query": "transfer learning breast ultrasound classification",
      "rationale": "学习策略：迁移学习方向"
    },
    {
      "query": "medical imaging deep learning breast cancer diagnosis",
      "rationale": "宽泛概念：医学影像 broader context"
    },
    {
      "query": "weakly-supervised semi-supervised breast ultrasound lesion",
      "rationale": "学习策略：弱监督/半监督方向"
    }
  ]
}
```

---

## 注意事项

1. **查询语言**：统一使用英文（即使主题是中文，学术检索也应以英文为主）
2. **简洁性**：查询字符串应简洁，避免过多逻辑运算符（AND/OR/NOT）
3. **可执行性**：查询应能直接用于 OpenAlex API 的 `search` 参数
4. **避免空结果**：确保每个查询都有可能返回结果（避免过于晦涩的术语组合）

---

请开始生成查询。
```

---

## 使用流程

### 1. 在 Pipeline Runner 中调用

```python
def run_stage_1_search(self) -> bool:
    # 读取 Prompt 模板
    prompt_template = Path("references/ai_query_generation_prompt.md").read_text()

    # 填充参数
    prompt = prompt_template.format(
        topic=self.topic,
        domain=self.domain,
        time_range="未指定",  # 或从用户输入获取
        target_refs=f"{self.target_refs['min']}-{self.target_refs['max']}"
    )

    # AI 生成查询（由 Claude Code / Codex 环境执行）
    queries_json = ai_generate_queries(prompt)  # 返回 JSON 字符串

    # 解析查询
    queries = json.loads(queries_json)["queries"]

    # 并行检索
    for q in queries:
        search_openalex(q["query"], ...)
```

### 2. AI 生成查询的接口

由于技能运行在 Claude Code / Codex 环境中，"AI 生成查询"这一步实际上是由环境中的 AI 直接执行：

- **Claude Code**：AI 直接理解 Prompt 并输出 JSON
- **Codex**：AI 直接理解 Prompt 并输出 JSON

无需调用外部 LLM API。

### 3. 后备方案

如果 AI 生成失败，降级为单一查询：

```python
fallback_queries = [{"query": self.topic, "rationale": "降级方案：单一查询"}]
```

---

## 版本历史

- **v1.0** (2026-01-02): 初始版本，用于多查询检索策略优化
