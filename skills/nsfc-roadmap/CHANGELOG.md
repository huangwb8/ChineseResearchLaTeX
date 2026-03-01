# nsfc-roadmap - 变更日志

版本号以 `nsfc-roadmap/config.yaml:skill_info.version` 为单一真相来源。

## [Unreleased]

### Added（新增）

- （暂无）

### Changed（变更）

- （暂无）

## [0.11.0] - 2026-03-01

### Added（新增）

- 支持 Nano Banana / Gemini PNG-only 渲染模式：`generate_roadmap.py --renderer nano_banana`（仅当用户明确提出使用图片模型时启用）

## [0.10.1] - 2026-02-28

### Fixed（修复）

- 修复 draw.io 导出 PDF 可能被切成多页/拼页：`.drawio` 写入的 `pageWidth/pageHeight` 与 `renderer.canvas` 一致；PDF 导出强制 `--crop`，确保单页输出

## [0.10.0] - 2026-02-28

### Added（新增）

- spec v2 能力：节点可选 `box.id`（稳定 id）与顶层 `edges`（显式连线，优先复现）
- 新增布局模板 `packed-three-column`：按文本高度紧凑堆叠，中心列支持 main/output 堆叠，减少空白并为走线留空间
- 每轮输出调试文件：`round_XX/layout_debug.json` 与 `round_XX/edge_debug.json`（布局/连线诊断）
- 新增轻量测试闭环：`tests/实例辅助优化-v202602281042/`（PLAN/REPORT + spec v2 fixture）

### Changed（变更）

- draw.io 导出改为节点稳定 id + 连线策略升级：当 `spec.edges` 未提供时按 `config.yaml:layout.auto_edges` 自动连线，并受 `layout.edge_density_limit` 限制
- `config.yaml`：新增 `layout.auto_edges` 与 `layout.edge_density_limit`；layout.template 允许 `packed-three-column`
- 文档同步：`SKILL.md`、`README.md` 补齐 packed 模板与 spec v2/调试产物说明

## [0.9.1] - 2026-02-20

### Changed（变更）

- 默认启用纯 AI 规划：`config.yaml:planning.planning_mode` 由 `template` 改为 `ai`
- `scripts/plan_roadmap.py`（AI 规划模式）：不再要求/引导“必须选择 template_ref”；模型画廊仅用于学习结构与信息密度控制
- 文档口径对齐：`SKILL.md`、`README.md`

## [0.9.0] - 2026-02-20

### Added（新增）

- 视觉选型证据包：规划阶段自动生成“模型画廊”
  - `output_dir/.nsfc-roadmap/planning/models_contact_sheet.png`（contact sheet）
  - `output_dir/.nsfc-roadmap/planning/models/`（单张参考图拷贝）
  - `output_dir/.nsfc-roadmap/planning/models_index.yaml`（索引）

### Changed（变更）

- `references/models/templates.yaml` 精简为最小机器索引（仅保留 `id/file/family/render_family`），避免“硬编码叙事 token”
- `scripts/plan_roadmap.py`（AI 规划模式）：`plan_request.json/plan_request.md` 增补模型画廊路径，引导宿主 AI 先看图再选 `template_ref`
- `scripts/template_library.py`：模板库解析改为兼容“最小 schema”（`families`/叙事字段可省略）
- 文档同步：`references/models/README.md`、`README.md`、`skills/README.md`、`SKILL.md`、`skills/nsfc-roadmap/README.md`

### Fixed（修复）

- 修复 classic 布局生成 `.drawio` 时的崩溃：`scripts/render_roadmap.py` 将主线 anchor 节点写入逻辑移动到 draw.io 导出阶段，避免 `UnboundLocalError: drawio_nodes referenced before assignment`

## [0.8.2] - 2026-02-20

### Changed（变更）

- 重校准拥挤阈值（NSFC 信息密集型场景）：`config.yaml:evaluation.thresholds` 将 `crowded_density_p1` 调整为 0.55，并显式加入 `crowded_density_p0=0.65`
- 固定画布高度约束：`config.yaml:evaluation.exploration.jitter_px.height_px` 设为 0，避免在优化循环中通过“拉长画布”掩盖内容拥挤问题
- 修正多轮优化方向：`scripts/generate_roadmap.py` 的自动修复逻辑不再用“缩字号/扩画布/缩间距”来应对拥挤；仅在 overflow 时减字号，在字号偏小时增字号，并避免密度驱动可读性下降
- `scripts/evaluate_roadmap.py` / `scripts/evaluate_dimension.py`：对齐拥挤提示文案与 P0/P1 判定口径，强调“优先精简内容/合并节点”，避免误导改渲染参数
- ai_critic 协议增强：request 增加“密度/字号/配色”纠偏约束；`config_local.color_scheme.name` 限制为 `{academic-blue, tint-layered}`，减少误切 `outline-print`
- 文档同步：`SKILL.md`、`README.md` 增补纠偏原则与常见问题口径

## [0.8.1] - 2026-02-19

### Changed（变更）

- 规划证据提取增强：`scripts/extract_proposal.py` 在提供 `proposal_path` 时同时提取“立项依据 + 研究内容/技术路线”，写入 `plan_request.json` 供宿主 AI 更全面规划
- `scripts/plan_roadmap.py`：AI 规划协议文案对齐“立项依据 + 研究内容/技术路线”的阶段一工作流；模板列表补充 `render_family`
- 模板库对齐“概念 family vs 可落地骨架”：`references/models/templates.yaml` 增加可选字段 `render_family`，并在解析/选择中用于稳定渲染回退
- 模板文档同步更新：`references/models/README.md` 与 `README.md` 补齐 `model-07..model-10` 与新增 family 说明（含近似落地提示）

## [0.8.0] - 2026-02-15

### Added（新增）

- 新增纯度量采集层：`scripts/measure_roadmap.py`（密度/溢出/阶段平衡/连线/字体等，**不做 P0/P1/P2 判定**）
- 新增维度度量采集：`scripts/measure_dimension.py`（structure/visual/readability 三维度度量，供宿主 AI 语义解读）
- 新增规划提取器：`scripts/extract_proposal.py`（从 tex/md/纯文本抽取标题/段落/关键词，供 AI 规划协议使用）
- `scripts/plan_roadmap.py`：新增 `--mode template|ai`，并支持 `config.yaml:planning.planning_mode`
- `config.yaml`：新增 `evaluation.evaluation_mode` 与 `planning.planning_mode`（默认分别为 `heuristic` / `template`，保持向后兼容）

### Changed（变更）

- `scripts/evaluate_roadmap.py`：重构为“度量采集（measure_*）+ 启发式回退判定”，并在输出中附带 `measurements` 字段
- `scripts/generate_roadmap.py`：在 `evaluation_mode=ai`（或 `stop_strategy=ai_critic`）时导出 `round_XX/measurements.json` 与 `round_XX/dimension_measurements.json`，并打包进 AI 证据包
- `scripts/generate_roadmap.py`：`ai_critic_request.md` 补充度量文件提示，便于宿主 AI 结合“纯度量证据”做判断与决策

## [0.7.0] - 2026-02-15

### Added（新增）

- 新增“AI 自主加强”优化计划：`plans/ai自主加强-优化-v202602150803.md`（将洞见提炼/规划/视觉理解/停止决策更多交给宿主 AI，脚本侧提供证据包与可复现协议）
- `scripts/generate_roadmap.py`：落地 `stop_strategy=ai_critic` 自主闭环：每轮生成 `ai_critic_request.md` 并暂停等待 `ai_critic_response.yaml`（不在脚本内调用外部模型 API）
- `scripts/generate_roadmap.py`：新增 AI 证据包导出（`output_dir/.nsfc-roadmap/ai/{run_dir}/ai_pack_round_XX/`），包含 `roadmap.png/spec_latest.yaml/config_used.yaml/evaluation.json/critique_*.json`
- `scripts/generate_roadmap.py`：新增 `config_local.yaml` 叠加机制（白名单字段覆盖），支持实例级启用 `evaluation.stop_strategy` 与局部图参数覆盖
- 新增轻量测试闭环：`tests/ai自主加强-优化-v202602150803/`（PLAN/REPORT + 协议跑通验证）

### Changed（变更）

- `scripts/render_roadmap.py`：支持 spec box 可选字段 `role`，当存在 `role=main` 时优先作为主线盒子，减少启发式漂移
- `SKILL.md`/`README.md`：补充 ai_critic request/response 协议、证据包结构与 `config_local.yaml` 用法

## [0.6.0] - 2026-02-15

### Added（新增）

- 默认生成主线连线：`.drawio` 内置 `Phase1 → Phase2 → …` 主链 edges（classic/three-column/layered-pipeline 均适用）
- 内部渲染兜底增加主线箭头（PNG/SVG），无 draw.io CLI 时仍可直接看出主流向
- spec 新增可选字段 `phase_header_override`：用于阶段标题条补充短标题摘要（保持向后兼容）
- 新增配色预设：`outline-print`（白底描边）与 `tint-layered`（低饱和浅填充）
- 新增轻量测试闭环：`tests/实例辅助优化-v202602150013/`（PLAN/REPORT + fixture）
- 新增针对 `技术路线图-v2` 实例的“成品感/主线连线/模板落地”优化计划：`plans/实例辅助优化-v202602150013.md`

### Changed（变更）

- `scripts/render_roadmap.py`：three-column/layered-pipeline 的 main box 选择与高度策略改为“按内容自适应”，避免短标题被拉伸成大框导致极端留白
- `scripts/generate_roadmap.py`/`scripts/plan_roadmap.py`：tex hints 在 three-column/layered-pipeline 下写入 `phase_header_override`，避免注入短 `critical` box 破坏主线骨架
- `scripts/evaluate_roadmap.py`：当 `phases>=2 且 edges=0` 时输出至少 P1 缺陷（主线连线缺失）
- `README.md`：补充主线箭头、配色预设与 `phase_header_override` 用法说明

## [0.5.0] - 2026-02-14

### Added（新增）

- 新增结构化模板库（单一真相来源）：`references/models/templates.yaml`，沉淀模板 id/family 与可复用 token
- 新增人类可读模板索引：`references/models/README.md`，用于快速挑选模板与理解“参考约束”
- 新增模板库读取脚本：`scripts/template_library.py`，支持 `template_ref → family` 的稳定映射
- 新增可选布局模板：支持 `classic/three-column/layered-pipeline` 两类模板家族骨架渲染（不追求像素级复刻）

### Changed（变更）

- `SKILL.md`：规划阶段明确要求读取模板库并在 `roadmap-plan.md` 写出 `template_ref + 选用原因 + 落地约束清单`
- `config.yaml`：扩展 `layout.template` 允许值，并新增 `layout.template_ref`（具体模板 id）
- `scripts/spec.py`：`RoadmapSpec` 增加可选字段 `layout_template/template_ref`（保持兼容）
- `scripts/plan_roadmap.py`：新增 `--template/--template-ref`，并在 `roadmap-plan.md` 中输出模板参考信息
- `scripts/render_roadmap.py`：按 `spec/config` 选择渲染策略，新增 three-column 与 layered-pipeline 两类布局骨架
- `README.md`：补充“模板风格选择”的用户使用说明

## [0.4.0] - 2026-02-14

### Added（新增）

- 新增多维度批判性自检：`structure/visual/readability` 三维度并行评估；每轮写入 `critique_*.json` 并汇总进 `evaluation.json`
- 新增维度评估脚本 `scripts/evaluate_dimension.py`：支持按维度单独输出结构化 JSON

### Changed（变更）

- `scripts/generate_roadmap.py`：集成 `evaluation.multi_round_self_check`；评分加入自检缺陷惩罚并在报告中记录 base/penalty
- `scripts/render_roadmap.py` / `scripts/drawio_writer.py`：draw.io 导出样式对齐配置：box/bar 的 `fontColor` 使用 `color_scheme.text` 与 `layout.phase_bar.text_color`
- `config.yaml`：新增 `evaluation.multi_round_self_check` 配置节（默认启用）
- `SKILL.md`/`README.md`：补充多维度自检产物与配置说明

## [0.3.0] - 2026-02-14

### Added（新增）

- 新增规划阶段脚本 `scripts/plan_roadmap.py`：输出 `roadmap-plan.md`（交付）+ `spec_draft.yaml`（中间产物）
- 新增默认 PDF 交付：优先使用 draw.io CLI 导出；无 CLI 时降级为 PNG→PDF（可控开关见 `config.yaml:renderer.pdf`）
- 新增输出文件管理：交付根目录仅保留交付文件 + `.nsfc-roadmap/`；runs 历史与中间产物统一收纳到隐藏目录，并自动迁移 legacy 残留
- 新增“标题/notes 默认不落图”开关：`config.yaml:layout.title.enabled=false`、`config.yaml:layout.notes.enabled=false`
- 新增轻量测试闭环：`tests/实例辅助优化-v202602141018/`（PLAN/REPORT + 最小 fixture）

### Changed（变更）

- 默认画布比例调整为更贴近标书排版：高度约为 A4 的 2/3（`renderer.canvas.height_px=2263`）
- `generate_roadmap.py`：支持 `--output-dir` 默认值（取 `config.yaml:output.dirname`）；新增 `--config`；runs 写入 `.nsfc-roadmap/runs/`
- `render_roadmap.py`：当检测到 draw.io CLI 时，优先从 `.drawio` 统一导出 PNG/SVG/PDF，确保交付口径一致
- `evaluate_roadmap.py`：对齐 title/notes 开关后的布局口径（预留空间一致）
- `spec.py`：默认 spec 不再写入 `notes`（避免备注性长句落图；建议写入 `roadmap-plan.md` 的“备注”区）

### Fixed（修复）

- 修复“notes 启用时可能与主图区域重叠”的布局口径问题（启用时预留底部空间）
- 新增规划阶段脚本 `scripts/plan_roadmap.py`，输出 `roadmap-plan.md` 与 `spec_draft.yaml`
- 新增隐藏中间产物机制：输出根目录仅保留交付文件与 `roadmap-plan.md`
- 默认启用 PDF 交付（无 draw.io CLI 时降级为 PNG→PDF）

### Changed（变更）

- 默认画布高度调整为 A4 高度的 2/3 比例（宽度不变）
- 标题/notes 默认不落图（可通过 `config.yaml:layout.*.enabled` 控制）
- 交付/中间产物结构对齐 `.nsfc-roadmap/` 目录规范
- README/SKILL 输出结构与流程更新（规划→生成→优化）

### Fixed（修复）

- draw.io CLI 可用时优先导出 PNG/SVG/PDF，提高交付一致性
- 评估器对 title/notes 关闭场景的高度计算一致性
## [0.2.0] - 2026-02-13

### Added（新增）

- 增加 run 隔离机制：每次运行输出到 `run_YYYYMMDDHHMMSS/`，避免 `round_XX/` 历史残留污染
- 增加 drawio XML 预检验：非法 XML 直接阻断后续评估与导出，并给出可读错误信息
- 增加 `stop_strategy: plateau` 停止策略（基于 PNG 哈希不变 + 分数提升阈值）
- 增加探索机制 `evaluation.exploration`：对边距/间距/画布高度做确定性抖动，帮助跳出局部最优
- 评估器增强：Defect 增加 `dimension` 字段，并新增基于 PNG 像素密度的视觉评估与启发式/视觉加权分数
- 增加 draw.io CLI 检测与安装指引：在报告中输出 renderer 模式与安装提示

### Changed（变更）

- `config.yaml`：对齐 `evaluation.thresholds/weights/exploration/plateau` 结构；`early_stop` 默认关闭（保留兼容）
- `optimization_report.md`：每轮增加 `png_sha256`，并在平台期停止时输出 stop reason

## [0.1.1] - 2026-02-11

### Added（新增）

- 初始化 `nsfc-roadmap` 技能骨架（SKILL.md/config.yaml/scripts/assets/README）
- 新增确定性渲染链路：`spec.yaml` → `roadmap.png/.svg/.drawio`
- 新增确定性启发式评估：每轮输出 `evaluation.json`，并在输出根目录导出 best round 的 `evaluation_best.json`
- 新增 best round 复现证据：输出根目录导出 `config_used_best.yaml`
- 新增 `tests/init` 轻量测试闭环（PLAN/REPORT + 推荐证据目录）

### Changed（变更）

- `generate_roadmap.py`：支持 `evaluation.early_stop`（满足阈值后提前停止）
- `config.yaml`：补充跨平台字体候选（macOS/Linux/Windows）

### Fixed（修复）

- 修复 LaTeX `\\itemtitlefont{...}` 标题抽取在嵌套花括号场景被截断的问题
- YAML 读取与输入路径做 fail-fast（错误信息更明确）
