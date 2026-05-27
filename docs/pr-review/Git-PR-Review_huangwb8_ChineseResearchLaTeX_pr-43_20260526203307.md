# Git PR Review: huangwb8/ChineseResearchLaTeX #43

## 结论摘要
- 建议：Request changes
- 风险等级：High
- 一句话判断：#43 比 #42 聚焦，功能方向合理，Copilot 评论多数已处理；但官方 `.doc/.docx` 直接入库的再分发授权缺失、无 CI 证据、CSL 来源许可不完整，仍不建议直接 merge。

## 独立评审综合结果
- 独立评审次数：5
- recommendation 分布：Request changes 5
- risk 分布：High 4；Medium 1
- 共识：5/5 均要求修改后再评估；最大共识是 license / 官方文件再分发是主要阻断点。
- 分歧：1 个 thread 将安全风险评为 Medium，但仍建议 Request changes；其余 4 个 thread 因合规和验证缺口评为 High。

## PR 在解决什么问题
- PR #43 为 `projects/thesis-ucas-doctor` 添加公开 UCAS Word 导出 workflow，包括 LaTeX 预处理、Pandoc DOCX 导出、DOCX 后处理、GB/T 7714 CSL、官方 Word 模板/规范、公开测试和格式 checklist。
- 证据：`raw/pr_meta.json` 显示 #43 为 OPEN，base `main`，head `Tenstu:submit-ucas-word-export-public`，16 files，+13484/-421，`mergeStateStatus=CLEAN`，`statusCheckRollup=[]`。

## 方案分析
### 优势
- 目标聚焦在 UCAS 项目级 Word 导出能力，没有扩散到整个 `bensz-thesis` 通用 DOCX 产品线。
- PR 描述给出 Test Plan，并说明 `pandoc`、`python-docx`、Microsoft Word/PowerShell 的适用条件。
- Copilot 的 8 条评论中，作者在 `c099fe3` 回复并修复了测试模块命名污染、无效 `--dry-run`、未使用常量、相对路径测试、弱断言、重复 normalization 等实现问题。
- 未见明显恶意信号：没有网络下载、secret 读取、远程 payload 或混淆代码。

### 局限
- `export_docx.py` 体量很大，单 PR 审查成本高。
- Word COM/PowerShell 自动化虽然是可选增强，但仍增加本地执行面，需要清晰边界和测试。
- 无 CI/check 结果，PR 描述中的测试命令没有机器可复核日志。

### 替代方案或待确认点
- 若 UCAS 官方文件不可再分发，应回到“用户自行下载 + SHA256 校验”的流程。
- 可考虑先 merge 代码和 checksum/下载说明，不把 `.doc/.docx` 二进制原件放入 Git 历史。

## 恶意/安全风险审查
- 结论：未发现明显恶意，但安全风险中到高；合并前应补验证。
- 风险信号：本地调用 pandoc、可选 PowerShell/Word COM、DOCX zip/XML 后处理、临时文件替换。
- 缓解因素：材料显示调用多用参数列表；PowerShell 使用 `-NoProfile -NonInteractive`；路径进入单引号前做转义；Word 自动化限定 Windows 且可选。

## License / 合规审查
- 结论：存在待确认风险，当前是 merge 阻断项。
- 风险来源：两个 UCAS 官方 `.doc/.docx` 原件被直接提交；README 从“再分发权限未明确，不直接提交原件”改为“仓库随项目提供原件”。CSL 文件也需要明确来源和许可。
- 建议动作：要求维护者确认 UCAS 官方文件允许在 GitHub 仓库再分发；若不能确认，移除二进制原件，保留下载链接、文件名规范和 SHA256 校验。

## 与“好 PR”社区标准的对照
- 小而聚焦：基本符合，范围主要在 `projects/thesis-ucas-doctor`。
- 可验证：部分符合，提供测试计划但缺 CI 证据。
- 可审查：部分符合，功能边界清晰，但 `export_docx.py` 和二进制 patch 体量较大。
- 合规清晰：不符合，官方原件再分发授权未证明。

## 关键证据
- Diff：`.git-pr-review/run_20260526203307_huangwb8_ChineseResearchLaTeX_pr-43/raw/pr_diff.patch`
- 元数据：`.git-pr-review/run_20260526203307_huangwb8_ChineseResearchLaTeX_pr-43/raw/pr_meta.json`
- Review comments：`.git-pr-review/run_20260526203307_huangwb8_ChineseResearchLaTeX_pr-43/raw/pr_review_comments.json`
- 独立评审聚合：`.git-pr-review/run_20260526203307_huangwb8_ChineseResearchLaTeX_pr-43/parallel_review/independent_review_summary.md`
- CI：`statusCheckRollup=[]`。

## 证据不足与待确认点
- 缺失材料：CI 结果、测试日志、官方 UCAS `.doc/.docx` 再分发授权证明、CSL 来源/许可、实际 DOCX 导出样例或质量报告。
- 对结论的影响：功能可以继续推进，但合规和验证证据不足使当前状态不宜 merge。

## 建议的处理方式
- Request changes。
- 优先处理官方二进制再分发问题：确认授权，或移除原件并恢复下载校验流。
- 补充 CI 或可复核日志：至少覆盖 `test_prepare_tex_for_word_export.py`、`test_export_docx_public.py`、`export_docx.py --help`、`git diff --check`。
- 明确与 #42 的关系：若 #43 修好并合并，#42 应 rebase/拆分，避免重复合入同一提交和大范围附带改动。
