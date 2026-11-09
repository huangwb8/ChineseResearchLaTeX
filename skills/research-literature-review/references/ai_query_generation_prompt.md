# AI 多查询生成 Prompt 模板

> 检索前读取。让 AI 基于主题生成查询变体，并在阶段 1 前按公开契约保存为 JSON；数量边界读取 `config.yaml:query_input`，默认 5–25 条。

## Prompt

```text
你是学术文献检索专家。请根据以下主题生成多组英文查询，用于 OpenAlex、PubMed、IEEE Xplore 等数据库。

主题：{topic}
领域：{domain}
时间范围：{time_range}
目标参考文献数：{target_refs}

生成原则：
1. 覆盖同义词与术语变体
2. 适度扩展邻近概念
3. 根据需要加入 review / validation / cohort 等限定词
4. 如主题涉及具体技术，补充架构名或学习策略变体
5. 有效查询数量遵守当前 query_input.min_queries/max_queries（默认 5–25 条）

输出 JSON：
{
  "queries": [
    {
      "query": "...",
      "rationale": "核心查询/同义词变体/方法变体/限定词变体/时间切片"
    }
  ]
}
```

## 自检

- 查询之间要有明确差异
- 尽量使用英文标准术语
- 避免晦涩到几乎没有结果的组合
- 保存到 runner 的 `--query-file` 参数所指路径，或当前 run 的 `input/queries.json`；不要猜测其他 run 或内部文件名
- 空查询剔除后必须满足当前配置数量边界（默认 5–25 条）；生成失败、文件冲突或 schema 无效时先修复输入，再启动检索
- 只有调用方显式授权 `--allow-single-query-fallback` 时才允许单查询后备，并记录 `--fallback-reason`
