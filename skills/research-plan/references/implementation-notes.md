# Implementation Notes

本文件面向维护者：记录脚本实现状态与“硬编码/AI 动态处理”的职责边界，避免在 `SKILL.md` 内堆叠实现细节（以满足社区推荐的 500 行以内约束）。

## 功能模块与脚本状态

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| 工作目录初始化 | implemented | `scripts/initialize.py` |
| JSON Schema 验证 | implemented | `scripts/validate.py` |
| BibTeX 生成 | implemented | `scripts/bibtex.py` |
| 工具函数 | implemented | `scripts/utils.py` |
| 文献检索 | planned | 计划新增 `scripts/literature_search.py` |
| PDF 下载 | planned | 计划新增 `scripts/pdf_download.py` |
| PDF 信息提取 | planned | 计划新增 `scripts/pdf_extract.py` |
| 分析框架综合 | planned | 计划新增 `scripts/framework_synthesis.py` |
| 计划生成 | planned | 计划新增 `scripts/plan_generator.py` |

说明：
- 版本号以 `config.yaml:skill_info.version` 为准（不在 `SKILL.md` 中重复记录）。
- 当 planned 脚本未实现时，可先由 AI 按 `SKILL.md` 流程“手动执行/半自动”完成对应步骤，并把可重复的确定性操作逐步沉淀到 `scripts/`。

## 硬编码 vs AI 动态处理（边界建议）

硬编码到 `scripts/`：
- 目录结构创建与文件命名规范
- JSON Schema 校验/字段完整性检查
- BibTeX 规范化与去重

AI 动态处理：
- 需求理解与主题提取
- 文献相关性评分（启发式 + 解释）
- Methods/Approach 语义提取与归纳
- 计划生成与多方案权衡（含不确定性声明）

