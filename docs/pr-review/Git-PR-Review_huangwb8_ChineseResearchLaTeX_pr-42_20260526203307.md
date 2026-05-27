# Git PR Review: huangwb8/ChineseResearchLaTeX #42

## 结论摘要
- 建议：Request changes
- 风险等级：High
- 一句话判断：方向有价值，但 #42 把 #43 的 UCAS Word 导出、bensz-thesis/font 样式、全项目 VS Code 配置、skill 文档和官方二进制资料打成一个大包；在官方 `.doc/.docx` 再分发授权、CI/构建证据、与 #43 合并顺序未明确前，不建议直接 merge。

## 独立评审综合结果
- 独立评审次数：5
- recommendation 分布：Request changes 4；Merge after fixes 1
- risk 分布：High 5
- 共识：5/5 都认为风险为 High；4/5 明确要求先改后合。
- 分歧：1 个 thread 认为在修复后可 merge，但它同样把合规、验证和重叠关系列为必须先处理的问题。

## PR 在解决什么问题
- PR #42 试图添加 UCAS 公开模板与工作流更新：UCAS Word 导出链路、`bensz-thesis` 构建/样式加固、共享字体引用、VS Code launcher/settings 批量同步，以及 `thesis-writing-workflow` skill。
- 证据：`raw/pr_meta.json` 显示 #42 为 OPEN，base `main`，head `Tenstu:main`，67 files，+14632/-532，`mergeStateStatus=CLEAN`，`statusCheckRollup=[]`。
- 关键上下文：#42 包含 #43 的两个提交 `24540c1ccfe1`、`c099fe3b0a17`，并额外包含多个跨产品线提交；二者存在显著重叠。

## 方案分析
### 优势
- PR 描述有 Summary、Public Boundary 和 Verification，主动声明不包含私有正文、私有 bib、过程目录、个人资产或生成产物。
- VS Code 配置看起来来自统一模板同步，方向符合本仓库“模板集中维护、项目落地同步”的约定。
- 新增测试覆盖 UCAS Word 导出相关路径，且部分实现有前置检查、路径转义和构建锁。

### 局限
- 作用域过大：67 个文件横跨公共包、项目、VS Code 模板、skill、开发文档和二进制资料，难以一次性审清。
- 与 #43 重叠：#42 包含 #43 的 Word 导出提交，不应和 #43 无序同时 merge。
- 无 CI 状态：PR 描述列出本地命令，但 GitHub 元数据没有可复核的 checks。

### 替代方案或待确认点
- 优先拆分：先处理更聚焦的 #43，待其合规和验证问题解决后，再单独审 #42 中剩余的 thesis/font/VS Code/skill 改动。
- 若保留 #42，应要求作者拆 PR 或至少给出逐模块验证日志和回滚方案。

## 恶意/安全风险审查
- 结论：未发现明显恶意迹象，但安全风险为 High，主要来自大范围改动和新增本地自动化执行面。
- 风险信号：新增/修改 Python `subprocess.run`、可选 PowerShell/Word COM 自动化、临时 DOCX 写入替换、全项目 VS Code launcher 同步。
- 证据：diff 中未见网络下载、凭证读取、混淆 payload 或 secret 处理；PowerShell 路径有单引号转义，Word 自动化标为可选。

## License / 合规审查
- 结论：存在待确认风险，当前是 merge 阻断项。
- 风险来源：PR 提交 UCAS 官方 `.doc/.docx` 二进制原件和 CSL 文件；`docs/official/README.md` 从“不直接提交原件，因为再分发权限未明确”改为“仓库随项目提供原件”。
- 建议动作：merge 前要求维护者确认 UCAS 官方文件再分发授权；若不能确认，恢复 download + SHA256 校验流程。CSL 文件需补来源和许可说明。

## 与“好 PR”社区标准的对照
- 小而聚焦：不符合。#42 把多个产品线和流程改动合在一起。
- 可验证：部分符合。PR 写了验证命令，但缺少 CI/check 日志。
- 可审查：不充分。3-4 万行 patch 和二进制文件让 review 成本很高。
- 风险披露：部分符合。描述了 public boundary，但没有补足官方资料再分发许可证明。

## 关键证据
- Diff：`.git-pr-review/run_20260526203307_huangwb8_ChineseResearchLaTeX_pr-42/raw/pr_diff.patch`
- 元数据：`.git-pr-review/run_20260526203307_huangwb8_ChineseResearchLaTeX_pr-42/raw/pr_meta.json`
- 独立评审聚合：`.git-pr-review/run_20260526203307_huangwb8_ChineseResearchLaTeX_pr-42/parallel_review/independent_review_summary.md`
- 评论：#42 无 issue comments / review comments。
- CI：`statusCheckRollup=[]`。

## 证据不足与待确认点
- 缺失材料：CI 结果、本地验证日志、官方 UCAS 文件再分发授权证明、二进制文件来源/许可声明、跨模块回滚方案。
- 对结论的影响：这些缺口直接影响是否可以 merge，因此建议 Request changes。

## 建议的处理方式
- 不要直接 merge #42。
- 请维护者先决定 #42/#43 的关系：建议优先让 #43 作为聚焦 PR 处理，#42 拆成后续独立 PR。
- 要求补齐：官方文件再分发授权或改回下载校验；CSL 来源/许可；CI 或可复核验证日志；跨产品线改动拆分说明。
