# nsfc-schematic 变更日志

本文档记录 `nsfc-schematic/` 的重要变更，格式遵循 Keep a Changelog。

## [Unreleased]

（暂无）

## [0.8.1] - 2026-02-19

### Added（新增）

- `references/models/templates.yaml`：新增图类型模板库（5 类常用骨架），用于规划阶段自动选型/强制指定。
- `scripts/plan_schematic.py`：新增 `--template-ref`，支持在规划阶段强制指定图类型模板。

### Changed（变更）

- `scripts/plan_schematic.py`：`proposal_path` 场景优先综合提取“立项依据 + 研究内容”，提升模板选择与叙事结构的全面性。
- `config.yaml`：新增 `layout.template_ref`（默认 `auto`）与 `planning.models_file`（默认指向模板库文件）。
- `config.yaml`：`evaluation.evaluation_mode` 默认改为 `heuristic`（`ai` 作为可选增强）。
- `config.yaml`：默认启用 PDF 导出（若检测到 draw.io CLI 则导出；否则保持 svg/png 交付）。
- `SKILL.md` / `README.md`：补齐“模板选择”工作流与交付自检清单，更新评估模式默认值说明。

### Fixed（修复）

- `scripts/spec_parser.py`：增加保守的“术语一致性”提示（warning-only），帮助早期发现同一概念多种写法风险（不影响解析/渲染）。

## [0.8.0] - 2026-02-16

### Added（新增）

- `scripts/ai_evaluate.py`：新增 AI 主评估离线协议（`ai_eval_request.md` + `ai_eval_response.json`），请求包直接包含 spec+关键 config+PNG 路径（不再依赖“先算度量再翻译”）。
- `scripts/ai_extract_tex.py`：新增 AI TEX 提取离线协议（`ai_tex_request.md` + `ai_tex_response.json`），支持 AI 直接读 TEX 生成 `spec_draft`（无响应自动降级）。

### Changed（变更）

- `config.yaml`：`evaluation.evaluation_mode` 默认改为 `ai`（无响应时自动降级为启发式评估，保证脚本可跑通）。
- `config.yaml`：新增 `planning.extraction.ai_tex_max_chars`（默认 20000），用于限制 `ai_tex_request.md` 体积，降低 context overflow 风险。
- `scripts/evaluate_schematic.py`：AI 模式从“度量驱动”改为“请求包驱动”，不再强依赖 `measure_schematic.py` 才能出协议文件。
- `scripts/generate_schematic.py`：移除 AI 模式下 `dimension_measurements.json`/`ai_dimension_*` 协议生成；当 AI 主评估生效时默认跳过多维度启发式扣分，避免口径重复。
- `scripts/plan_schematic.py` / `scripts/generate_schematic.py`：当输入来自 TEX 且启用 AI 模式时，优先消费 `ai_tex_response.json` 中的 `spec_draft`；缺失时自动回退到正则术语抽取。
- `scripts/utils.py`：`read_text()` 增加 UTF-8/UTF-8-SIG/GB18030 解码容错，提升跨平台标书兼容性（Windows/历史 GBK 编码）。
- `SKILL.md`：同步更新 AI 模式产物与工作流说明。

## [0.7.0] - 2026-02-15

### Added（新增）

- `scripts/measure_schematic.py`：新增主评估“纯度量采集层”，输出几何/路由/像素 proxy 度量（不做 P0/P1/P2 判定）。
- `scripts/measure_dimension.py`：新增多维度自检“纯度量采集层”，输出 structure/visual/readability 的结构化度量（不做 P0/P1/P2 判定）。
- `scripts/geometry.py`：抽取主评估与度量采集共用的几何/距离/相交判定，避免口径漂移。
- `scripts/color_math.py`：抽取 WCAG 对比度计算等色彩数学，避免 evaluate/measure 口径漂移。
- `config.yaml`：新增 `evaluation.evaluation_mode`（`heuristic|ai`），支持离线 AI 评估协议：产出 `measurements.json` / `dimension_measurements.json` 与 `ai_*_request.md`/`ai_*_response.json` 模板。
- `tests/ai自主规划-优化-v202602151546/`、`plans/v202602151643.md`、`tests/v202602151643/`、`plans/B轮-v202602151703.md`、`tests/B轮-v202602151703/`：新增轻量测试闭环与 auto-test-skill A/B 轮验证证据。

### Changed（变更）

- `scripts/evaluate_schematic.py`：启用 `evaluation_mode=ai` 时生成离线评审协议文件，并在检测到有效 `ai_evaluation_response.json` 时使用 AI 结果；否则自动回退启发式评估以保证流程可跑通。
- `scripts/evaluate_schematic.py`：新增 `protocol_dir` 参数（优先于内部 hook）用于控制协议文件输出目录，避免污染 config 对象。
- `scripts/evaluate_dimension.py`：新增 `write_ai_dimension_protocol()`，用于生成多维度离线评审协议文件（不在脚本内调用任何外部模型/联网）。
- `scripts/generate_schematic.py`：AI 模式下自动生成 `dimension_measurements.json`/`ai_dimension_request.md`/`ai_dimension_response.json`（不依赖 multi_round_self_check 开关），并支持从 AI 返回的 `suggestion` 字段驱动 `_apply_auto_fixes()`（带参数白名单与范围护栏）；无有效 AI 响应时回退启发式评估/自检。
- `README.md` / `SKILL.md`：补充 `evaluation_mode=ai` 的使用方式与离线协议产物说明。

## [0.6.0] - 2026-02-14

### Added（新增）

- `scripts/evaluate_dimension.py`：引入多维度批判性自检（structure/visual/readability），每轮生成 `critique_*.json` 证据并以线性扣分形成 `score_total`。
- `config.yaml`：新增 `evaluation.multi_round_self_check`（可开关、可配置扣分权重）与 `evaluation.exploration.candidates_per_round`（每轮有限候选对比）。
- `scripts/generate_schematic.py`：当 `evaluation.stop_strategy=ai_critic` 且命中平台期时，自动生成离线宿主 AI 视觉复核请求 `ai_critic_request.md` 与 `ai_critic_response.json` 模板（不在脚本内调用任何外部模型/联网）。
- `tests/多轮自检-v202602141523/`：新增轻量测试闭环（`PLAN.md` + `REPORT.md` + fixture），覆盖 `critique_*.json`、`score_base/score_penalty/score_total`、正交路由 `edge_crossings` 与 `ai_critic_request.md` 生成。
- `plans/v202602141625.md` / `tests/v202602141625/`：新增 auto-test-skill A 轮批判性测试会话（含回归脚本与端到端证据）。
- `plans/B轮-v202602141637.md` / `tests/B轮-v202602141637/`：新增 auto-test-skill B 轮质量原则检查会话与验证证据。

### Changed（变更）

- `scripts/generate_schematic.py`：每轮从 `_candidates/` 中选择最优候选并提升到 `round_*/` 根目录；`evaluation.json` 增补 `score_base/score_penalty/score_total`；报告补充 Top defects，自动修复策略改为按 defect.dimension 定向调整。
- `scripts/evaluate_schematic.py`：正交路由（orthogonal）下的 edge-edge crossings 统计改为“按边对计数”（避免长折线路由被过度惩罚），并将缺陷维度从 `edge_integrity` 拆分为 `edge_crossings`（便于定向修复）。
- `scripts/evaluate_dimension.py`：对 `color_scheme.file` 增加路径安全校验（拒绝 `..`/绝对路径/盘符路径），避免读取超出 skill 根目录的文件。
- `scripts/schematic_writer.py`：分组标题默认使用配色方案的 text 颜色，提升导出一致性与可读性。
- `scripts/utils.py`：新增 `is_safe_relative_path()` 并在生成/评估脚本中复用，统一路径安全口径。
- `scripts/render_schematic.py`：内部渲染读取 `color_scheme.file` 前增加路径安全校验，避免越权读取。
- `config.yaml`：补齐 `evaluation.thresholds.wcag_contrast_*` 与 `crowded_density_*` 默认阈值，减少“隐藏默认值”导致的口径不透明。
- `README.md` / `SKILL.md`：同步更新新产物与停止策略口径。

## [0.5.1] - 2026-02-14

### Added（新增）

- `scripts/plan_schematic.py`：规划模式完成后，默认在当前工作目录额外输出 `schematic-plan.md` 作为扁平交付文件，便于用户审阅；支持 `--no-workspace-plan` 禁用。

### Changed（变更）

- `README.md` / `SKILL.md`：补充 `schematic-plan.md` 的交付口径与审阅步骤说明。

## [0.5.0] - 2026-02-13

### Added（新增）

- `config.yaml`：新增 edge label 字号配置 `layout.font.edge_label_size`，并新增缩印门禁所需阈值 `evaluation.thresholds.min_edge_font_px/warn_edge_font_px`。
- `config.yaml`：新增 title 落图开关与顶部预留 `layout.title.enabled/layout.title.padding_y`（避免 `layout.font.title_size` 成为僵尸配置）。
- `scripts/routing.py`：新增确定性正交路由（waypoint）实现，用于渲染兜底、drawio 写入与评估口径对齐。
- `tests/优化-v202602131859/`：新增回归测试，覆盖 edge label 字号注入、waypoint 写入、title cell 落图与 PNG 尺寸口径。
- `plans/优化-v202602131859.md`：新增“SeqCCS 原理图实例暴露问题”的优化计划（作为本版本优化依据与复盘记录）。

### Changed（变更）

- `scripts/schematic_writer.py`：为所有连线注入 edge label 可读性样式（`fontSize/fontColor/fontStyle/labelBackgroundColor`），并在正交路由模式下写入 waypoint（`mxGeometry/Array@points`）。
- `scripts/spec_parser.py`：在自动布局时为 title 预留顶部空间，避免与分组/节点重叠。
- `scripts/evaluate_schematic.py`：补齐 edge label 字号与缩印等效字号检查；并改为基于确定性路由的“连线穿越/贴近节点”启发式检查，降低误报与停滞。
- `scripts/render_schematic.py`：draw.io CLI 渲染 PNG 时同时约束宽高，并在必要时对 PNG 做居中裁剪/补边以对齐 spec 画布尺寸；内部渲染兜底同步使用 edge label 字号与标题开关。

### Fixed（修复）

- `scripts/evaluate_schematic.py`：修复在非 straight 路由模式下 `edge_crossings` 计数未初始化导致的运行时错误。

## [0.4.0] - 2026-02-13

### Added（新增）

- `config.yaml`：新增输出文件管理配置：`output.hide_intermediate`、`output.intermediate_dir`、`output.max_history_runs`，用于将中间产物隐藏到 `.nsfc-schematic/` 并限制历史 run 数量。
- `scripts/generate_schematic.py`：新增 `--config` 参数，允许为单个项目指定独立配置文件。
- `scripts/evaluate_schematic.py`：新增缩印可读性检查（`evaluation.thresholds.print_scale_*`）。

### Changed（变更）

- `scripts/generate_schematic.py`：默认将 `run_*`、`optimization_report.md`、`spec_latest.yaml`、`config_used_best.yaml`、`evaluation_best.json` 等中间产物写入隐藏目录（默认 `.nsfc-schematic/`），避免污染用户工作目录；并在运行开始时自动收纳旧版残留到 `.nsfc-schematic/legacy/`。
- `scripts/generate_schematic.py`：对 `output.intermediate_dir` 与 `output.artifacts.*` 增加相对路径安全校验（拒绝 `..`/绝对路径/盘符路径），避免写出 `output_dir`。
- `config.yaml`：提升默认字号与阈值（`node_label_size`、`warn_font_px` 等），更贴近缩印场景的可读性需求。
- `README.md` / `SKILL.md`：同步更新输出结构与配置说明。

## [0.3.1] - 2026-02-13

### Fixed（修复）

- `scripts/plan_schematic.py`：修复含中文/非 ASCII 术语时可能生成重复 node id，导致 spec 解析失败的问题。
- `scripts/plan_schematic.py`：增强 2-5 分组支持（可包含多个 process 分组），并补齐结构性自检（重复 id / edge 端点不存在）。
- `scripts/plan_schematic.py`：`--plan-md` 模式导出后新增自检；存在 P0 时以 exit_code=2 阻断误用（仍保留导出产物便于修正）。
- `scripts/extract_from_tex.py`：补充 `\\subsection{研究内容}` 匹配与短语清洗，提升规划阶段术语提示质量。

## [0.3.0] - 2026-02-13

### Added（新增）

- 新增“规划阶段”脚本：`scripts/plan_schematic.py`，支持从 TEX/自然语言生成 `PLAN.md` + `spec_draft.yaml`（先规划再生成）。
- 新增规划模板：`references/plan_template.md`，标准化规划草案的输出结构与自检清单。
- `config.yaml`：新增 `planning.*` 配置（规划输出文件名、默认分组、规划自检阈值等）。

### Changed（变更）

- `README.md` / `SKILL.md`：新增“规划模式”使用说明与示例命令。
- `scripts/extract_from_tex.py`：增强“研究内容”段落定位与短语提取，提升规划阶段的术语提示质量。

## [0.2.2] - 2026-02-13

### Added（新增）

- `config.yaml`：新增 `layout.text_fit`（节点文案自动扩容）与 `layout.auto_expand_canvas`（自动扩展画布）配置项，减少“文字溢出/贴边/越界”风险。

### Fixed（修复）

- `scripts/schematic_writer.py`：调整 `.drawio` 元素层级为“分组底层 → 连线中层 → 节点顶层”，降低“线压字/遮挡文字”的风险。

### Changed（变更）

- `scripts/spec_parser.py`：在解析 spec 时对节点做确定性的文字适配 autosize，并基于实际节点尺寸计算分组尺寸；必要时自动扩展画布以避免越界。
- `scripts/evaluate_schematic.py`：将“节点文案溢出/遮挡”从软提示加强为 P0/P1 分级（更贴合出版级交付硬门槛）。

## [0.2.1] - 2026-02-11

### Added（新增）

- `tests/v202602112232/`：新增回归测试，确保含换行 label 的 `.drawio` 仍是合法 XML（且 `<br>` 必须被转义为 `&lt;br&gt;`）。

### Fixed（修复）

- `scripts/schematic_writer.py`：修复换行转 `<br>` 未转义导致 `.drawio` 非法 XML、draw.io CLI “部分解析”后只剩大分组框的问题。
- `scripts/generate_schematic.py`：新增 `.drawio` XML 合法性 preflight；非法时直接阻断渲染与评估并给出可读错误。

### Changed（变更）

- `scripts/render_schematic.py`：导出分辨率优先以 spec 的 `canvas.width` 为准，避免与渲染/评估口径不一致。
- `scripts/evaluate_schematic.py`：当 spec 节点数充足但 PNG 像素密度极低时，将其提升为 P0/P1（疑似渲染内容缺失/被忽略）。
- `scripts/generate_schematic.py`：每次运行创建 `run_YYYYMMDDHHMMSS/` 隔离 `round_*`，并在 `output_dir` 根目录同步 latest best 产物与报告。

## [0.2.0] - 2026-02-11

### Added（新增）

- `config.yaml`：新增 `evaluation.stop_strategy=plateau` + `evaluation.plateau.*`，用“收敛/停滞检测”替代硬阈值早停（legacy `early_stop` 保留兼容但默认关闭）。
- `config.yaml`：新增 `evaluation.exploration.*`，多轮自动扰动布局参数以探索不同候选（可复现 seed）。
- `evaluate_schematic.py`：新增“长对角线/穿越或贴近节点/节点文案拥挤度”等更贴近审稿人观感的指标与 defects，并在结果中输出 `metrics`。

### Changed（变更）

- `render_schematic.py`：内部渲染兜底升级为正交连线，并输出真正矢量 `schematic.svg`（不再用 PNG 包装 SVG）。
- `generate_schematic.py`：报告增加 draw.io CLI 缺失强提示与安装指引；每轮记录 `schematic.png` 的 SHA256；默认 stop_strategy 下可在收敛时提前停止。
- `evaluate_schematic.py`：调整综合评分权重（默认更偏向启发式评分，避免视觉分“常量化”主导）。

## [0.1.1] - 2026-02-11

### Fixed（修复）

- `render_schematic.py` / `evaluate_schematic.py`：将 Pillow 依赖改为“按需导入”，避免在仅使用 draw.io CLI 时也强制依赖 Pillow。
- `spec_parser.py`：新增 group/node/edge id 的格式校验，避免生成非法 XML 或引入注入风险。
- `evaluate_schematic.py`：视觉分辨率检查改为以 spec 的画布尺寸为准，避免与渲染产物尺寸不一致。

### Changed（变更）

- `generate_schematic.py`：`--output-dir` 改为可选；未指定时默认使用 `config.yaml:output.dirname`（相对当前工作目录）。
- `SKILL.md` / `README.md`：更新示例命令，避免输出写入 `tests/`。

## [0.1.0] - 2026-02-11

### Added（新增）

- 初始化技能骨架：`SKILL.md`、`README.md`、`config.yaml`、`CHANGELOG.md`
- 新增核心脚本：`spec_parser.py`、`schematic_writer.py`、`render_schematic.py`、`evaluate_schematic.py`、`extract_from_tex.py`、`generate_schematic.py`
- 新增配色库：`assets/color_schemes.yaml`
- 新增参考资料与示例：`references/design_principles.md`、`references/spec_examples/*.yaml`
- 新增测试会话：`tests/init/PLAN.md`、`tests/init/REPORT.md`
- 首次发布 `nsfc-schematic`，支持从结构化 spec 或 TEX 提示生成 NSFC 原理图。
- 交付格式支持 `.drawio`、`.svg`、`.png`，并提供多轮评估优化与 best round 导出。
