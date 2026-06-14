# 文献检索策略指南

本文档提供系统化文献检索的最佳实践。

## 检索式构建

### 基本原则

1. **PICOS 框架**：
   - P (Population): 研究人群/对象
   - I (Intervention): 干预措施
   - C (Comparison): 对照
   - O (Outcome): 结局指标
   - S (Study design): 研究设计

2. **布尔运算符**：
   - AND: 缩小范围，必须同时包含
   - OR: 扩大范围，包含任一
   - NOT: 排除特定词汇

3. **检索技巧**：
   - 使用引号进行精确匹配："machine learning"
   - 使用截词符: machine* (匹配 machines, machining 等)
   - 使用通配符: wom?n (匹配 woman, women)

### 示例检索式

```
("gene expression"[Title/Abstract] OR "transcriptomics"[Title/Abstract])
AND ("cancer"[Title/Abstract] OR "tumor"[Title/Abstract] OR "neoplasm"[Title/Abstract])
AND ("biomarker"[Title/Abstract] OR "prognosis"[Title/Abstract])
AND ("2019"[Date - Publication] : "3000"[Date - Publication])
```

## 数据源特性

### PubMed

**优势**：
- 生物医学领域最全面
- 免费开放
- 高质量索引

**检索语法**：
- 字段标识: [Title/Abstract], [MeSH Terms], [Author]
- 日期范围: `2019:3000`
- 过滤器: `humans[Filter]`, `english[Filter]`

**API**: https://www.ncbi.nlm.nih.gov/books/NBK25501/

### Semantic Scholar

**优势**：
- AI 驱动的相关性排序
- 引文网络分析
- 免费且无需注册

**API 特点**：
- RESTful API
- 支持批量查询
- 返回论文影响力指标

**文档**: https://api.semanticscholar.org/

### Google Scholar

**优势**：
- 覆盖面最广
- 包含跨学科文献
- 引文分析

**限制**：
- 无官方 API
- 检索结果数量估算不精确

### IEEE Xplore

**优势**：
- 工程技术领域权威
- 会议论文丰富
- 标准文献

**适用场景**：
- 信号处理
- 计算机科学
- 电子工程

### arXiv

**优势**：
- 最新预印本
- 免费获取
- 物理/计算机/数学

**注意**：
- 未经过同行评议
- 版本可能更新

## 相关性评估

### 评分标准 (1-10分)

| 分数 | 相关性 | 特征 |
|------|--------|------|
| 9-10 | 高度相关 | 直接针对研究问题，方法完全适用 |
| 7-8 | 相关 | 研究主题相关，方法可参考 |
| 5-6 | 部分相关 | 间接相关，有参考价值 |
| 1-4 | 不相关 | 主题不符或方法不适用 |

### 评估维度

1. **标题相关性** (30%)
   - 关键词匹配度
   - 研究领域一致性

2. **摘要相关性** (40%)
   - 研究问题匹配
   - 方法论适用性
   - 结果参考价值

3. **全文相关性** (30%)
   - Methods 章节详细度
   - 分析策略可复用性
   - 技术细节完整性

## 常见问题

**Q: 检索结果太多怎么办？**
A:
- 增加具体限制条件
- 使用更精确的关键词
- 限定研究设计类型

**Q: 检索结果太少怎么办？**
A:
- 减少限制条件
- 使用同义词扩展
- 扩大年份范围

**Q: 如何获取全文？**
A:
1. 检查期刊是否开放获取
2. 使用 Unpaywall 查找合法免费版本
3. 通过机构图书馆访问
4. 联系作者索取

## 参考文献

1. Bramer WM, et al. Systematic review of search strategies. PLoS One. 2018
2. Sampson M, et al. Optimizing search strategies. J Med Libr Assoc. 2009
3. McGillivray B, et al. Literature review search strategies. 2021
