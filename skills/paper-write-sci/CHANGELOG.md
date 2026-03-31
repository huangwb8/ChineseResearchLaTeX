# Changelog

All notable changes to paper-write-sci will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.10.0] - 2026-03-29

### Added

- 新增章节职责审查体系：`config.yaml` 增加 `section_role_check` 配置，工作区新增 `section-role-check/`，并补充 `references/templates/section-role-check-template.md` 与 `references/templates/discussion-role-check-template.md`，用于专门识别章节串位与 `Discussion` 复述 `Results` 的问题

### Changed

- `SKILL.md` 新增“章节职责守卫”“章节职责审查”与 `Discussion audit` 规则，并将 workflow 扩展为“数字审查 -> 章节职责终审 -> 逻辑终审”的闭环；协作模式计划要求新增 `section-role risk`
- `references/styles/bensz-01.md` 重写 `Discussion` 相关风格约束，明确区分 `Results` 与 `Discussion` 的“具体性”来源，并加入 `Discussion` 反例与改写方向，避免把作者感误做成数值堆叠
- `README.md`、`references/writing-style-guide.md`、`references/styles/general-01.md`、`references/styles/style-template.md` 与 `references/collaborative-plan-template.md` 同步对齐章节分工基线、`Discussion` 去结果化规则与计划输出要求
- `config.yaml` 版本从 `0.9.0` 升至 `0.10.0`

## [0.9.0] - 2026-03-29

### Changed

- 为 `.tex` 编辑新增“分段分点”策略：新段落必须通过空行表达；多个点仍属同一段时，改为逐行书写而不插空行，提升 PDF/Word 回跳源文时的定位体验
- `SKILL.md`、`README.md`、`references/writing-style-guide.md`、`references/styles/bensz-01.md`、`references/styles/general-01.md` 与 `references/styles/style-template.md` 同步补齐 `.tex` 源文可读性约束，覆盖正文、局限性展开与 panel-by-panel legend 场景
- `config.yaml` 新增 `tex_readability` 配置节，并将版本号从 `0.8.2` 升至 `0.9.0`

## [0.8.2] - 2026-03-28

### Changed

- 将 `bensz-01` 与 `general-01` 的来源说明恢复到 README 的“风格系统”章节，便于维护者查看风格出处，同时继续避免这些信息进入实际执行用的风格文件
- `config.yaml` 版本从 `0.8.1` 升至 `0.8.2`

## [0.8.1] - 2026-03-28

### Changed

- 删除风格文件中对具体来源材料与样本文件名的展示，避免向用户暴露与功能无关的内部来源声明
- 精简 `general-01` 的来源清单与 `style-template.md` 的来源字段，只保留风格定位、适用范围与可执行写作规则
- README 示例中的参考材料路径改为通用占位符 `reference.docx`，`config.yaml` 版本从 `0.8.0` 升至 `0.8.1`

## [0.8.0] - 2026-03-28

### Changed

- `bensz-01` 风格新增 Figure / Supplementary Figure legend 专项规则，明确要求采用更详尽的 panel-by-panel 导读写法，并补足视觉编码、术语解释、统计符号和读图门槛说明
- `references/writing-style-guide.md`、`references/styles/style-template.md`、`SKILL.md` 与 `README.md` 同步强化图注写作基线，要求 Supplementary Figure 与主图保持同等级别的可读性，不再默认写成简略提纲
- `config.yaml` 版本从 `0.7.1` 升至 `0.8.0`，并更新 `bensz-01` 的风格描述，使执行层和文档层口径一致

## [0.7.1] - 2026-03-28

### Changed

- 工作区隐藏目录从 `.write-paper-sci/` 统一更名为 `.paper-write-sci/`，避免继续沿用 legacy 命名
- `config.yaml`、`SKILL.md`、`README.md` 与运行清单字段同步切换到新目录名，确保脚本行为与文档口径一致

## [0.7.0] - 2026-03-26

### Added

- `scripts/prepare_workspace.py` 现在会为每轮工作生成独立 `run_id`、创建 `run_{timestamp}` 子目录，并在 `analysis/runtime-context.json` 写出当前运行清单
- 运行清单新增 `workspace_root`、`workspace_dir`、`analysis_dir`、`number_check_dir`、`logic_check_dir`、`render_dir`、`timestamp` 等字段，方便后续步骤显式引用本轮目录
- 协作模式计划文件默认使用 `WritePaperSCI_{topic}_{run_id}.md`，让计划与本轮隐藏工作区一一对应

### Changed

- `config.yaml` 新增 `runtime_outputs.timestamp_format` 与 `runtime_outputs.run_dir_pattern`，将 run 目录命名规则集中到单一配置源
- `SKILL.md`、`README.md` 与 `references/templates/logic-tree-template.md` 全面改为按本轮 `run_{timestamp}` 描述输出路径
- `config.yaml` 版本从 `0.6.0` 升至 `0.7.0`

### Fixed

- 修复同一篇论文多轮修改时共享 `.write-paper-sci/` 目录导致中间文件互相覆盖、难以追溯的问题
- 修复同一秒内重复启动协作模式时，计划文件名可能重名覆盖的问题

## [0.6.0] - 2026-03-26

### Added

- 新增统一风格框架文件 `references/styles/style-template.md`，为后续扩展作者风格与领域风格提供固定骨架
- 新增逻辑树模板 `references/templates/logic-tree-template.md`，统一论文主线、次线、证据与章节映射的表达方式
- `bensz-01` 风格重写为作者特征导向版本，突出问题导向开头、方法命名、数字对比和诚实局限
- `general-01` 风格重写为官方建议综合版本，吸收 Nature、Scientific Reports 与 Elsevier 官方写作建议
- README 重写，补充模式差异、风格系统、输出位置与典型 Prompt

### Changed

- skill 正式统一命名为 `paper-write-sci`，同时保留 `write-paper-sci` 作为兼容别名关键词
- `SKILL.md` 重构：明确默认模式为 `autonomous`，并将 `collaborative` 定义为“只产出计划、不改论文”
- 协作模式计划文件改为显式输出到 `<paper_dir>/plans/WritePaperSCI_{topic}_{timestamp}.md`
- 中间文件约束强化：除协作计划等明确交付物外，其余产物统一写入 `<paper_dir>/.write-paper-sci/`
- `config.yaml` 版本升级 `0.5.0 -> 0.6.0`，同步调整模式名、公共产物目录、风格框架与审查配置
- 数字审查模板与逻辑审查模板重写为更严格的可执行格式，便于基于 `parallel-vibe` 开展独立审查

### Fixed

- 修复 skill 元数据、README、CHANGELOG 中仍残留旧名 `write-paper-sci` 的不一致问题
- 修复协作模式计划文件此前落在隐藏目录中的约束偏差，使其符合“对外交付物在 `plans/`，其余中间文件在 `.write-paper-sci/`”的新规则

## [0.5.0] - 2026-03-26

### Added

#### 运行模式
- 新增两种运行模式：
  - **auto**（默认）：AI 自主模式，发现问题直接修改
  - **collaborative**：人机协作模式，只生成计划供人类审查
- 协作模式计划文件命名：`WritePaperSCI_{主题}_{时间戳}.md`

#### 风格化写作系统
- 新增风格文件目录：`references/styles/`
- 新增 `bensz-01` 风格：基于 gastric cancer 免疫亚型研究手稿，适用于生物医学领域
- 新增 `general-01` 风格：综合 Nature/Science/Cell 写作指南，适用于通用 SCI 论文
- 支持通过 config.yaml 配置默认风格
- 风格文件包含：叙事风格、章节风格、语言风格、数字呈现、术语一致性、示例库

#### 数字审查功能
- 基于 parallel-vibe 进行独立并行审查
- 三维度审查：来源验证、使用适当性、解读合理性
- 所有 runner 一致通过后才可写入数字
- 中间文件目录：`.write-paper-sci/number-check/`
- 审查模板：`references/templates/number-check-template.md`

#### 逻辑审查功能
- 构建论文逻辑树（主线 + 次线 + 章节对应）
- 四维度检查：断裂、矛盾、冗余、跳跃
- 多轮迭代审查（默认最多 3 轮）
- 基于 parallel-vibe 进行独立并行审查
- 中间文件目录：`.write-paper-sci/logic-check/`
- 审查模板：`references/templates/logic-check-template.md`

### Changed

#### 工作区目录
- 工作区隐藏目录从 `.write-paper/` 更改为 `.write-paper-sci/`
- 新增子目录：`number-check/`、`logic-check/`

#### SKILL.md 重构
- 新增“运行模式”章节
- 新增“风格化写作”章节
- 新增“数字审查”阶段（阶段 4）
- 新增“逻辑审查”阶段（阶段 5）
- 原有阶段编号后移（渲染输出从阶段 5 变为阶段 7）

#### config.yaml 更新
- 版本从 `0.4.0` 升至 `0.5.0`
- 新增 `mode` 配置（默认 auto）
- 新增 `style` 配置（默认 bensz-01）
- 新增 `number_check` 配置
- 新增 `logic_check` 配置
- 更新 `workspace.hidden_dir` 为 `.write-paper-sci`

### Fixed
- 修复原有 `.write-paper/` 目录命名与 skill 名称不一致的问题

## [0.4.0] - 2026-03-11

### Added
- README.md：新增用户使用指南，补充完整 Prompt 模板、局部改写示例、参考论文输入方式与输出说明
- SKILL.md：新增“高质量参考论文/项目”输入类型，并增加 `reference-style.md` 风格提炼产物
- config.yaml：新增 `directories`、`analysis_files`、`entry_candidates`、`render_detection` 配置

### Changed
- SKILL.md：阶段 0 增加必填输入校验与 Word 导出能力识别
- SKILL.md：阶段 2/3/5 强化“局部修改”“参考论文只学风格不抄句子”规则
- config.yaml：版本从 `0.3.0` 升至 `0.4.0`

### Fixed
- SKILL.md：修复“默认总能输出 Word”这一隐式假设
- protected_paths：补充 `*.bst`、`*.bbx`、`*.cbx`

## [0.3.0] - 2026-03-11

### Changed
- SKILL.md：章节→路径映射改为优先自动扫描 `main.tex` 的 `\input{}`
- SKILL.md：渲染输出阶段增加输出路径检测说明
- SKILL.md：`.write-paper/` 明确创建在论文源代码目录内
- config.yaml：删除 `section_order` 死配置

### Added
- SKILL.md：阶段 1.3 后增加轻量用户确认点
- `references/writing-style-guide.md`：各章节高质量写作示范风格

### Fixed
- 删除 SKILL.md 中的机器特定绝对路径
- 删除 config.yaml 中死配置

## [0.1.0] - 2026-03-11

### Added
- 初始化技能，实现核心功能：基于 LaTeX 项目的 SCI 期刊论文逐节写作
- SKILL.md：五阶段工作流
- 各章节详细写作指南
- config.yaml：章节路径映射、格式保护目录、构建工具优先级配置
- 工作区隔离机制
