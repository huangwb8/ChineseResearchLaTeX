# 示例库

目的：提供可对照的“结构骨架 + 语气”参考。示例为演示用途，引用需按你的课题替换并核验。

每个示例可选配套一个 `*.metadata.yaml`，用于示例推荐（`scripts/run.py examples` / `coach --topic ...`）的关键词匹配与分类。

目录：
- `medical/`：医学/临床场景示例
- `engineering/`：工程/算法场景示例
- `cs/`：计算机/信息方向示例
- `materials/`：材料/化学方向示例
- `chemistry/`：化学方向示例
- `biology/`：生物学方向示例
- `math/`：数学/优化方向示例

## metadata.yaml 约定（用于示例推荐）

建议字段：
- `category`：示例类别（与目录名一致即可）
- `keywords`：关键词列表（用于匹配）
- `description`：一句话描述（用于输出展示）
- `difficulty`：starter|intermediate|advanced（可选）
- `word_count`：示例字数（可选）
- `structure_version`：结构版本标识（可选，例如 nsfc2026）
