# research-literature-interpretation

面向单篇论文的导师式深度解读技能。它提供证据与批判性判断原则，由 AI 按论文类型、读者目标和材料范围自主组织问题、机制、论证、证据边界和后续研究。

成稿默认面向移动端：短段落、克制而有职责的加粗与引用块，并用“直觉—技术—核查”渐进披露。最终只有一套正文；入门读者可以先抓主线，硬核读者可以继续下钻到公式、协议和来源锚点。

输入可以是本地 PDF/HTML、arXiv/DOI/出版社链接或正文片段。默认输出 Markdown；项目论文库中的条目写入与目录同名的 `docs/papers/<friendly-id>/<friendly-id>.md`（`<首位作者全名>-<年份>-<工作关键词>`），原始材料保持不变。

该技能不要求固定章节、表格或叙事顺序；建议先取证、建模、压力测试，再按需要表达。新笔记必须带证据 frontmatter 契约（稳定来源、证据深度、读取范围、问题/方法/结果/限制及支持或反驳关系）；`python3 scripts/validate_notes.py --style <note>` 可检查机械格式与移动端样式上限，精确阈值以 `config.yaml` 为准，但不能替代科学判断。旧笔记可用 `--allow-legacy` 只读检查，不能认证新运行。论文发现和去重请使用 `research-literature-radar`。

详细执行契约见 [`SKILL.md`](SKILL.md)；版本与可调阈值分别以 [`config.yaml`](config.yaml) 为准。
