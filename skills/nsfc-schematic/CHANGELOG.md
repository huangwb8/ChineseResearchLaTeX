# nsfc-schematic 变更日志

本文档记录 `nsfc-schematic/` 的重要变更，格式遵循 Keep a Changelog。

## [Unreleased]

（暂无）

## [0.14.1] - 2026-03-01

### Changed（变更）

- `scripts/generate_schematic.py`：增强 Nano Banana / Gemini PNG-only 模式的 prompt 文本排版约束（打印级字体风格 + 禁止扭曲/旋转/艺术字 + 建议“白底标签框”承载文字），降低图片中文字“扭曲/不可读”风险
- `README.md` / `SKILL.md`：补充 Nano Banana 文字可读性调优建议与硬约束说明

## [0.14.0] - 2026-03-01

### Changed（变更）

- `config.yaml`：将 `evaluation.stop_strategy` 默认值从 `plateau` 改为 `ai_critic`，使 AI 闭环评价成为开箱即用的默认模式（无需手动配置 `config_local.yaml`）
- `SKILL.md`：更新"评估-优化循环"章节，反映 ai_critic 为默认模式；更新"AI 自主闭环"章节，去掉"可选"表述，并说明如何回退到 plateau

## [0.13.1] - 2026-03-01

### Changed（变更）

- `config.yaml`：默认将 `layout.font.edge_label_size` 从 22 调整为 24，提升连线标签缩印可读性
- `config.yaml` / `scripts/spec_parser.py`：新增 `layout.canvas_fit.center_content`（默认 true），自动布局下将内容包围盒居中，减少单侧大留白与视觉重心偏移

## [0.13.0] - 2026-03-01

### Added（新增）

- Nano Banana / Gemini PNG-only 渲染模式：`scripts/generate_schematic.py --renderer nano_banana`（仅当用户主动要求时使用；只交付 `schematic.png`）。
- `scripts/nano_banana_check.py`：基于项目根目录 `.env` 的 Gemini 配置做连通性检查（不会生成图片）。
- `scripts/nano_banana_generate_png.py`：独立的 Nano Banana PNG 生成器（便于调试与复用）。
- `scripts/nano_banana_client.py` / `scripts/env_utils.py`：Gemini 配置加载与 REST 调用封装（支持从 CWD 向上查找 `.env`）。
- Nano Banana 调试证据：每次生成会在 debug_dir 写出 `nano_banana_request.json` / `nano_banana_response.json`（不包含 API key）。

### Changed（变更）

- `scripts/generate_schematic.py`：新增 `--renderer`（默认 drawio；nano_banana 模式自动关闭 SVG/PDF 导出，并避免每轮多候选导致的成本乘法）。
- `README.md` / `SKILL.md`：补齐 Nano Banana 模式的触发规则、环境变量要求与可执行 runbook。

## [0.12.3] - 2026-03-01

### Added（新增）

- `README.md` / `SKILL.md`：新增“parallel-vibe 多方案并行优化”runbook，用于在需要反复开多条 run 做对比时，把不同策略拆到隔离工作区里并行尝试。
- `scripts/generate_schematic.py`：新增 `--run-tag`，为 `run_*/` 目录附加可读标签（便于多策略对比时快速定位 run 来源）。

### Changed（变更）

- `scripts/generate_schematic.py`：扩展 `config_local.yaml` 白名单，支持在不修改全局 `config.yaml` 的前提下做“实例级/线程级”参数对比：
  - `renderer.internal_routing`
  - `layout.auto.{margin_x,margin_y,node_gap_x,node_gap_y,group_gap_x,group_gap_y,max_cols}`
  - `evaluation.exploration.{enabled,candidates_per_round,seed}`

## [0.12.2] - 2026-03-01

### Added（新增）

- `config.yaml`：新增 `renderer.drawio.cli_path`，允许显式指定 draw.io CLI 可执行文件路径（或可被 PATH 解析的命令名），降低跨平台安装/路径问题导致的“无法使用 CLI”概率。
- `scripts/generate_schematic.py`：`config_local.yaml` 白名单放开 `renderer.drawio.cli_path`，支持单项目/单实例覆盖（无需修改全局配置）。

### Changed（变更）

- `scripts/generate_schematic.py`：从 TEX 抽取术语数量改为读取 `config.yaml:planning.extraction.max_terms`（并做范围钳制），避免与配置口径不一致。
- `README.md` / `SKILL.md`：补齐 `renderer.drawio.cli_path` 的使用说明。

### Fixed（修复）

- `scripts/generate_schematic.py`：修复 `ai_critic_response.version` 非 1 时的异常处理分支（避免触发 `NameError`）。
- `scripts/generate_schematic.py`：修复 label wrap 的空白检测正则（支持按单词边界换行）。
- `scripts/render_schematic.py`：draw.io CLI 渲染路径下的 PNG 画布尺寸校正不再强依赖 Pillow（缺失时降级跳过并给出提示）。

## [0.12.1] - 2026-03-01

### Added（新增）

- `references/spec_examples/seqccs_min.yaml`：新增最小回归夹具（显式 canvas 下的 fit-to-canvas + PDF 正常交付），用于防止“隐式扩画布→导出缩放→等效字号变小”回归。

### Changed（变更）

- `scripts/render_schematic.py`：draw.io CLI 导出参数对齐与增强：
  - PDF 导出默认启用 `--crop`，并提供不支持 `--crop` 的兼容回退；
  - SVG/PDF 与 PNG 一样固定 `--width/--height`，减少导出尺寸漂移；
  - 未检测到 draw.io CLI 时，PDF 自动降级为 PNG→PDF 栅格输出（保证交付目录内始终有可用 PDF）。
- `scripts/spec_parser.py`：显式 `schematic.canvas` 时优先 fit-to-canvas：
  - 自动布局在计算分组网格时基于可用宽度自动降列（支持 `cols=1`），避免内容溢出触发导出缩放/平铺；
  - 显式 canvas 不再自动扩画布（包括 `auto_expand_canvas` 与 `canvas_fit` 的扩张路径），仅允许按需收缩。
- `scripts/generate_schematic.py`：`optimization_report.md` 的 Final 段落补齐 `schematic.pdf`（当 PDF 启用时），并对齐 `config_local.color_scheme.name` 白名单到实际内置配色方案。
- `config.yaml`：`evaluation.exploration.max_cols_options` 扩展为 `[1, 2, 3]`，让自修复/探索能尝试 `max_cols=1`。

## [0.12.0] - 2026-03-01

### Added（新增）

- `config.yaml`：新增 `evaluation.spec_variants`（默认关闭），支持对节点/分组 label 做“安全变体”（wrap/truncate/candidates），用于缓解“长文案导致拥挤/溢出”的布局问题。

### Changed（变更）

- `scripts/generate_schematic.py`：`optimization_report.md` 每轮显式记录“下一轮 auto-fix 配置增量”（可解释性增强），并补齐“显式布局较多”时的保守修复/引导策略。
- `scripts/generate_schematic.py`：`config_local.yaml` 白名单放开 `evaluation.spec_variants`（mode/wrap_max_chars/truncate_max_chars/allow_in_ai_critic），便于单项目启用 spec 安全变体而不改全局配置。

## [0.11.0] - 2026-03-01

### Added（新增）

- `references/spec_examples/ai_critic_min.yaml`：新增 `ai_critic` 最小闭环 spec 夹具，便于维护者快速跑通离线闭环。

### Changed（变更）

- `config.yaml`：版本升级至 `0.11.0`；规划输出文件名改为 `schematic-plan.md`（替代 `PLAN.md`，对齐 roadmap 的交付口径）。
- `scripts/plan_schematic.py`：默认不再在当前工作目录（CWD）写出 `schematic-plan.md`；如需额外复制到 CWD，使用 `--also-write-workspace-plan`（显式开关）。
- `scripts/plan_schematic.py`：规划阶段中间产物统一托管到 `output_dir/.nsfc-schematic/`，并自动创建 `.nsfc-schematic/.gitignore`，降低误提交运行历史的概率。
- `scripts/generate_schematic.py`：`.nsfc-schematic/.gitignore` 规则补齐 `/planning/`（与规划阶段一致），避免规划证据污染 `git status`。
- `README.md` / `SKILL.md`：补齐“评估-优化闭环（plateau）”与“AI 自主闭环（ai_critic）”可执行 runbook，并同步规划文件名与输出口径。

## [0.10.0] - 2026-02-28

### Added（新增）

- `scripts/routing.py`：升级为“单折线 + 双折线候选 + 代价函数”路由搜索，并支持 `edge_kind` 走廊偏好；新增 edge label 锚点选择与 bbox 估计工具（用于避障定位）。
- `scripts/evaluate_schematic.py` / `scripts/measure_schematic.py`：新增空间利用率度量与告警（content bbox margin/coverage），新增 edge label 压字检查（node/header occlusion）。
- `scripts/spec_parser.py`：新增显式布局识别（`explicit_layout` / `explicit_layout_ratio`），用于自动修复阶段避免破坏式膨胀。

### Changed（变更）

- `config.yaml`：版本升级至 `0.10.0`；默认关闭图内标题（`layout.title.enabled=false`）；新增 `layout.shape_policy`、`renderer.drawio_border_mode` 以及空间利用/标签净距阈值配置。
- `scripts/schematic_writer.py`：去除 draw.io `pageWidth/pageHeight` 硬最小值，严格对齐 spec 画布；edge label 写入 `mxGeometry offset`，降低压字风险。
- `scripts/render_schematic.py`：导出边框支持 adaptive 模式；内部渲染支持形状策略（uniform/semantic）与标签避障锚点。
- `scripts/generate_schematic.py`：auto-fix 改为“边标签优先修复 + 显式布局保守策略”；`config_local` 新增 `layout.font.edge_label_size` 白名单覆盖。
- `scripts/plan_schematic.py`：规划草案默认不写图内标题，并新增边标签长度/数量约束（防止规划阶段先天拥挤）。
- `README.md` / `SKILL.md`：同步更新标题策略、形状策略、自适应边框与配置说明。

## [0.9.0] - 2026-02-28

### Added（新增）

- `scripts/spec_parser.py`：补齐 spec v2 语义（`node.id` 可选稳定化、`edges.id/kind/route`、`group.node` 路径引用）。
- `scripts/schematic_writer.py`：每轮新增调试证据 `layout_debug.json` / `edge_debug.json`。
- `scripts/generate_schematic.py`：新增 `config_local.yaml` 实例级覆盖（白名单校验），支持单项目参数微调而不改全局 `config.yaml`。
- `scripts/generate_schematic.py`：新增 `ai_critic` 离线闭环工作区（`.nsfc-schematic/ai/`、`ai_pack_round_XX`、`ai_critic_request.md`、`ai_critic_response.yaml`）。

### Changed（变更）

- `config.yaml`：版本升级至 `0.9.0`，新增 `layout.auto_edges`（`minimal|off`）并明确 `stop_strategy=ai_critic` 为“宿主 AI 响应驱动”闭环。
- `scripts/render_schematic.py` / `scripts/evaluate_schematic.py` / `scripts/measure_schematic.py`：连线路由改为支持 per-edge `route`（`orthogonal|straight|auto`）并兼容 mixed routing。
- `scripts/generate_schematic.py`：候选提升时同步保留 `layout_debug.json`/`edge_debug.json`/`measurements.json`/`dimension_measurements.json` 到 `round_XX/`。
- `README.md` / `SKILL.md`：同步更新 spec v2、纠偏原则、ai_critic 闭环协议与调试产物说明。

## [0.8.6] - 2026-02-20

### Changed（变更）

- 默认启用纯 AI 规划：`config.yaml:planning.planning_mode=ai`，规划阶段不再要求/默认从模板库中单选 `template_ref`
- `config.yaml:layout.template_ref` 默认置空（高级选项；仅在用户明确要求“参考某个模板”时使用）
- `scripts/plan_schematic.py`：新增 `--mode template|ai`（默认取配置）；AI 模式输出 `plan_request.json/plan_request.md` 并在宿主 AI 写入 `PLAN.md + spec_draft.yaml` 后复跑校验
- 文档口径对齐：`SKILL.md`、`README.md`

## [0.8.5] - 2026-02-20

### Changed（变更）

- `references/models/`：新增一批规划阶段“视觉参考模板”，并将 `curated_*.png` 统一重命名为 `model-06..model-13`，与 `model-01..model-02` 命名体系对齐。
- `references/models/templates.yaml`：扩展模板索引（新增 `model-06..model-13`），保证新模板可被 `plan_schematic.py --template-ref model-xx` 直接选用并进入模型画廊/Contact Sheet 流程。
- `scripts/plan_schematic.py`：规划草案分组保留 `role` 字段，并在自检阶段优先按 `role=input/output` 识别输入/输出节点，避免分层模板（如 `数据层/应用层`）触发误报 P0。
- `README.md` / `SKILL.md`：同步说明“5 类常用骨架 + 多个 model-xx 视觉参考”的口径。

## [0.8.4] - 2026-02-20

### Changed（变更）

- `config.yaml`：默认画布比例从 A4 横版调整为更接近 MacBook 的 16:10（更适合屏幕审阅）。

## [0.8.3] - 2026-02-20

### Changed（变更）

- `config.yaml`：默认画布改为更接近 A4 横版比例，降低“过扁/过宽”观感风险。
- `config.yaml`：新增 `layout.canvas_fit`（可选自动“收缩到内容”）与 `layout.routing`（路由避让与障碍 padding）配置项，提升排版一致性与可读性。
- `scripts/schematic_writer.py`：分组容器改用 swimlane 渲染“统一标题栏”，改善长中文分组标题的观感与对齐一致性。

### Fixed（修复）

- `scripts/schematic_writer.py`：连线路由加入“分组标题栏”避让与更保守的障碍 padding，降低连线/标签遮挡节点与标题的概率。
- `scripts/spec_parser.py`：当用户显式给出超大画布时，可选按内容边界收缩画布，避免极端比例与大量空白。

## [0.8.2] - 2026-02-20

### Added（新增）

- `scripts/model_gallery.py`：新增“模型画廊”生成器（复制参考图 + 生成 contact sheet），用于规划阶段视觉选型。

### Changed（变更）

- `references/models/templates.yaml`：为模板补充可选 `file/simple_file`（其中 `simple_file` 为骨架/模式图），并升级模板库版本号。
- `scripts/plan_schematic.py`：规划阶段自动生成模型画廊（best-effort），并在 `PLAN.md` 中输出 contact sheet 与索引路径，便于“先看 skeleton 再选 template_ref”。
- `SKILL.md` / `README.md` / `references/plan_template.md`：补齐“视觉选型（skeleton/simple 优先）”说明与产物路径示例。

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
