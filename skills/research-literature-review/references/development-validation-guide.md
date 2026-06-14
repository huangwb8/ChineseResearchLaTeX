# 开发验证指南

> 面向维护者。核心目标是验证“检索策略能否覆盖应被找到的代表性文献”。

## Gold Set 方法

- `Gold Set` = 已知必须被检索到的代表性文献集
- 构建原则：
  - 代表性
  - 时间 cutoff 一致
  - 权威性

## 验证重点

- 优先看 Recall，而不是 Precision
- 先问三件事：
  1. 覆盖率是否达标
  2. 缺失是否集中在某个子主题/年份/venue
  3. 缺口是否能映射到一个确定的扩容动作

## 最小流程

1. 构建或读取 Gold Set
2. 用真实检索结果对比覆盖率
3. 记录缺失 DOI 或论文
4. 决定是扩 Query、补切片、做 citation chase，还是补 metadata

## 常见症状与动作

| 症状 | 常见原因 | 动作 |
|---|---|---|
| Recall < 80% | 查询过窄、同义词不足 | 扩 Query Set |
| Recall 80%-95% | 小众术语、版本替换、venue 覆盖差 | 做 citation chase / 版本替换检查 |
| 缺失集中在少量 DOI | 解析或 metadata 问题 | 定点补齐 |

## 相关入口

- `references/ai_query_generation_prompt.md`
- `references/mcp-literature-search-engines.md`
- `scripts/openalex_citation_chase.py`
