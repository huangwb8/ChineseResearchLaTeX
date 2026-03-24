# Git PR Review: huangwb8/ChineseResearchLaTeX #36

## 结论摘要
- 建议：Request changes
- 风险等级：High
- 一句话判断：这个 PR 在当前形态下不适合直接 merge，阻塞点不是排版细节，而是三件更根本的事同时存在：它没有真正接上仓库现有 thesis 构建/发布链路、它把 GPL 来源代码带入了 MIT 根仓库但未澄清分发边界、而且它当前目标版式也并不符合你的 thesis 规范。

## 独立评审综合结果
- 独立评审次数：计划 5 次，已按 `git-pr-review` workflow 启动 `parallel-vibe` 且强制使用 `runner=codex`。
- 当前状态：并行独立评审仍在运行，尚未产出可聚合的 `RESULT.md`；本次报告因此以原始证据、仓库现状和 PR 讨论为主。
- 已知趋势：从已落盘的 `runner.log` 看，独立线程正在反复核对 license、构建入口与 release 打包问题，没有出现与主审方向相反的明显信号。
- 影响：不改变本报告的主结论，只意味着这里暂时不能给出完整的 recommendation / risk 分布统计。

## PR 在解决什么问题
- 背景：PR #36 试图把一个新的“国科大资源与环境学位论文”模板项目接入本仓库，PR 描述明确写着 “Source this project from LeoJhonSong/UCAS-Dissertation and adapt it for ChineseResearchLaTeX.”，目标包括 UCAS 指南对齐、资环 Word 版式约束、统一 thesis 构建工作流和 DOCX 导出支持。
- 证据：
  - PR 元信息：<https://github.com/huangwb8/ChineseResearchLaTeX/pull/36>
  - PR body：<https://github.com/huangwb8/ChineseResearchLaTeX/pull/36>
  - 作者后续说明其上游来自 GPL-3.0 仓库：<https://github.com/huangwb8/ChineseResearchLaTeX/pull/36#issuecomment-4115345218>

## 方案分析
### 优势
- 这是一次完整度较高的模板引入，不只是几行样式微调，而是把项目脚手架、README、VS Code 配置、DOCX 导出脚本和示例论文内容一起带进来了。
- PR 作者对已有 review comment 的响应是积极的，至少修掉了早期的明显编译问题和 README 错误，如 `\include{...}`、`\graphicspath`、`\listofnotations`、`etoolbox` 依赖等。
- 如果单独看这个子项目目录，它已经具备“可单项目自用”的雏形。

### 局限
- 第一处阻塞是“统一 thesis 工作流”并没有真正接上。当前 [`thesis_project_tool.py`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-thesis/scripts/thesis_project_tool.py#L74) 只把 `main.tex + extraTex/` 识别为 thesis 项目根，而新项目是 `Thesis.tex + styles/ + chapter*.tex` 结构；同时默认主文件仍是 [`main.tex`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-thesis/scripts/thesis_project_tool.py#L401)。这意味着 PR README 里声称可用的统一入口并不成立。
- 第二处阻塞是发布链路会坏。当前 [`scripts/pack_release.py`](/Volumes/2T01/Github/ChineseResearchLaTeX/scripts/pack_release.py#L34) 的白名单只会打包 `.vscode`、`extraTex`、`main.tex`、`README.md` 等约定布局；PR 新项目的关键文件却是 `styles/`、`bibs/`、`Thesis.tex`、`chapter*.tex`、`info.tex`、`abstract.tex`、`template.json`、`LICENSE`。在不改打包脚本的前提下，Release zip 将是不完整的。
- 第三处阻塞是该 PR 没有把新 thesis 项目完整纳入现有仓库叙事。当前根 README 的毕业论文模板列表仍只有 [`thesis-smu-master`](https://github.com/huangwb8/ChineseResearchLaTeX/blob/main/README.md#L143-L151) 和 [`thesis-sysu-doctor`](https://github.com/huangwb8/ChineseResearchLaTeX/blob/main/projects/README.md#L58-L64) 两个项目，说明这个新项目尚未跟 README/模板列表/发布口径完全对齐。
- 第四处是产品匹配问题。PR 本身服务的是“UCAS 资源与环境”这一特定规范；而你已经明确表示它“目前并不符合我的 thesis 的规范，可能要稍加改良才能使用”。这意味着即使它技术上能 merge，也还不是你可直接采用的模板交付物。

### 替代方案或待确认点
- 如果维护者愿意接收这个方向，建议先不要直接 vendoring 整套上游项目，而是先确定：
  1. 这个学校/学科模板是否要正式纳入 `bensz-thesis` 统一架构；
  2. 若纳入，项目结构要先改造成与现有 `thesis_project_tool.py`、`pack_release.py`、README 生成器兼容；
  3. 只有在 license 边界明确后，才决定是以独立 GPL 子树接入，还是仅参考公开规范重写实现。
- 如果你的目标是“尽快得到可用 thesis 模板”，这个 PR 更像一个外部模板导入草稿，而不是已经适配到本仓库生产口径的成品。

## 恶意/安全风险审查
- 结论：未发现明显恶意行为或后门迹象，但存在中高等级的“供应链/流程风险”。
- 风险信号：
  - 未发现凭证读取、远程下载执行、CI 权限修改、混淆载荷、删除审计日志等典型恶意信号。
  - 风险主要来自把大量外部来源代码直接拷入仓库，却没有同步把构建、发布、license 边界一起收口。
  - 新增的 `export_docx.py` 主要调用本地 `pandoc` / `zipfile` / `python-docx` 流程，未见网络外传逻辑；这一块更像复杂度和维护性问题，而不是安全后门。
- 证据：
  - PR 改动范围：34 files, 3860 additions，无删除。
  - 评论线程中也没有出现安全类修复，只围绕编译与 README 纠错。

## License / 合规审查
- 结论：存在明确待决风险，当前不适合在未补充说明和调整发布流程的情况下 merge。
- 风险来源：vendored 第三方模板代码、项目级 GPL 文本、MIT 根仓库分发口径、release zip 未打包 `LICENSE`。
- 关键事实：
  - 仓库根当前声明为 MIT：[`license.txt`](/Volumes/2T01/Github/ChineseResearchLaTeX/license.txt#L1)
  - PR 作者在描述和回复中都明确表示新项目源自 `LeoJhonSong/UCAS-Dissertation`，并说明上游仓库是 GPL-3.0：<https://github.com/huangwb8/ChineseResearchLaTeX/pull/36#issuecomment-4115345218>
  - 上游仓库当前公开标注为 GPL-3.0：<https://github.com/LeoJhonSong/UCAS-Dissertation>
  - 当前 release 打包白名单不包含项目级 `LICENSE`：[`pack_release.py`](/Volumes/2T01/Github/ChineseResearchLaTeX/scripts/pack_release.py#L34)
- 对你提出的三点关切，结论分别是：
  - `GPL/MIT 是否冲突`：我不把这件事表述成“必然法律冲突”，但就仓库治理和分发实践而言，现在的状态明显不清楚，风险足以阻止直接 merge。
  - `上游作者是否知情`：当前 PR 证据里没有看到与上游作者沟通、获知、回链或协作的记录。需要说明的是，若确实按 GPL 条款合规使用开源代码，法律上不一定要求逐一征得作者同意；但在一个 MIT 根仓库里直接 copy 进来时，没有这种上下游沟通证据，会显著放大 reviewer 的版权与社区关系担忧。
  - `版权问题`：现有证据能证明“有归因与 license 认知”，但不能证明“当前仓库的最终分发方式已经满足所有义务”。因此更准确的表述是“存在未解决的版权/再分发边界问题”，而不是已经完全合规。
- 建议动作：
  - 维护者先决定是否愿意在本仓库接受 GPL 子目录。
  - 若接受，必须同步补 README / NOTICE / Release 资产口径，并让打包脚本把相应许可证文本带出去。
  - 若不接受，则不要合入这些 GPL 源文件，改为基于公开规范重写并保留来源说明。

## 与“好 PR”社区标准的对照
- `问题定义清晰`：部分符合。PR 目标写得很直白，但“接入统一 thesis build workflow”这个承诺与当前代码真实接口不一致，因此问题定义和实际落地之间有落差。
- `改动范围可控`：不符合。一次性引入 34 个文件、3860 行新增、整套外部模板与导出脚本，超出了“易于 reviewer 快速确认安全和可维护性”的范围。
- `与现有架构一致`：不符合。仓库当前 thesis 主线强调 `packages/bensz-thesis/` 公共包和统一工具链，新项目却主要以项目内 vendored styles/scripts 自成体系存在。
- `验证证据充分`：不符合。PR 作者口头说“重新构建成功”，但本仓库侧没有 CI，没有将其纳入当前 `thesis_project_tool.py` / `pack_release.py` / README 模板列表等既有链路的可验证证据。
- `合规信息清楚`：不符合。license 来源虽被提到，但分发边界、仓库根 MIT 口径、release 打包遗漏 LICENSE 等问题都未收口。
- `reviewer 体验`：一般。作者愿意修评论是加分项，但 reviewer 仍需额外推断大量架构和合规后果。

## 关键证据
- PR 页面与元信息：
  - <https://github.com/huangwb8/ChineseResearchLaTeX/pull/36>
  - <https://github.com/huangwb8/ChineseResearchLaTeX/pull/36/files>
- 作者关于上游 GPL 的说明：
  - <https://github.com/huangwb8/ChineseResearchLaTeX/pull/36#issuecomment-4115345218>
- 当前 thesis 统一构建器只识别 `main.tex + extraTex/`：
  - [`packages/bensz-thesis/scripts/thesis_project_tool.py`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-thesis/scripts/thesis_project_tool.py#L74)
  - [`packages/bensz-thesis/scripts/thesis_project_tool.py`](/Volumes/2T01/Github/ChineseResearchLaTeX/packages/bensz-thesis/scripts/thesis_project_tool.py#L401)
- 当前 release 打包白名单：
  - [`scripts/pack_release.py`](/Volumes/2T01/Github/ChineseResearchLaTeX/scripts/pack_release.py#L34)
- 当前 thesis 项目说明仍围绕共享 `bensz-thesis` 公共包：
  - [`projects/README.md`](/Volumes/2T01/Github/ChineseResearchLaTeX/projects/README.md#L58)
- 根 README 的毕业论文模板列表仍未包含该项目：
  - [`README.md`](/Volumes/2T01/Github/ChineseResearchLaTeX/README.md#L143)
- 上游仓库公开主页：
  - <https://github.com/LeoJhonSong/UCAS-Dissertation>

## 证据不足与待确认点
- 没有看到本仓库维护者对“是否接受 GPL 子树”的明确态度，这决定了本 PR 是“可修复后再看”还是“方向上就不该进仓”。
- 没有看到与上游作者沟通、回链或协作的证据；这不自动等于违法，但会影响维护者对版权与社区关系风险的判断。
- 没有本仓库 CI / release dry-run 证明这个项目能走通既有 `thesis_project_tool.py` 与 `pack_release.py`。
- `parallel-vibe + codex` 的独立评审已启动，但截至本报告落笔时尚未完成聚合；若后续产物落盘，建议把 recommendation 分布再补写进本节上方的综合结果。

## 建议的处理方式
- 当前建议是 `Request changes`，而且是“阻塞式 changes”：
  1. 先明确 license 策略。没有这一点，不建议 merge。
  2. 若要继续推进，先把项目结构改造成与本仓库 thesis 主线兼容，至少要能真实通过 `thesis_project_tool.py`、`pack_release.py`、README 模板列表这三条主链路。
  3. 明确该模板只是“UCAS 资源与环境”场景，不应包装成已满足一般 thesis 规范的通用模板；你提出的“目前不符合我的 thesis 规范”这一点，应直接视为产品匹配度不足，而不是小瑕疵。
  4. 若维护者最终不接受 GPL 导入路径，建议关闭本 PR，改为基于公开写作规范与版式要求重新实现。
