# 开发验证指南（Development Validation Guide）

> **目的**：本指南解释 systematic-literature-review 技能的开发验证方法论，帮助开发者理解如何验证检索策略的有效性。

---

## 一、验证方法论：Gold Set 方法

### 什么是 Gold Set？

**Gold Set（黄金文献集）**是**已知的、必须被检索到的代表性文献集合**，用于验证检索策略的覆盖率。

**构建原则**：
1. **代表性**：Gold Set 应覆盖研究主题的主要子领域
2. **时间一致性**：只包含在检索时"理论上可获得"的文献（cutoff 原则）
3. **权威性**：优先选择高引用、Top 期刊/会议的文献

---

## 二、现有验证示例：张峰 CRISPR 论文（Cong et al., 2013）

### 背景

该验证示例使用**张峰实验室 2013 年 CRISPR-Cas9 论文**的参考文献作为 gold set：

- **原论文**：Cong, L. et al. (2013). Multiplex genome engineering using CRISPR/Cas systems. *Science*, 339(6121), 819-823.
- **DOI**：[10.1126/science.1231143](https://doi.org/10.1126/science.1231143)

### Gold Set 构建

在 `build_gold_feng_zhang_crispr_cong2013.py` 中，gold set 按**发表时间 cutoff**过滤：

```python
# cutoff 原则：只包含原论文发表前 6 个月的文献
CUTOFF_DATE = datetime(2013, 1, 1)  # 2013年1月（论文发表于2013年1月）
```

**原因**：确保验证的是"当时可获得的文献"，避免使用"未来文献"导致 unrealistic 的预期。

### Gold Set 规模

- **总参考文献数**：~30 篇
- **过滤后 Gold Set**：~20 篇（符合 cutoff 原则）

---

## 三、如何运行验证

### 步骤 1：生成 Gold Set

```bash
cd systematic-literature-review/scripts
python build_gold_feng_zhang_crispr_cong2013.py
```

输出：`gold_feng_zhang_crispr_cong2013.json`

### 步骤 2：运行验证脚本

```bash
python validate_feng_zhang_crispr_cong2013.py
```

输出示例：
```
验证结果：
  Gold Set 总数: 20
  找到文献数: 18
  覆盖率: 90.0%

缺失文献:
  - DOI:10.1016/j.cell.2012.05.025
  - DOI:10.1038/nbt.2195
```

### 步骤 3：查看缺口清单

```bash
python validate_feng_zhang_crispr_cong2013.py --show-missing
```

输出缺失的 DOI 和建议的扩展检索策略。

---

## 四、验证指标解读

> 数值口径请以 `config.yaml` 的 `quality_thresholds` / `evidence.*` 为准，如需调整统一改配置。

| 指标 | 目标阈值 | 说明 |
|------|----------|------|
| **Recall（召回率）** | ≥ 95% | Gold Set 中被找到的文献比例 |
| **Precision（精确率）** | 不强制 | 检索阶段优先召回，筛选阶段提升精确率 |
| **F1 Score** | ≥ 90% | Recall 和 Precision 的调和平均 |

### 为什么优先 Recall？

本 skill 的检索阶段遵循 **Recall-first**（筛选阶段再提升 precision），因此开发验证优先关注 **Recall（覆盖率）**。检索扩容与失败诊断细节统一在：
- `systematic-literature-review/references/mcp-literature-search.md`
- `systematic-literature-review/references/cross-domain-search-and-screening.md`

---

## 五、如何为自定义主题构建 Gold Set

### 方法 1：从权威综述获取

1. 找到目标领域的**高质量综述**（Nature Reviews/Annual Reviews 等）
2. 提取综述的**参考文献列表**
3. 按**时间 cutoff**过滤（只包含综述发表前 N 个月的文献）
4. 手动筛选出**代表性文献**（20-30 篇）

### 方法 2：从哨兵论文获取

1. 选择 3-5 篇**哨兵论文**（领域内的奠基性工作）
2. 使用 `openalex_citation_chase.py` 获取它们的**参考文献**
3. 去重并按**时间 cutoff**过滤
4. 手动筛选出**代表性文献**

### 方法 3：手动构建

1. 列出研究主题的**核心子领域**（3-6 个）
2. 每个子领域选择**2-5 篇代表性文献**
3. 确保覆盖**主要方法/应用/评估**
4. 记录每篇文献的**DOI 和选择理由**

---

## 六、验证失败时的优化策略

开发验证的优化建议只保留“可落地”的最小闭环（避免与检索 playbook 重复维护）：

| 症状 | 最常见原因 | 直接动作（脚本/文档） |
|------|-----------|------------------------|
| Recall 很低（<80%） | 查询过窄/同义词不足/切片缺失 | 扩展 Query Set 与切片：`references/mcp-literature-search.md`；必要时跑 `scripts/expand_keywords.py` |
| Recall 中等（80–95%） | 小众 venue/非标准术语/版本替换 | 做哨兵引文追踪与版本替换检查：`references/cross-domain-search-and-screening.md`；跑 `scripts/openalex_citation_chase.py` |
| 缺失集中在少数 DOI | 记录/解析问题或特定站点覆盖差 | 对缺失 DOI 做定点检索/解析与补元数据（优先让缺口清单可复现） |

---

## 七、验证脚本的扩展使用

### 使用真实检索产出验证

如果你已经通过 MCP 工具或其他方式获得了检索结果，可以验证覆盖率：

```bash
# 将检索结果的 DOI 保存到文件（每行一个）
cat your_dois.txt | grep "doi.org" > found_dois.txt

# 运行验证
python validate_feng_zhang_crispr_cong2013.py --found-dois found_dois.txt
```

### 使用自定义 Gold Set

1. 创建自定义 gold set JSON 文件：
   ```json
   {
     "name": "Your Topic Gold Set",
     "cutoff_date": "2023-01-01",
     "papers": [
       {"doi": "10.xxx/yyy", "title": "Paper 1"},
       {"doi": "10.xxx/zzz", "title": "Paper 2"}
     ]
   }
   ```

2. 修改 `validate_search_strategy.py` 中的 gold set 路径

3. 运行验证

---

## 八、验证报告的解读

报告解读只看三件事：
1. 总体覆盖率（Recall）是否达标
2. 缺失是否“结构性集中”（集中在年份段/子主题/venue/版本类型）
3. 缺口是否能映射到一个确定的扩容动作（Query Set/切片/哨兵追踪/版本替换）

---

## 九、常见问题

### Q1: 为什么不使用完整参考文献列表作为 Gold Set？

**A**: 原论文的参考文献可能包含：
- **综述类文章**（非原始研究）
- **非核心文献**（边缘相关）
- **未来文献**（发表后引用的工作）

使用 cutoff 原则过滤后，可以确保 Gold Set 只包含"当时可获得的、代表性的核心文献"。

### Q2: 验证脚本可以用于其他领域吗？

**A**: 可以。步骤：
1. 选择该领域的**权威论文**（如高引用综述）
2. 提取其参考文献并应用 cutoff 原则
3. 修改验证脚本中的 gold set 路径
4. 运行验证

### Q3: 如果 Gold Set 本身有误怎么办？

**A**: Gold Set 应定期审查：
1. 检查是否有**错误引用**（DOI 无效）
2. 检查是否有**非核心文献**（应移除）
3. 检查 cutoff 原则是否**一致**

---

## 十、总结

**验证流程**：
1. 构建 Gold Set（代表性 + cutoff 原则）
2. 运行验证脚本
3. 检查覆盖率
4. 如覆盖率 < 95%，优化检索策略
5. 重新验证直至满足目标

**核心原则**：
- **Recall 优先**：检索阶段最大化召回率
- **可复现性**：所有验证步骤可重复执行
- **诚实报告**：如实记录覆盖率和缺口

---

**文档版本**：1.0
**最后更新**：2025-01-15
**维护者**：systematic-literature-review 技能维护团队
