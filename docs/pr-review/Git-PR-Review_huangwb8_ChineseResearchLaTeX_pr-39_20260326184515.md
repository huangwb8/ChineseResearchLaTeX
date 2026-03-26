# Git PR Review: huangwb8/ChineseResearchLaTeX #39

PR 链接：<https://github.com/huangwb8/ChineseResearchLaTeX/pull/39>

## 结论摘要

- 建议：Request changes
- 风险等级：High
- 一句话判断：这个 PR 的目标合理，但当前同时存在可复现的 DOCX 导出正确性问题、官方二进制资料再分发依据不足、以及缺少 CI / 人工 review 的验证缺口，不建议直接 merge。

## 独立评审综合结果

- 独立评审次数：5
- runner 配置：`parallel-vibe + codex`
- `2 runners/thread` 说明：`git-pr-review` / `parallel-vibe` 当前原生只支持 `1 thread = 1 runner`，本次按最接近的官方支持方案执行了 5 个 `codex` 独立 thread
- recommendation 分布：`Request changes` x 5
- risk 分布：`High` x 4，`Medium` x 1
- 共识：先不要 merge，至少要先修复 `export_docx.py` 的两处真实输入问题，并处理官方 `.doc/.docx` 的合规依据
- 分歧：
  - 安全/供应链线程认为“恶意代码风险”本身偏低，因此给出 `Medium`
  - 其余线程把总体风险评为 `High`，原因集中在正确性、维护边界和合规
- 并行执行备注：5 个 thread 都完成了审查，但 `parallel-vibe` 下的 `codex` 实际落在只读沙箱，无法写出标准 `workspace/RESULT.md`；我已基于各 thread `runner.log` 里的最终审查正文做人工聚合，见 `.git-pr-review/.../parallel_review/independent_review_summary.md`

## PR 在解决什么问题

- 该 PR 试图把 `thesis-ucas-doctor` 与 UCAS 资环“具体要 + Word 模板”基线进一步对齐。
- 主要动作包括：
  - 在共享 `ucasDissertation.cls` 中加入 `\makeSpine`，支持独立 `spine.tex`
  - 新增 `projects/thesis-ucas-doctor/scripts/export_docx.py`，提供 LaTeX→DOCX 导出与质量报告
  - 将两份官方参考资料收口到 `projects/thesis-ucas-doctor/docs/official/`
  - 扩展 README 与对照矩阵，说明 DOCX 验收口径
- 这个问题本身是真实存在的：PR body 和 diff 都说明维护者正在尝试把 UCAS thesis 线从“仅 PDF 对齐”推进到“结构与版式优先的 DOCX 验收链路”。

## 方案分析

### 优势

- PR 目标和限制写得比较清楚，没有把 DOCX 能力包装成已经成熟的通用能力。
- 书脊入口 `spine.tex` 独立出来，结构上清晰。
- `docs/official/README.md` 和 `SHA256SUMS.txt` 至少建立了“单一位置 + 完整性校验”的维护意识。

### 局限

- `export_docx.py` 的公式处理当前会破坏仓库真实示例里的 `equation + aligned` 输入。
- `export_docx.py` 的图片处理没有展开 `\graphicspath{{assets/}}`，会让当前示例里的裸 `\includegraphics{pngtest}` 丢图。
- PR 没有 CI / checks，也没有人工 reviewer 的明确结论；目前“导出链路通过”的证据主要来自作者自述。
- 作用域偏大：共享 class、项目脚本、官方二进制资料、README 和 CHANGELOG 一次混入，review 和回滚成本都偏高。

### 替代方案或待确认点

- 如果资环“最多三级标题”的约束只针对 `thesis-ucas-doctor`，更稳妥的方式是做成项目级开关或项目层覆写，而不是直接写死到共享 `ucasDissertation.cls` 默认行为里。
- 如果无法明确证明官方 `.doc/.docx` 可再分发，建议改成“来源链接 + 下载说明 + SHA256 + 用户自行下载”，不要直接把原件入库。

## 恶意/安全风险审查

- 结论：未发现明显恶意代码迹象，但存在中等偏高的工程风险。
- 低风险点：
  - 没有看到远程下载执行、shell 注入、遥测回传、密钥读写或 CI/CD 权限变更。
  - `pandoc` 调用使用参数列表，不是字符串拼接 shell 执行。
- 高风险点：
  - 新增 1209 行脚本，功能面扩张明显，但验证证据不足。
  - 两个 Office 二进制文件不可像源码一样透明审阅，增加了审计盲区。
- 综合判断：这不是“安全审计升级处理”级别的恶意 PR，但当前绝不该因为“无恶意”就直接 merge。

## License / 合规审查

- 结论：存在待确认风险。
- 风险来源：
  - `projects/thesis-ucas-doctor/docs/official/中国科学院大学资源与环境学位评定分委员会研究生学位论文撰写具体要.doc`
  - `projects/thesis-ucas-doctor/docs/official/中国科学院大学资环学科群研究生学位论文word模板.docx`
- 当前证据能确认：
  - 仓库整体 GitHub 元数据是 MIT
  - PR 新增了上述二进制官方文件
  - `docs/official/README.md` 与 `SHA256SUMS.txt` 只说明用途和校验，没有给出上游来源 URL、版权声明、转载许可或 NOTICE
- 当前证据不能确认：
  - 这两份官方文件是否允许被镜像进公开源码仓库
  - 是否允许随 release 资产或仓库长期再分发
- 建议动作：
  - 合入前补官方来源链接和再分发依据
  - 如无法明确证明许可，移除原件，只保留说明和校验值

## 与“好 PR”社区标准的对照

- 目标清楚：基本符合。PR body 结构化，目标明确。
- 风险与限制披露：部分符合。作者写了 DOCX 能力限制，但没正面处理授权边界和已知缺陷。
- 粒度合适：不符合。共享 class、项目脚本、文档和二进制资产缠结在一个 PR 里。
- 可验证：不符合。没有 CI / checks，没有人工 reviewer 结论，且已有自动 review 指向真实功能缺陷。
- reviewer 体验：一般。说明文字不少，但真正阻断 merge 的风险点分散在脚本实现、共享样式和二进制资产里，review 负担仍然重。

## 关键证据

- Diff / 元数据：
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/raw/pr_meta.json`
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/raw/pr_diff.diff`
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/raw/pr_files.json`
- 评论：
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/raw/pr_review_comments.json`
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/raw/pr_reviews.json`
- 关键源码快照：
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/raw/export_docx.py`
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/raw/ucasDissertation.cls.pr`
- 审查笔记：
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/evidence/key_findings.md`
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/evidence/missing_items.md`
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/notes/license_review.md`
- 并行独立审查：
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/parallel_review/independent_review_summary.md`
  - `.git-pr-review/run_20260326184515_huangwb8_ChineseResearchLaTeX_pr-39/parallel_review/independent_review_summary.json`

## 证据不足与待确认点

- 没有 CI / checks 结果。
- 没有 maintainer 或人工 reviewer 的明确结论。
- 没有官方 `.doc/.docx` 的来源 URL、版权声明或再分发依据。
- 5 个 `parallel-vibe` thread 都完成了内容审查，但由于有效沙箱是只读，无法写出标准 `RESULT.md`；本次综合结果来自 `runner.log` 中的最终审查正文，证据可追溯，但不是该 skill 的理想落盘形态。

## 建议的处理方式

- 当前建议：`Request changes`
- 最低修复条件：
  - 修复 `export_docx.py` 的 `aligned` 数学块处理
  - 修复 `\graphicspath` / 图片资源路径解析
  - 为 `--reference-doc` 显式路径补存在性检查
  - 补充官方 `.doc/.docx` 的来源与再分发依据；若无法证明许可，则不要提交原件
  - 最好补一轮可重复验证证据：至少脚本运行日志、质量报告样例，或更好的是 CI/checks
- 如果作者完成以上修复，并且验证证据补齐，这个 PR 可以再按 “Merge after fixes” 重新评估；在当前状态下不建议直接合入。
