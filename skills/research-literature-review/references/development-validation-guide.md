# 开发验证指南

> 面向维护者。核心目标是验证“检索策略能否覆盖应被找到的代表性文献”。

## 文稿与交付回归

除检索覆盖外，还需验证写作资料、格式和交付。仓库维护入口：

Skill 自带的回归测试统一位于 `scripts/test_*.py`，原 `qa/` 和 `tests/` 目录已合并到 `scripts/`。单独运行这些测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s skills/research-literature-review/scripts -p 'test_*.py'
```

联合运行仓库级回归：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_review_quality_regression.py skills/research-literature-review/scripts tests/research-literature-review/test_relevance_selection.py -q --basetemp <本轮任务工作区>/test-output -o cache_dir=<本轮任务工作区>/pytest-cache
```

真实导出用例需要 XeLaTeX、BibTeX 和 Pandoc；缺依赖时跳过并明确报告，不能计为真实导出通过。测试覆盖缺文件与越界资源、报告误判、失败传播、完整摘要与提取字段、模板覆盖保护、标题层级和完整包独立重编译。Word 样式来自随包发布的 `review-reference.docx`，采用黑色层级标题、A4 页边距、Times New Roman 与宋体字体声明；导出器可通过 `fc-list` 为默认宋体选择已安装的同类字体，接收端缺字体仍会替换，跨平台须渲染核验。

另用实际页面渲染检查标题、中文、表格、图片和参考文献。源文件统计或编译退出码不能代替目视检查。历史产物仅作只读参考，不因排版整齐就充当内容金标准；对关键数字与研究身份应回到证据来源。

比较新旧写作指南时固定输入证据、人群和篇幅。短篇合成测试能识别明显事实或推理错误，不能证明真实长篇综述的普遍提升。不要把所有检查都通过的弱测试包装成质量提升百分比。

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
