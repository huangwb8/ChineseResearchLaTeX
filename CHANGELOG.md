# Changelog

本文件记录项目的修改历史，方便回顾项目的优化过程。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [Unreleased]

### Added（新增）

- **scripts/pack_release.py**：新增 Release 打包脚本，自动为 `projects/` 下各子项目生成 zip 并可选上传到 GitHub Release（`--upload`）
- **nsfc-ref-alignment v0.1.1**：新增 NSFC 标书“引用-参考文献”一致性核查技能（只读 + 报告制）
  - `skills/nsfc-ref-alignment/scripts/run_ref_alignment.py`：抽取 `\cite{}` 等引用并核对 `.bib` 完整性（缺失 bibkey/重复条目/字段缺失/DOI 格式），中间产物隔离在 `.nsfc-ref-alignment/run_{timestamp}/`
  - 默认仅输出审核报告（写入 `./references`），不直接修改标书正文或 `.bib`

### Changed（变更）

- **nsfc-schematic v0.13.1 → v0.14.0**：将 `evaluation.stop_strategy` 默认值从 `plateau` 改为 `ai_critic`，AI 闭环评价成为开箱即用的默认模式；如需无人值守自动收敛，可在 `config_local.yaml` 覆盖 `stop_strategy: plateau`
- **nsfc-schematic v0.14.0 → v0.14.1**：增强 Nano Banana / Gemini PNG-only 模式的 prompt 字体与排版硬约束（禁止扭曲/旋转/艺术字；建议黑字+白底标签框），降低图片中文字“扭曲/不可读”风险
- **nsfc-schematic v0.14.1 → v0.14.2**：Nano Banana / Gemini PNG-only 模式固定输出 4K 分辨率（长边>=3840px；按画布比例缩放并在必要时补白），并将导出分辨率检查口径改为“长边>=3840px”，避免与 spec 画布尺寸不一致造成误报
- **nsfc-schematic v0.14.2 → v0.14.3**：Nano Banana + `ai_critic` 风格延续与配色建议增强
  - `ai_critic_response.yaml`：新增 `style_continuity`（为 true 时下一轮把上一轮 PNG 作为参考图传入 Gemini，保证风格连续）与 `nano_banana_color_advice`（自动拼入下一轮 prompt）
  - `skills/nsfc-schematic/scripts/nano_banana_client.py`：支持 `reference_png` 输入，并在 debug request 中省略 base64
  - `skills/nsfc-schematic/scripts/generate_schematic.py`：证据包携带 `nano_banana_prompt.md`，并在风格延续时自动附加“风格延续”提示段落
- **nsfc-schematic v0.9.0 → v0.10.0**：实例辅助优化（标题策略、标签可读性、空间利用率、形状统一）
  - `skills/nsfc-schematic/config.yaml`：默认关闭图内标题；新增 `layout.shape_policy`、`renderer.drawio_border_mode` 及空间利用/标签净距阈值
  - `skills/nsfc-schematic/scripts/routing.py` / `schematic_writer.py` / `render_schematic.py`：路由升级为双折线候选+代价函数，edge label 增加避障锚点与 offset，导出边框支持 adaptive
  - `skills/nsfc-schematic/scripts/evaluate_schematic.py` / `measure_schematic.py`：新增内容 bbox 覆盖率/边距检查与 label 压字检查
  - `skills/nsfc-schematic/scripts/generate_schematic.py`：auto-fix 改为“边标签优先、显式布局保守”，并放开 `config_local.layout.font.edge_label_size`
  - `skills/nsfc-schematic/scripts/plan_schematic.py`：规划阶段默认无图内标题，并限制边标签长度/数量
  - 文档同步：`skills/nsfc-schematic/README.md`、`skills/nsfc-schematic/SKILL.md`、`skills/nsfc-schematic/CHANGELOG.md`、`README.md`、`skills/README.md`

- **nsfc-schematic v0.10.0 → v0.11.0**：规划阶段“中间文件托管”一致性 + 自优化闭环显式化
  - `skills/nsfc-schematic/scripts/plan_schematic.py`：默认不再在 CWD 写出 `schematic-plan.md`；如需额外复制到 CWD，使用 `--also-write-workspace-plan`
  - `skills/nsfc-schematic/config.yaml`：规划输出文件名统一为 `schematic-plan.md`（替代 `PLAN.md`）
  - `skills/nsfc-schematic/scripts/plan_schematic.py` / `skills/nsfc-schematic/scripts/generate_schematic.py`：自动创建 `output_dir/.nsfc-schematic/.gitignore`（忽略 `/planning/` + `/runs/`），中间产物统一托管到 `.nsfc-schematic/`
  - `skills/nsfc-schematic/SKILL.md` / `skills/nsfc-schematic/README.md`：补齐 “plateau 自动收敛” 与 “ai_critic 离线闭环” 的可执行 runbook
  - `skills/nsfc-schematic/references/spec_examples/ai_critic_min.yaml`：新增最小闭环 spec 夹具

- **nsfc-schematic v0.11.0 → v0.12.0**：P2 落地（auto-fix 可解释性 + spec 安全变体 + 显式布局降级策略）
  - `skills/nsfc-schematic/config.yaml`：新增 `evaluation.spec_variants`（默认关闭），可对过长 label 做 wrap/truncate/candidates（仅改 label，不改 id/edges）
  - `skills/nsfc-schematic/scripts/generate_schematic.py`：`config_local.yaml` 白名单放开 `evaluation.spec_variants`，支持单项目启用
  - `skills/nsfc-schematic/scripts/generate_schematic.py`：`optimization_report.md` 每轮输出“下一轮 auto-fix 配置 delta”，并在显式布局比例较高时更保守修复/引导 ai_critic

- **nsfc-schematic v0.12.0 → v0.12.1**：实例辅助优化（PDF 单页稳定 + 显式画布 fit-to-canvas + 回归夹具）
  - `skills/nsfc-schematic/scripts/render_schematic.py`：PDF 导出启用 `--crop` 并提供兼容回退；SVG/PDF 固定 `--width/--height`；无 draw.io CLI 时 PDF 自动降级为 PNG→PDF
  - `skills/nsfc-schematic/scripts/spec_parser.py`：显式 `schematic.canvas` 时不再自动扩画布（包括 `auto_expand_canvas`/`canvas_fit` 扩张路径），并在自动布局中基于可用宽度自动降列（支持 `cols=1`）
  - `skills/nsfc-schematic/scripts/generate_schematic.py`：报告 Final 段落补齐 `schematic.pdf`；`config_local.color_scheme.name` 白名单对齐内置配色
  - `skills/nsfc-schematic/references/spec_examples/seqccs_min.yaml`：新增最小回归夹具

- **nsfc-schematic v0.12.1 → v0.12.2**：健壮性修复与跨平台 draw.io CLI 路径支持
  - `skills/nsfc-schematic/scripts/generate_schematic.py`：修复 ai_critic 响应版本校验分支的 `NameError` 风险；修复 wrap label 的空白检测正则；TEX 术语抽取数量改为读取 `planning.extraction.max_terms`
  - `skills/nsfc-schematic/scripts/render_schematic.py`：新增 `renderer.drawio.cli_path` 支持，并在无效值时降级为 warn+自动检测；draw.io CLI 路径下的 PNG 尺寸校正缺少 Pillow 时降级跳过（不阻断主流程）
  - `skills/nsfc-schematic/scripts/generate_schematic.py`：`config_local.yaml` 白名单放开 `renderer.drawio.cli_path`（便于单项目覆盖）
  - 文档同步：`skills/nsfc-schematic/README.md`、`skills/nsfc-schematic/SKILL.md`、`skills/nsfc-schematic/CHANGELOG.md`、`skills/nsfc-schematic/config.yaml`

- **nsfc-schematic README.md**：新增「Gemini API 配置」章节，说明 Nano Banana 模式所需的环境变量（`GEMINI_BASE_URL`、`GEMINI_API`、`GEMINI_MODEL`）及连通性验证方法

- **nsfc-schematic v0.12.2 → v0.12.3**：parallel-vibe 多方案并行对比（用于“开很多 run 反复优化”）
  - `skills/nsfc-schematic/README.md` / `skills/nsfc-schematic/SKILL.md`：补齐 parallel-vibe 并行优化 runbook，并推荐用 `--run-tag` 标记不同策略来源
  - `skills/nsfc-schematic/scripts/generate_schematic.py`：新增 `--run-tag`；扩展 `config_local.yaml` 白名单，放开 `renderer.internal_routing`、`layout.auto.*` 与 `evaluation.exploration.*`（便于线程级参数对比而不改全局配置）
  - `skills/nsfc-schematic/config.yaml` / `skills/nsfc-schematic/CHANGELOG.md`：版本号更新至 `0.12.3`（单一真相来源）

- **nsfc-schematic v0.12.3 → v0.13.0**：新增 Nano Banana/Gemini PNG-only 原理图模式（仅当用户主动要求）
  - `skills/nsfc-schematic/scripts/generate_schematic.py`：新增 `--renderer`（默认 drawio；`nano_banana` 模式只交付 PNG，并避免每轮多候选导致成本乘法）

- **nsfc-schematic v0.13.0 → v0.13.1**：自动布局可读性小幅提升（居中 + 标签字号）
  - `skills/nsfc-schematic/scripts/spec_parser.py`：新增 `layout.canvas_fit.center_content`（默认 true），自动布局下将内容包围盒居中，减少单侧大留白/视觉重心偏移
  - `skills/nsfc-schematic/config.yaml`：默认将 `layout.font.edge_label_size` 从 22 调整为 24

- **nsfc-roadmap v0.10.1 → v0.11.0**：新增 Nano Banana/Gemini PNG-only 技术路线图模式（仅当用户主动要求）
  - `skills/nsfc-roadmap/scripts/generate_roadmap.py`：新增 `--renderer`（默认 drawio；`nano_banana` 模式只交付 PNG）
  - `skills/nsfc-schematic/scripts/nano_banana_check.py`：Gemini 配置连通性检查
  - `skills/nsfc-schematic/scripts/nano_banana_generate_png.py`：独立的 PNG 生成器（便于调试）
  - 文档同步：`skills/nsfc-schematic/README.md`、`skills/nsfc-schematic/SKILL.md`、`skills/nsfc-schematic/CHANGELOG.md`、`skills/nsfc-schematic/config.yaml`

- **nsfc-roadmap v0.11.0 → v0.11.1**：Nano Banana + `ai_critic` 组合增强（宿主 AI 主导读图评估 + 可控 Gemini prompt）
  - `skills/nsfc-roadmap/scripts/generate_roadmap.py`：`ai_critic_response.yaml` 支持 `nano_banana_prompt`（full/patch）与 `action: nano_banana_prompt_only`；证据包新增 `nano_banana_prompt.md`
  - 文档同步：`skills/nsfc-roadmap/README.md`、`skills/nsfc-roadmap/SKILL.md`、`skills/nsfc-roadmap/CHANGELOG.md`、`skills/nsfc-roadmap/config.yaml`

- **nsfc-roadmap v0.11.1 → v0.11.2**：Nano Banana（Gemini PNG-only）模式文字可读性优化（印刷体字体约束 + 禁扭曲）+ 默认更偏好 4K 输出
  - `skills/nsfc-roadmap/scripts/generate_roadmap.py`：确定性 prompt 增强（字体/排版强约束，避免扭曲/乱码），并提示 `[kind]` 标签不应渲染为节点文字
  - `skills/nsfc-roadmap/scripts/nano_banana_client.py`：图像尺寸选择更倾向 `IMAGE_SIZE_4K`（提升 A4 缩印可读性）
- **nsfc-roadmap v0.11.2 → v0.11.3**：Nano Banana（Gemini PNG-only）模式固定输出 4K 分辨率（长边>=3840px；按画布比例缩放并在必要时补白），不再受 spec/画布尺寸影响
  - 文档同步：`skills/nsfc-roadmap/README.md`、`skills/nsfc-roadmap/SKILL.md`、`skills/nsfc-roadmap/CHANGELOG.md`、`skills/nsfc-roadmap/config.yaml`
- **nsfc-roadmap v0.11.3 → v0.11.4**：Nano Banana + `ai_critic` 风格延续与配色建议增强
  - `ai_critic_response.yaml`：新增 `style_continuity`（为 true 时下一轮把上一轮 PNG 作为参考图传入 Gemini，保证风格连续）与 `nano_banana_color_advice`（自动拼入下一轮 prompt）
  - `skills/nsfc-roadmap/scripts/nano_banana_client.py`：支持 `reference_png` 输入，并在 debug request 中省略 base64
  - `skills/nsfc-roadmap/scripts/generate_roadmap.py`：在风格延续时自动附加“风格延续”提示段落，并将上一轮 PNG 作为参考图传入

- **.gitignore**：新增忽略规则 `**/.nsfc-ref-alignment/`，避免运行 nsfc-ref-alignment 时产生的中间产物污染 `git status`
- **projects/NSFC_{General,Local,Young}**：enumerate 列表换行后的续行增加 2 个中文字符缩进；中文字体伪粗体参数 `AutoFakeBold=3` 调整为 `AutoFakeBold=5`
- **projects/NSFC_{General,Local,Young}/extraTex/1.1.立项依据.tex**：将正文中“括号序号罗列”自然改为 `enumerate` 列表，并用 `\ssssubtitle{}` 作为列表标签示例，避免用户不知道可用
- **projects/NSFC_{General,Local,Young}/.vscode/settings.json**：优化 LaTeX Workshop 编译链路，强制将所有中间文件输出到 `.latex-cache/`，并在编译结束后复制 `main.pdf` 到项目根目录（根目录不再残留 `.aux/.log/.xdv/...` 等产物）
- **projects/NSFC_{General,Local,Young}/.vscode/settings.json**：LaTeX Workshop 的 `xelatex/bibtex` 调用改为通过项目内 `code/tex-tool.sh` 解析可执行文件路径，降低 VS Code 未继承 PATH（尤其 macOS Finder 启动）导致的“找不到 xelatex/bibtex”概率
- **AGENTS.md**：Release 发布流程步骤 4/5 合并，改为引用 `scripts/pack_release.py`，消除硬编码描述
- **AGENTS.md**：Release 发布流程新增步骤 5「发布微信动态」，规范发布后的社区通知格式（100–200 字，含项目名、版本号、更新亮点、Release 地址）
- **AGENTS.md**：新增「系统 Skill 保护」规则，禁止直接修改系统级 Skill（如 `~/.claude/skills/`、`~/.codex/skills/`），项目个性化需求应在项目目录内实现
- **nsfc-humanization 0.1.3 → 0.2.0**：补齐列表/图表标题覆盖并提升输出自检能力
  - `skills/nsfc-humanization/SKILL.md`：明确 `itemize/enumerate` 与 `\item` 的结构保护规则；将 `\caption{...}` 纳入可编辑自然语言范围；新增风格自评（最多 1 轮回修）
  - `skills/nsfc-humanization/references/machine-patterns.md`：扩充机器味模式库与对比示例（模板句式堆叠、被动语态滥用、数字罗列无解读、目标/内容混同等）
  - `skills/nsfc-humanization/config.yaml` / `skills/nsfc-humanization/README.md`：版本号更新至 0.2.0（单一真相来源）
- **nsfc-humanization 0.2.0 → 0.4.0**：补齐章节/领域/强度/一致性机制，并提供可核查输出
  - `skills/nsfc-humanization/SKILL.md`：新增 `section_type`/`field`/`strength`/`output_mode`/`self_eval_rounds`；支持 `diagnosis_only`；支持“变更摘要”与 STYLE_CARD（跨段落一致性）
  - `skills/nsfc-humanization/README.md`：补充参数用法与 STYLE_CARD 工作流示例
  - `skills/nsfc-humanization/references/machine-patterns.md`：补充 `field` 的领域表达偏好提示
  - `skills/nsfc-humanization/config.yaml` / `skills/nsfc-humanization/CHANGELOG.md`：版本号更新至 0.4.0（单一真相来源）
- **nsfc-code 0.1.6 → 1.0.0**：标记为正式稳定版本（`config.yaml` 版本号更新）
- **nsfc-abstract 0.3.1 → 1.0.0**：标记为正式稳定版本（`config.yaml` 版本号更新）
- **nsfc-justification-writer 0.7.9 → 1.0.0**：标记为正式稳定版本（`config.yaml` 版本号更新）
- **nsfc-research-content-writer 0.2.3 → 1.0.0**：标记为正式稳定版本（`config.yaml` 版本号更新；新增 `CHANGELOG.md`）
- **nsfc-qc 0.2.1 → 1.0.0**：标记为正式稳定版本（`config.yaml` 版本号更新）
- **nsfc-reviewers 0.5.0 → 1.0.0**：标记为正式稳定版本（`config.yaml` 版本号更新）
- **nsfc-humanization 0.4.0 → 1.0.0**：标记为正式稳定版本（`config.yaml` 版本号更新）
- **get-review-theme**：已为 v1.0.0 稳定版，无需升级
- **nsfc-code 0.1.5 → 0.1.6**：修复脚本/文档口径不一致与工作区回灌风险
  - `skills/nsfc-code/scripts/nsfc_code_rank.py`：新增 `--output-dir`（与 `SKILL.md` 示例对齐），并跳过 `.nsfc-code/`；TOML 解析优先用 `tomllib`（Python 3.11+）
  - `skills/nsfc-code/SKILL.md`：修复 shell 代码块弯引号；`nsfc_code_new_report.py` 示例补齐 `--ts "${TS}"`
  - `skills/nsfc-code/scripts/validate_skill.py`：smoke 校验改为 JSON 结构解析并覆盖 `--output-dir`
  - 文档口径对齐：`README.md` / `skills/README.md` / `Prompts.md`
- **nsfc-roadmap 0.9.1 → 0.10.0**：补齐 spec v2（稳定 id + 显式 edges）与紧凑布局能力，逼近 draw.io 上限
  - `skills/nsfc-roadmap/scripts/spec.py`：新增 `box.id`、`edges`、`size_hint/layout_hint/style` 等可选字段（保持向后兼容）
  - `skills/nsfc-roadmap/scripts/render_roadmap.py`：新增 `packed-three-column` 渲染器；draw.io 导出升级为稳定节点 id + 显式/自动连线；每轮输出 `layout_debug.json`/`edge_debug.json`
  - `skills/nsfc-roadmap/config.yaml`：新增 `layout.auto_edges` 与 `layout.edge_density_limit`，并允许 `layout.template=packed-three-column`
  - 新增轻量测试闭环：`skills/nsfc-roadmap/tests/实例辅助优化-v202602281042/`（PLAN/REPORT + spec v2 fixture）
- **nsfc-roadmap 0.10.0 → 0.10.1**：修复 draw.io 导出 PDF 可能被切成多页/拼页（单页输出更稳定）
  - `.drawio` 写入的 `pageWidth/pageHeight` 与 `renderer.canvas` 一致；PDF 导出强制 `--crop`
- **nsfc-schematic 0.8.6 → 0.9.0**：对齐 roadmap 核心协议（spec v2 + 调试产物 + ai_critic 闭环 + 实例级配置）
  - `skills/nsfc-schematic/scripts/spec_parser.py`：支持 `node.id` 可选稳定化与显式 `edges.id/kind/route`（含 `group.node` 路径引用）
  - `skills/nsfc-schematic/scripts/schematic_writer.py`：每轮输出 `layout_debug.json` / `edge_debug.json`
  - `skills/nsfc-schematic/scripts/generate_schematic.py`：新增 `.nsfc-schematic/ai/` 离线闭环（`ai_pack_round_XX`、`ai_critic_request.md`、`ai_critic_response.yaml`）与 `config_local.yaml` 白名单覆盖
  - 文档同步：`skills/nsfc-schematic/SKILL.md`、`skills/nsfc-schematic/README.md`、`skills/nsfc-schematic/CHANGELOG.md`

---

## [v3.2.5] - 2026-02-22

### Added（新增）

- **nsfc-humanization v0.1.0**：新增 NSFC 标书去"机器味"润色技能
  - 支持纯文本和 LaTeX 混合文本
  - 硬性约束：格式零修改、语义零损失、只润色文字
  - 包含"机器味"识别清单与"资深专家"风格模仿规范

---

## [v3.2.4] - 2026-02-22

### Changed（变更）

- **nsfc-qc v0.2.0 → v0.2.1**：新增术语一致性检查
  - `nsfc_qc_precheck.py`：新增 `_detect_terminology_consistency()` 启发式检测英文术语大小写/连字符不一致，输出 `terminology_issues.csv` 与 `terminology_issues_summary.json`
  - `run_parallel_qc.py`：术语文件纳入 snapshot 证据包，thread prompt 新增"术语一致性（必检）"指令
  - `SKILL.md`：术语一致性提升为独立必检项（第 6 项），原"其它 QC"降为第 7 项

---

## [v3.2.3] - 2026-01-24
  - 通过宿主 AI 的语义理解逐条核查引用是否与文献内容吻合
  - 只在发现致命性引用错误时对"包含引用的句子"做最小化改写
  - 支持 LaTeX、Markdown、Word 多格式文档
  - 完美复用 systematic-literature-review 的 PDF/Word 渲染流程
  - 错误优先级分级：P0（must_fix）、P1（warn_only）、P2（skip）

### Changed（变更）

- **systematic-literature-review v1.0.0 → v1.0.1**：Bug 修复与功能增强
  - 新增 BibTeX 导出的 `abstract` 字段支持
  - 修复 argparse help 文本中 `%` 未转义导致的崩溃问题
  - 修复 DOI 链接显示与 LaTeX 编译环境问题

### Fixed（修复）

- 修复 systematic-literature-review 中 argparse help 文本 `%` 未转义导致程序崩溃
- 修复 systematic-literature-review 中 DOI 链接显示问题，确保 LaTeX 编译环境兼容性

### Updated（文档更新）

- 更新 [README.md](README.md)：技能表格新增 check-review-alignment（v1.0.2），更新 systematic-literature-review 版本号至 v1.0.1
- 更新 [skills/README.md](skills/README.md)：新增 check-review-alignment 完整技能说明（功能、使用场景、Prompt 模板、技能特点、核心原则），调整后续技能编号（8→9，9→10，10→11）

---

## [Unreleased]

### Added（新增）

- **nsfc-code v0.1.2**：新增 NSFC 申请代码推荐技能（只读）
  - 读取标书正文内容，参考 `skills/nsfc-code/references/nsfc_code_recommend.toml`
  - 输出 5 组推荐（申请代码1=主代码、申请代码2=次代码）及理由，写入 `NSFC-CODE-vYYYYMMDDHHmm.md`
  - 提供候选粗排脚本 `skills/nsfc-code/scripts/nsfc_code_rank.py`（支持 `--prefix` 降噪、避免 `NSFC-*` 报告回灌）
  - 提供报告骨架脚本 `skills/nsfc-code/scripts/nsfc_code_new_report.py`（固定结构 + 时间戳，降低手误）

### Changed（变更）

- **nsfc-humanization 0.1.0 → 0.1.2**：补齐结构保护规则与最小改动策略，修正示例避免“新增信息”，并增加提示词注入防护
  - `skills/nsfc-humanization/SKILL.md`：新增 YAML frontmatter；新增“结构保护与可编辑范围”“强度控制”“结构/语义自检”；将“不确定性表达”限定为“仅原文已包含时才允许更自然表达”
  - `skills/nsfc-humanization/SKILL.md`：新增提示词注入防护规则，并补充“整篇标书按段落/小节分批输入”的建议
  - `skills/nsfc-humanization/references/machine-patterns.md`：修正会引入新场景/新实体的示例；新增 LaTeX token（`\cite/\ref/\eqref/数学模式`）保留示例
  - `skills/nsfc-humanization/config.yaml`：版本号更新至 0.1.2（单一真相来源）
  - `skills/nsfc-humanization/CHANGELOG.md`、`skills/nsfc-humanization/README.md`：同步版本号与变更记录（README 补齐推荐用法与 FAQ）
  - `README.md`：技能版本表同步更新（先到 v0.1.2，后续更新见 0.1.3 条目）

- **nsfc-humanization 0.1.2 → 0.1.3**：将“括号嵌套括号 + 分号罗列（数据来源/规模）”纳入机器味识别与高优先级改写策略
  - `skills/nsfc-humanization/SKILL.md`：新增“括号嵌套与信息堆砌”识别项，并在执行流程中补充“括号重写优先级”（括号仅保留短提示，信息优先改写为连续句子流）
  - `skills/nsfc-humanization/references/machine-patterns.md`：新增“括号嵌套与信息堆砌（数据来源/规模）”对比示例
  - `skills/nsfc-humanization/config.yaml`、`skills/nsfc-humanization/CHANGELOG.md`、`skills/nsfc-humanization/README.md`：版本号更新至 0.1.3（单一真相来源）
  - `README.md`：技能版本表同步更新为 v0.1.3

- **nsfc-research-content-writer v0.2.2 → v0.2.3**：补充篇幅控制约束、差异化组织框架与任务结束提醒
  - `skills/nsfc-research-content-writer/SKILL.md`：新增篇幅控制原则（12–15页/12000–15000字）、基础/应用研究框架建议，并在任务结束后提醒使用 `nsfc-roadmap` 生成技术路线图；强化创新点“少而精”与年度计划“推进逻辑”
  - `skills/nsfc-research-content-writer/references/page_budget.md`：新增研究内容篇幅控制参考（页数/字数/图表策略）
  - `skills/nsfc-research-content-writer/references/anti_patterns.md`：新增反模式 10（忽视页数控制，以字数为导向）
  - `README.md`：同步版本号

- **nsfc-schematic v0.8.5 → v0.8.6**：规划阶段默认改为“纯 AI 规划”（不再要求/默认单选 `template_ref`）
  - `skills/nsfc-schematic/config.yaml`：新增 `planning.planning_mode=ai`，并将 `layout.template_ref` 默认置空（高级选项）
  - `skills/nsfc-schematic/scripts/plan_schematic.py`：新增 `--mode template|ai`；AI 模式输出 `plan_request.json/plan_request.md` 并在宿主 AI 写入 `PLAN.md + spec_draft.yaml` 后复跑校验
  - 文档口径对齐：`skills/nsfc-schematic/SKILL.md`、`skills/nsfc-schematic/README.md`

- **nsfc-roadmap v0.9.0 → v0.9.1**：规划阶段默认改为“纯 AI 规划”（不再要求/引导必须选择 `template_ref`）
  - `skills/nsfc-roadmap/config.yaml`：`planning.planning_mode` 默认由 `template` 改为 `ai`
  - `skills/nsfc-roadmap/scripts/plan_roadmap.py`（AI 规划模式）：模型画廊仅用于学习结构/信息密度控制；request 协议不再要求 `template_ref`
  - 文档口径对齐：`skills/nsfc-roadmap/SKILL.md`、`skills/nsfc-roadmap/README.md`

- **nsfc-schematic v0.8.4 → v0.8.5**：规划阶段模板库扩展（新增 `model-06..model-13` 视觉参考）
  - `skills/nsfc-schematic/references/models/`：将 `curated_*.png` 统一重命名为 `model-06..model-13`
  - `skills/nsfc-schematic/references/models/templates.yaml`：新增 `model-06..model-13` 模板索引，确保可被 `--template-ref model-xx` 选择并进入模型画廊/Contact Sheet
  - `skills/nsfc-schematic/scripts/plan_schematic.py`：规划草案保留分组 `role`，自检阶段按 `role` 识别输入/输出节点，避免分层模板触发误报 P0

- **nsfc-schematic v0.8.3 → v0.8.4**：默认画布比例改为更接近 MacBook 的 16:10（更适合屏幕审阅）
  - `skills/nsfc-schematic/config.yaml`：默认 `renderer.canvas` 高度调整（16:10）

- **nsfc-schematic v0.8.2 → v0.8.3**：分组标题栏统一、画布比例更稳健、连线路由避让增强
  - `skills/nsfc-schematic/scripts/schematic_writer.py`：分组容器改用 swimlane 渲染统一标题栏，改善长中文分组标题排版一致性
  - `skills/nsfc-schematic/scripts/spec_parser.py`：新增可选“收缩到内容”画布拟合，避免极端比例与大量空白
  - `skills/nsfc-schematic/scripts/schematic_writer.py`：连线路由加入分组标题栏避让与更保守的障碍 padding，降低遮挡风险
  - `skills/nsfc-schematic/config.yaml`：默认画布更接近 A4 横版比例，并新增 `layout.canvas_fit` / `layout.routing` 配置项

- **AGENTS.md**：在"变更边界"部分新增规则
  - 当 `skills/` 目录内文件有变化时，需检查 `README.md` 是否需要同步更新

- **nsfc-research-foundation-writer v0.1.0 → v0.1.1**：写入安全约束与只读自检脚本增强
  - `SKILL.md`：补充参数说明与“只替换正文、不改标题层级”的写入安全约束；补充可选脚本自检入口
  - `references/`：信息表去年份化；DoD 清单补齐 `.cls/.sty` 禁改约束；示例输出增加“不得编造细节”的说明
  - `scripts/`：新增 `validate_skill.py`（结构一致性校验）与 `check_project_outputs.py`（项目输出轻量自检）
  - `README.md`：移除年份绑定表述，补充 `output_mode` 与自检命令
  - `skills/README.md`：同步移除年份绑定表述，补齐推荐 Prompt 模板的 `output_mode` 与禁改约束

- **nsfc-justification-writer v0.7.7 → v0.7.8**：强化“科学问题/科学假设”写作闭环与信息表口径
  - `references/`：新增科学问题与科学假设写作要点（瓶颈→约束→问题→假设闭环自检）
  - `references/info_form.md` 与 `scripts/core/info_form.py`：信息表字段提示强化（科学问题≠研究目标、假设不写验证方式、瓶颈→约束映射）
  - `scripts/core/writing_coach.py` 与 `assets/prompts/*.txt`：写作教练与诊断/评审提示加入“逻辑链闭环”检查要点
  - `README.md`、`skills/README.md`：同步版本号与“科学问题/科学假设”措辞

- **nsfc-justification-writer v0.7.8 → v0.7.9**：整合第三方“瘦身提质”约束的诊断预警（页数/字数/文献/开篇）
  - `skills/nsfc-justification-writer/config.yaml`：新增 `constraints.*`（页数 6-10 推荐 6-8、字数 8000-10000、核心文献 30-50、开篇 300 字），并将兜底字数调整为 9000±800
  - `skills/nsfc-justification-writer/scripts/core/diagnostic.py`：Tier1 增加预估页数、核心文献数量与开篇信号检查（启发式，默认不阻断写入）
  - `skills/nsfc-justification-writer/scripts/run.py`：`test-session` 将 pytest/python 缓存隔离到会话目录，测试中间产物集中收口
  - `skills/nsfc-justification-writer/SKILL.md`、`skills/nsfc-justification-writer/README.md`：同步写作约束口径
  - `README.md`、`skills/README.md`：同步 nsfc-justification-writer 版本号

- **nsfc-roadmap v0.8.0 → v0.8.1**：规划阶段对齐“立项依据 + 研究内容/技术路线”，并同步新增模板文档
  - `scripts/extract_proposal.py`：`proposal_path` 场景同时提取立项依据与研究内容/技术路线，提升模板选择与路线图叙事的全面性
  - `references/models/templates.yaml`：增加 `render_family`（概念 family 与可落地图骨架解耦，支持稳定回退）
  - `references/models/README.md`、`skills/nsfc-roadmap/README.md`：补齐 `model-07..model-10` 与新增 family 的使用说明

- **nsfc-roadmap v0.8.1 → v0.8.2**：密度/字号/配色纠偏（内容与渲染解耦），修复多轮优化“越改越差”的方向性问题
  - `skills/nsfc-roadmap/scripts/generate_roadmap.py`：移除 P0/P1 触发时的“缩字号/扩画布/缩间距”自动修复逻辑；改为仅在 overflow 时减字号、在字号偏小时增字号，并避免密度驱动参数劣化
  - `skills/nsfc-roadmap/config.yaml`：重校准拥挤阈值（P1=0.55，P0=0.65），避免对信息密集型路线图误判
  - `skills/nsfc-roadmap/config.yaml`：固定画布高度约束（禁用 exploration 的 `height_px` 抖动），避免在优化循环中通过“拉长画布”掩盖内容拥挤问题
  - `skills/nsfc-roadmap/scripts/evaluate_roadmap.py` / `skills/nsfc-roadmap/scripts/evaluate_dimension.py`：对齐拥挤提示文案与 P0/P1 判定口径（强调优先精简内容，不靠缩字号“过阈值”）
  - `skills/nsfc-roadmap/scripts/generate_roadmap.py`：ai_critic request 增加“密度/字号/配色”纠偏约束；`config_local.color_scheme.name` 限制为 `{academic-blue, tint-layered}`，避免误切 `outline-print`
  - 文档同步：`skills/nsfc-roadmap/SKILL.md`、`skills/nsfc-roadmap/README.md`、`skills/README.md`、根 `README.md` 更新相关说明与版本号

- **nsfc-roadmap v0.8.2 → v0.9.0**：新增“视觉选型模式”（模型画廊 contact sheet）+ 模板索引最小化
  - `skills/nsfc-roadmap/scripts/plan_roadmap.py`：规划阶段自动生成 `models_contact_sheet.png` / `models/` / `models_index.yaml`，并在 AI 规划请求中显式引导“先看图再选 template_ref”
  - `skills/nsfc-roadmap/references/models/templates.yaml`：精简为最小机器索引（仅保留 `id/file/family/render_family`），避免硬编码叙事 token
  - `skills/nsfc-roadmap/scripts/template_library.py` / `skills/nsfc-roadmap/scripts/generate_roadmap.py`：对齐最小 schema，去除对 `use_when/avoid/family tokens` 的依赖
  - `skills/nsfc-roadmap/scripts/render_roadmap.py`：修复 classic 布局导出 `.drawio` 时的 `UnboundLocalError` 崩溃（主线 anchor 节点写入位置修正）
  - 文档同步：`skills/nsfc-roadmap/references/models/README.md`、`skills/nsfc-roadmap/README.md`、`skills/nsfc-roadmap/SKILL.md`、`skills/README.md`、根 `README.md`

- **nsfc-qc v0.1.1 → v0.1.2**：新增中文直引号排版预检（只读）
  - `scripts/nsfc_qc_precheck.py`：检测 `"免疫景观"` 这类直引号写法，输出 `quote_issues.csv` 并在 `precheck.json` 中给出结构化统计与替换建议（``免疫景观''）
  - `scripts/materialize_final_outputs.py`：metrics 聚合时纳入 `typography` 预检信息并补齐产物索引

- **nsfc-qc v0.1.2 → v0.1.3**：引用真伪核查升级为“硬编码证据包 + AI 语义判断”，并将 4 步法隔离编译固定为 QC 最后一步
  - `scripts/nsfc_qc_precheck.py`：新增 `--resolve-refs`（抓取标题/摘要/可选 OA PDF 片段）与标书引用上下文提取，输出 `reference_evidence.jsonl`
  - `scripts/run_parallel_qc.py`：默认先跑预检并把证据包复制到 snapshot 的 `./.nsfc-qc/input/`，thread 可只读使用；新增 `--compile-last`
  - `scripts/nsfc_qc_compile.py`：新增 4 步法隔离编译脚本（xelatex→bibtex→xelatex→xelatex），回填 metrics

- **nsfc-qc v0.1.3 → v0.1.4**：实例隔离输出（deliver-dir + sidecar 工作区）+ 报告/JSON 一致性校验 + 路径可搬运性增强
  - `scripts/nsfc_qc_run.py`：新增“一键实例隔离”运行器，默认输出到 `QC/{run_id}/` + `QC/{run_id}.nsfc-qc/`
  - `scripts/run_parallel_qc.py`：支持 `--workspace-dir` 重定向中间产物；run_id 冲突自动后缀 `r1/r2...`；parallel-vibe 不可用/plan-only 也会落盘 final 输出
  - `scripts/materialize_final_outputs.py`：支持 `--run-dir`；metrics/artifacts 路径改为相对 run_dir；把 precheck/compile 的确定性信号映射为“底线 findings”，并注入报告表格；新增 `final/validation.json`
  - `scripts/nsfc_qc_precheck.py`、`scripts/nsfc_qc_compile.py`：compile.json 路径字段优先输出相对 out_dir（同时保留 *_abs）

- **nsfc-qc v0.1.4 → v0.1.5**：默认工作区改为交付目录内隐藏目录（`.nsfc-qc/`），并减少交付目录中间文件噪声
  - `scripts/nsfc_qc_run.py`：默认 workspace_dir 从 `QC/{run_id}.nsfc-qc/` 调整为 `QC/{run_id}/.nsfc-qc/`
  - `scripts/nsfc_qc_run.py`：交付目录仅保留最终报告与结构化输出；预检/编译等中间 artifacts 保留在隐藏工作区 run 目录下

- **nsfc-qc v0.1.5 → v0.1.6**：新增“全称与缩写规范”确定性预检（启发式）
  - `scripts/nsfc_qc_precheck.py`：输出 `abbreviation_issues.csv`，并在 `precheck.json` 中给出结构化统计与建议（首次出现建议“中文全称（English Full Name, ABBR）”；后文尽量仅用 ABBR）
  - `scripts/run_parallel_qc.py`：把 `abbreviation_issues.csv` 复制进 snapshot 的 `./.nsfc-qc/input/` 供 thread 只读引用
  - `scripts/materialize_final_outputs.py`：将缩写预检信号映射为确定性 findings（P1/P2）并纳入 metrics 聚合与 artifacts 索引

- **nsfc-qc v0.1.6 → v0.1.7**：thread 证据包目录统一到 `snapshot/.nsfc-qc/input/`（确保所有中间操作严格落在 `.nsfc-qc/` 下）
  - `scripts/run_parallel_qc.py`：证据包路径统一为 `./.nsfc-qc/input/*`，确保所有中间操作严格落在 `.nsfc-qc/` 下

- **nsfc-qc v0.1.7 → v0.1.8**：snapshot 最小化为仅拷贝 `*.tex/*.bib`（并跳过 `QC/` 等大目录），显著降低隐藏工作区体积与线程倍增开销
  - `scripts/run_parallel_qc.py`：`_copy_snapshot()` 改为按扩展名白名单拷贝（`.tex/.bib`），避免全量 copytree
  - `scripts/nsfc_qc_precheck.py`、`scripts/nsfc_qc_compile.py`：隔离编译 ignore 列表加入 `QC/`，避免把历史 QC 交付目录拷入编译工作区

- **nsfc-qc v0.1.8 → v0.1.9**：移除“编译是否成功/PDF 页数”相关流程与输出，定位为“内容质量 QC”（标书写得怎么样）
  - `scripts/nsfc_qc_run.py`、`scripts/run_parallel_qc.py`：移除 `--compile-last`
  - `scripts/nsfc_qc_precheck.py`：移除 `--compile` 与隔离编译逻辑
  - `scripts/materialize_final_outputs.py`、`templates/REPORT_TEMPLATE.md`：final 输出不再聚合 compile 信息；报告中页数改为提示用户自行编译核对

- **nsfc-qc v0.1.9 → v0.2.0**：缩略语检查增强（误报过滤 + AI 友好摘要），并将缩略语规范升级为 thread 独立必检项
  - `skills/nsfc-qc/scripts/nsfc_qc_precheck.py`：扩展 stoplist（Fig/Tab/Sec 等）与误报过滤（清除 `\\label/\\ref/\\cite` 参数与 `\\begin/\\end` 环境名；过滤 `V2` 这类版本 token）；新增 `abbreviation_issues_summary.json`
  - `skills/nsfc-qc/scripts/run_parallel_qc.py`：将 `abbreviation_issues_summary.json` 纳入 snapshot 证据包，并在 thread prompt 中要求独立输出“缩略语规范”小节（按文件/行号给出建议）
  - `skills/nsfc-qc/SKILL.md`：thread 统一任务新增“缩略语规范”独立必检项，预检产物清单补齐缩写相关产物
  - `skills/nsfc-qc/references/qc_checklist.md`：缩略语规范独立成章，细化检查点与分级口径

- 优化 [AGENTS.md](AGENTS.md)：有机整合外部 [huangwb8/skills](https://github.com/huangwb8/skills) 项目的 Skill 开发规范
  - 新增"Skill 开发规范"章节，包含完整的目录结构、文档规范（SKILL.md/README.md/config.yaml）、版本管理、六大质量原则、文档更新与发布流程
  - 融合外部规范的核心原则：SKILL.md ≤500 行、description ≤1024 字符（单行格式、融入负向约束）、移除版本标记、简洁标题（无序号前缀）
  - 强调硬编码与 AI 功能划分、多轮自检、冗余残留检查、安全性审视、过度设计检查、通用性验证六大质量原则
  - 重构文档结构：合并目录结构和项目概览、统一通用规范部分、整合 LaTeX 技术规范、明确化文档与版本管理、完善文档更新原则（有机更新哲学）
  - 移除冗余内容（删除重复的"项目目标""默认语言""工程原则"等章节、自动生成的冗长目录树）
  - 精简了 Codex CLI 特定说明，核心内容已融入通用规范

- 更新 [CLAUDE.md](CLAUDE.md)：完善与 AGENTS.md 的关系说明
  - 强调 AGENTS.md 为跨平台通用项目指令（Single Source of Truth）
  - 明确 CLAUDE.md 通过 `@./AGENTS.md` 自动引用，修改 AGENTS.md 后无需任何同步操作

- 更新 3 个 NSFC 标书模板 README：补充并优化“如何调整/自定义序号样式（enumerate 编号）”教程（含 3 套常用多级序号组合）
  - [projects/NSFC_General/README.md](projects/NSFC_General/README.md)
  - [projects/NSFC_Local/README.md](projects/NSFC_Local/README.md)
  - [projects/NSFC_Young/README.md](projects/NSFC_Young/README.md)

- **nsfc-schematic v0.7.0 → v0.8.0**：AI 自主化评估与 TEX 提取协议升级
  - AI 主评估协议从“measurements.json 驱动”改为“spec+config+PNG 请求包驱动”（`ai_eval_request.md`/`ai_eval_response.json`）
  - 新增 TEX → spec 的 AI 离线提取协议（`ai_tex_request.md`/`ai_tex_response.json`），无响应自动降级
  - AI 主评估生效时默认跳过多维度启发式扣分，避免重复扣分导致口径漂移

- **nsfc-schematic v0.8.0 → v0.8.1**：规划阶段引入“图类型模板库”与稳健默认值
  - `references/models/templates.yaml`：新增 5 类常用图类型模板（线性/分层/反馈/并行/中心辐射）
  - `plan_schematic.py`：`proposal_path` 场景综合提取“立项依据 + 研究内容”，并支持 `--template-ref` 强制指定模板
  - `evaluation.evaluation_mode` 默认改为 `heuristic`（`ai` 作为可选增强），默认启用 PDF 导出（需 draw.io CLI）

- **nsfc-schematic v0.8.1 → v0.8.2**：规划阶段新增“模型画廊”（skeleton/simple 优先）辅助视觉选型
  - `skills/nsfc-schematic/references/models/templates.yaml`：为部分模板补充 `file/simple_file`（其中 `simple_file` 为骨架/模式图）
  - `skills/nsfc-schematic/scripts/model_gallery.py`：新增 contact sheet 生成器（full + skeleton）
  - `skills/nsfc-schematic/scripts/plan_schematic.py`：规划输出 `PLAN.md` 中增加模型画廊路径提示

- 更新 `.gitignore`：忽略 `projects/**/.nsfc-qc/`（nsfc-qc 的运行产物与报告目录），避免污染工作区

- 更新 `.gitignore`：修正 `/tests/` 仅忽略根目录 `tests/`，并放行 `skills/nsfc-justification-writer` 的 `plans/`、`tests/` 进入版本控制（中间产物目录仍默认忽略）

### Added（新增）

- **nsfc-qc**：新增实例辅助优化计划文档（目录隔离/相对路径/报告结构校验方案）
  - [skills/nsfc-qc/plans/实例辅助优化-v202602170903.md](skills/nsfc-qc/plans/实例辅助优化-v202602170903.md)

- **nsfc-roadmap**：新增路线图“画图经验”沉淀文档（模板共性规律 + family 选型 + 密度/字号优化经验）
  - [skills/nsfc-roadmap/plans/画图经验-优化-v202602200803.md](skills/nsfc-roadmap/plans/画图经验-优化-v202602200803.md)

- **nsfc-reviewers v0.5.0**：新增 NSFC 标书专家评审模拟技能（🚧 开发中）
  - 模拟 5 位领域专家角色（创新性/可行性/基础与团队/严格综合/建设性）对标书进行多维度评审
  - 支持并行多组评审（最多 5 组，依赖 parallel-vibe），无 parallel-vibe 时自动降级到单组模式
  - 6 维度加权评审：创新性 25%、假说 20%、方法 20%、基础 15%、团队 10%、成果 10%
  - 问题分级输出：P0（致命）→ P1（重要）→ P2（建议），含证据锚点
  - 跨组共识聚合（默认 60% 共识阈值），自动升级严重度
  - 强制输出整理：中间过程自动归档到 `.nsfc-reviewers/`，最终交付清晰可见
  - 包含 5 个脚本、7 个参考资料文件、完整的 plans 和 tests 目录

- **nsfc-roadmap v0.8.0**：新增 NSFC 技术路线图生成技能（🚧 开发中）
  - 从 NSFC 标书自动生成可打印、A4 可读的技术路线图
  - 输出 `.drawio`（可编辑）与 `.svg`/`.png`/`.pdf`（交付）
  - 内置 6 个参考模板（model-01 ~ model-06）
  - 多轮评估-优化（默认 5 轮），三维度自检（Structure/Visual/Readability）
  - "平台期停止"策略：基于 PNG 哈希与分数提升阈值自动停止
  - 支持规划模式（先审阅 `roadmap-plan.md` 再生成）与 AI 自主闭环模式
  - 包含 13 个脚本、模板库（templates.yaml + 6 张参考图）

- **nsfc-schematic v0.7.0**：新增 NSFC 原理图/机制图生成技能（🚧 开发中）
  - 将标书中的研究机制、算法架构、模块关系转成原理图
  - 分组结构：输入层 → 处理层 → 输出层（柔性）+ 任意连线
  - 节点文案自动扩容，避免导出后文字溢出/遮挡
  - 正交路由，确定性几何计算避免连线穿字
  - 多轮评估-优化（默认 5 轮），三维度自检（结构/视觉/可读性）
  - 元素层级保护：分组底层 → 连线中层 → 节点顶层
  - 离线 AI 评估协议：脚本生成证据包，AI 自主评分
  - 包含 14 个脚本、设计原则参考、spec 示例、配色库

- **nsfc-abstract v0.2.0**：NSFC 标书中英文摘要生成技能（英文为中文的忠实翻译；中文≤400字、英文≤4000字符），输出写入工作目录 `NSFC-ABSTRACTS.md`；新增"字数超限闭环处理"说明，并增强确定性长度校验/写入脚本（JSON/diff 输出、严格模式不写入）
- **nsfc-abstract v0.3.0**：新增"标题建议"输出（默认 1 个推荐标题 + 5 个候选标题及理由），并在校验/写入脚本中加入标题分段的确定性检查；新增标题写作规则参考文档 `skills/nsfc-abstract/references/title-rules.md`
- **nsfc-qc v0.1.1**：新增 NSFC 标书只读质量控制技能（多线程独立 QC + 标准化报告）
  - 中间文件统一归档到 `project_root/.nsfc-qc/`（包含 parallel-vibe 产物），不污染标书目录
  - 多线程（默认 5 threads，默认串联）独立检查：文风生硬、引用假引/错引风险、篇幅与章节分布、逻辑清晰度等
  - 确定性脚本可生成标准化 final 输出骨架（report/metrics/findings），即使 threads 尚未运行也可落盘
  - `--compile` 路径在缺少 TeX 工具链时自动降级（记录 `missing_tools`），不崩溃

### Updated（文档更新）

- 更新 [README.md](README.md)：技能生态系统新增"质量保障与图表生成"分类，技能表格新增 nsfc-reviewers（v0.5.0）、nsfc-roadmap（v0.8.0）、nsfc-schematic（v0.7.0），均标记为 🚧 开发中
- 更新 [skills/README.md](skills/README.md)：新增 nsfc-reviewers/nsfc-roadmap/nsfc-schematic 三个完整技能说明（功能、使用场景、Prompt 模板、技能特点），调整后续技能编号（8→12，9→13，10→14），更新推荐工作流（新增图表生成与专家评审环节）和技能依赖关系

- 更新 [README.md](README.md)：技能表格更新 nsfc-abstract（v0.2.0）
- 更新 [README.md](README.md)：nsfc-abstract 版本号与描述更新至 v0.3.0（加入"标题建议"输出）
- 更新 [skills/README.md](skills/README.md)：新增 nsfc-abstract 小节说明与可选长度校验命令，并调整后续技能编号

### Removed（移除）

- 移除 `skills/nsfc-bib-manager/` 技能，并同步更新相关文档/脚本中对该技能的引用：`README.md`、`skills/README.md`、`skills/nsfc-justification-writer/*`、`skills/transfer_old_latex_to_new/config.yaml`（改为“提供 DOI/链接并手动补齐 references/*.bib”的流程表述）

### Changed（变更）

- **nsfc-research-content-writer v0.2.1 → v0.2.2**：完善技能自检与可追溯测试基础设施
  - 补齐 `templates/`、`plans/`、`tests/`，提供 A/B 轮计划与测试报告模板，支持确定性会话创建脚本
  - 配置集中化：`config.yaml` 补齐 `skill_info.description`，新增 `checks`（risk_phrases/subgoal_markers_min）
  - 脚本优化：抽出 `_yaml_utils.py` 复用 YAML 片段解析；`check_project_outputs.py` 读取配置并增强子目标 marker 识别；`create_test_session.py` 强化会话 ID 校验
  - 文档一致性：移除本 skill 及 `skills/README.md` 中的年份限定表述

- **nsfc-justification-writer**：目录结构与可移植性收口（解决“目录管理太乱”）
  - 资源统一归档到 `assets/`（prompts/templates/examples/presets），并在代码中加入新路径优先 + 旧路径兼容回退
  - 移除仅用于说明的 `config/` 兼容占位目录（旧路径 `config/presets/` 仍可由用户按需自行创建）
  - 文档统一归档到 `references/docs/`，补齐索引与“路径提示”（仓库根目录/skill 目录两种运行方式）
  - 实现模块统一托管到 `scripts/core/`（不再保留根级 `core/` 目录），入口脚本统一从 `scripts/` 调用
  - Python 单测统一放在 `tests/pytest/`，`tests/` 同时承载 pytest 测试与 auto-test-skill 会话；更新 `tests/README.md` 解释分工
  - runs/cache 默认落点统一到 `tests/_artifacts/` 并被 gitignore，避免运行产物污染仓库
  - 新增 `scripts/run.py test-session`：每次测试自动创建 `tests/<session>/` 子目录并记录 `TEST_PLAN.md`/`TEST_REPORT.md`
  - 修复单测与实现行为不一致（SLR 目录检测与配置校验 guardrails）

- 统一 skills 作者口径：将 `skills/*/SKILL.md` 的 `metadata.author` 与 `skills/*/config.yaml` 的 `skill_info.author` 固定为 `Bensz Conan`

- 调整 NSFC_General 模板的段后距与标题间距逻辑：移除全局 `\parskip=7.8pt`，改为 `\parskip=0pt` 并在 `\subsection` 的 `titlespacing` 中显式给出 7.8pt 的标题后间距，避免 `\NSFCBodyText` 改写 `\parskip` 导致 `\section`/`\subsection` 垂直间距前后不一致
- 更新 NSFC_General 的样式微调文档：说明默认不使用 `\parskip`，并同步标题间距示例到最新配置
- 更新三套 NSFC 正文项目的 README 间距调节指南：突出说明如何设置正文间距、参考文献间距，以及 `\subsubsubsection` 与更低层级标题的前后间距（并补齐 `projects/NSFC_Local/README.md`）
- **NSFC_Local / NSFC_Young**：迁移 NSFC_General 的标题间距与参考文献兼容性优化：对齐 `titlesec` 的 `\titlespacing*{\section}`/`\titlespacing*{\subsection}`；引入 `etoolbox` 并新增 `\NSFCHasCite` 检测逻辑，为“无引用也可跑 bibtex / 可选隐藏空参考文献”提供基础：`projects/NSFC_Local/extraTex/@config.tex`、`projects/NSFC_Young/extraTex/@config.tex`

### Changed（变更）

- **NSFC_General / NSFC_Young / NSFC_Local**：优化参考文献配置的关注点分离，将 `\NSFCBibStyle` 与 `\NSFCBibDatabase` 定义从 `extraTex/@config.tex` 移至 `references/reference.tex`，使参考文献专用配置与通用样式配置解耦：`projects/NSFC_General/extraTex/@config.tex`、`projects/NSFC_Young/extraTex/@config.tex`、`projects/NSFC_Local/extraTex/@config.tex`、`projects/NSFC_General/references/reference.tex`、`projects/NSFC_Young/references/reference.tex`、`projects/NSFC_Local/references/reference.tex`
- **NSFC_General / NSFC_Young / NSFC_Local**：正文 `extraTex` 段间距改为紧凑模式（在 `\\NSFCBodyText` 中将 `\\parskip` 设为 `0pt`），使段间距与行间距观感一致：`projects/NSFC_General/extraTex/@config.tex`、`projects/NSFC_Young/extraTex/@config.tex`、`projects/NSFC_Local/extraTex/@config.tex`
- **NSFC_General / NSFC_Young / NSFC_Local**：参考文献样式新增可调参数并统一实现：标题与上文/标题与条目/条目间距（`\NSFCBibTitleAboveSkip/\NSFCBibTitleBelowSkip/\NSFCBibItemSep`）+ 参考文献条目行宽（`\NSFCBibTextWidth`，用于跨项目消除换行差异）；参考文献标题不再走 `\section*`（避免 titlesec 对 `\section` 的 spacing 差异影响参考文献），改为在 `thebibliography` 内部手工排版并显式设置 list 间距，确保"参考文献相关参数一致时"渲染效果一致：`projects/NSFC_General/extraTex/@config.tex`、`projects/NSFC_Young/extraTex/@config.tex`、`projects/NSFC_Local/extraTex/@config.tex`
- **NSFC_General / NSFC_Young / NSFC_Local**：参考文献间距参数改为“两层架构”管理：`extraTex/@config.tex` 仅提供基础默认值（统一为 `10pt/0pt/0pt/397.16727pt`），用户在 `references/reference.tex` 中按需用 `\\setlength` 覆盖并附示例注释，降低升级覆盖风险：`projects/NSFC_General/extraTex/@config.tex`、`projects/NSFC_Young/extraTex/@config.tex`、`projects/NSFC_Local/extraTex/@config.tex`、`projects/NSFC_General/references/reference.tex`、`projects/NSFC_Young/references/reference.tex`、`projects/NSFC_Local/references/reference.tex`、`references/README.md`
- **NSFC_General / NSFC_Young / NSFC_Local**：将 `\NSFCBibTextWidth` 的推荐默认值统一按 Young 的最窄有效行宽设置，默认情况下三套项目的参考文献换行更接近一致：`projects/NSFC_General/extraTex/@config.tex`、`projects/NSFC_Young/extraTex/@config.tex`、`projects/NSFC_Local/extraTex/@config.tex`
- **NSFC_General / NSFC_Young / NSFC_Local**：`references/reference.tex` 统一为"样式/数据库均由 @config.tex 控制"的写法：使用 `\\NSFCBibStyle/\\NSFCBibDatabase` 指定 bst 与 bib，并加入间距调节提示注释；同时对齐 General 的参考文献排版（与 Local/Young 一致采用 `\\begin{spacing}{1}` + `\\wuhao`）：`projects/NSFC_General/references/reference.tex`、`projects/NSFC_Young/references/reference.tex`、`projects/NSFC_Local/references/reference.tex`
- **NSFC_Young / NSFC_Local**：示例图片不再使用子图并排，改为两张图分开展示，便于审阅与排版微调：`projects/NSFC_Young/extraTex/2.1.研究内容.tex`、`projects/NSFC_Local/extraTex/1.3.方案及可行性.tex`
- **transfer_old_latex_to_new**：核心模块迁移到 `scripts/core/` 并统一导入路径；文档从 `docs/` 归档到 `references/`，同步修复引用链接；清理已跟踪的 `__pycache__` 缓存目录。
- **transfer_old_latex_to_new**：资源处理支持 `figure_handling=link/skip`，并补齐超出项目根目录资源的扫描提示。
- **transfer_old_latex_to_new v1.4.1**：资源扫描支持 `exclude_dirs` 与无扩展名图片解析；`\\import/\\includefrom` 路径解析更完整；`\\cite*` 家族引用提取更全面；`link` 策略下避免覆盖已有非软链接文件。
- **transfer_old_latex_to_new**：配置指南补充预留字段说明（cache/output.deliverables/backup_location）。
- 重构三个 NSFC 正文项目的 `extraTex/*.tex` 示例正文（保持原有主题与提纲结构不变），并统一段首缩进与代码展示风格：`projects/NSFC_Young/`, `projects/NSFC_General/`, `projects/NSFC_Local/`

### Fixed（修复）

- **NSFC_General / NSFC_Young / NSFC_Local**：修复“参考文献”标题配色与最新 Release 不一致的问题：在自定义 `thebibliography` 标题渲染中补回 `MsBlue`，保持现有参考文献间距/行宽/条目样式不变：`projects/NSFC_General/extraTex/@config.tex`、`projects/NSFC_Young/extraTex/@config.tex`、`projects/NSFC_Local/extraTex/@config.tex`
- **transfer_old_latex_to_new**：CacheManager 对不可 JSON 序列化的结果不再抛异常，仅落 L1 缓存。
- **transfer_old_latex_to_new**：资源扫描与复制增加路径越界保护，避免不受控写入与异常。
- **transfer_old_latex_to_new**：批量 AI 响应解析不完整时自动回退，避免静默丢失结果。
- **transfer_old_latex_to_new**：资源扫描补充排除目录统计并输出提醒，避免隐式漏拷资源。
- 修复 [references/README.md](references/README.md) 与 [config.yaml](config.yaml) 的辅助文档列表不一致问题：移除对不存在文件的引用，并修正文档中 LaTeX 命令的反斜杠显示。
- 修复正文“提示语/标题”排版异常：保留模板的全局 `\\parindent=0pt`，改为在 `extraTex` 正文中通过 `\\NSFCBodyText` 启用段首缩进 2em，避免与 `main.tex` 的 `\\hspace*{2em}`/`\\linebreak{}` 叠加导致换行错位：`projects/NSFC_Young/extraTex/@config.tex`, `projects/NSFC_General/extraTex/@config.tex`, `projects/NSFC_Local/extraTex/@config.tex`
- 示例内容整合仓库素材：正文中引用 `projects/*/figures/*` 与 `projects/*/code/test.sh`（`\\includegraphics` + `\\lstinputlisting`），并统一 `listings` 样式为 `codestyle01`
- 篇幅控制：三套项目 PDF 均落在 12–14 页；对 Young/General/Local 将两张示例图合并为子图，代码清单做片段截取；并移除 General 示例中过多的 `\\NSFCBlankPara` 额外留白以避免无意义增页

### Changed（变更）

- **complete_example v1.4.0 → v1.4.1**：路径解析与编译验证加固（更少污染、更可复现）
  - `skill_controller.py`：`project_name` 支持“项目名/项目路径”两种输入；新增 projects/ 边界校验，拦截路径穿越；缺失 `main.tex` 时明确报错
  - `skill_controller.py`：默认 `target_files` 改为自动扫描 `extraTex/*.tex`（排除 `@config.tex`），避免模板文件名变更导致示例/默认流程失效
  - `format_guard.py`：编译产物写入 `run_dir/_latex_build/`（使用 `-output-directory`），降低对项目根目录的污染；批量 apply 后统一编译验证，失败自动回滚
  - `format_guard.py`：bibtex 运行优先使用相对路径参数，规避 TeX 安全策略对绝对路径输出的限制
  - `security_manager.py`：读取 `config.yaml:security.*` 覆盖默认黑白名单；统一使用 posix 路径匹配；忽略注释行的格式注入误报
  - `basic_usage.py` / `advanced_usage.py` / `SKILL.md`：更新示例 `target_files` 默认示例路径

- **complete_example v1.3.0 → v1.4.0**：中间文件存储机制重构（项目级隐藏目录）
  - **项目隔离**：所有中间文件存储在目标项目的 `.complete_example` 隐藏目录中
  - **硬编码保证**：通过硬编码方式确保所有运行时文件（备份、日志、分析结果等）都存放在项目级目录
  - **路径变更**：
    - 旧路径：`skills/complete_example/runs/<run_id>/`
    - 新路径：`{project_path}/.complete_example/<run_id>/`
  - **配置更新**：`config.yaml` 中 `run_management.runs_root` 改为 `{project_path}/.complete_example`
  - **代码更新**：
    - `skill_controller.py`：`_create_run_directory()` 改为接收 `project_path` 参数
    - `format_guard.py`：更新注释中的路径说明
    - `advanced_usage.py`：更新提示信息中的路径说明
  - **文档更新**：`SKILL.md` 中所有 `runs/` 路径引用改为 `.complete_example/`
  - **Git 忽略**：`.gitignore` 新增 `projects/**/.complete_example/` 规则
  - **优势**：
    - ✅ 项目间完全隔离，每个项目有独立的中间文件存储
    - ✅ 便于项目迁移和备份（中间文件随项目一起移动）
    - ✅ 删除项目时自动清理所有相关中间文件
    - ✅ 隐藏目录设计，不污染项目结构

- **complete_example v1.2.0 → v1.3.0**：智能资源分配与篇幅控制优化
  - **新增 `ResourceAllocator`**：智能资源分配器，确保项目中所有 figures 和 code 素材被充分利用
  - **轮询分配策略**：将所有图片和代码随机分配到各个章节（示例无需理解语义）
  - **篇幅自动控制**：估算最终 PDF 页数，自动调整章节字数以达到 12-14 页目标
  - **配置参数**：新增 `page_control` 配置节，包含目标页数、每页字数、各种元素占用的页数等
  - **资源利用率目标**：figures 和 code 的 100% 利用率（所有素材都分配到章节）
  - **新增方法**：`AIContentGenerator.generate_section_content_with_allocation()` 支持预分配资源和目标字数
  - **分配方案可视化**：资源分配结果保存至 `.complete_example/<run_id>/analysis/resource_allocation.json`

- **NSFC_Local**：对齐 2026 地区基金 Word 正文模板（提纲页/边距/标题缩进/段后距）
  - `projects/NSFC_Local/extraTex/@config.tex`：启用 `\\raggedbottom`；`geometry` 设为 `L3.20/R2.94/T2.67/B2.91 cm`；标题缩进统一为 `\\NSFCTitleIndent=28pt`；`\\NSFCSubsection` 使用 `parshape` 复刻"首行缩进、续行回到左边距"；新增 `\\NSFCSubsectionAfterSkip` 并调小默认段后距以让提纲与正文衔接更紧凑
  - `projects/NSFC_Local/main.tex`：标题文字与空格/标点按 2026 模板归一；补齐提纲标题/提示语的加粗位置（与 Word 模板一致）；使用 `\\linebreak{}` 精确对齐标题换行，使 PDF 中每行标题文字与 Word 模板一致；微调提纲区块前后间距以贴近分页观感
  - `projects/NSFC_Local/template/2026年最新word模板-5.地区科学基金项目-正文.docx`：由同名 `.doc` 转换生成，供标题一致性验证与基准管理使用

- **complete_example v1.0.0 → v1.2.0**：多元示例占位符（表格/公式）+ 模板渲染与安全加固
  - 新增本地启发式 LLM 回退：无 API Key 也可生成可解析 JSON 与可落盘示例内容
  - 补齐离线模式对"方案及可行性"类小节（研究方法/技术路线/关键技术/可行性分析）的示例内容生成，便于一键填充模板
  - 新增占位符支持：`{{TABLE:...}}` / `{{INLINE_MATH:...}}` / `{{DISPLAY_MATH:...}}` / `{{EQUATION:...|label}}` / `{{ALIGN:...}}`
  - 新增安全模板渲染器：避免 LaTeX 模板中 `{...}` 被误解析为 Python format 占位符导致 KeyError
  - 修复文献占位符冲突：reference 占位符统一为 `references:<citekey>`，避免同一 `.bib` 多条目覆盖
  - 安全加固：拒绝项目目录外文件写入；章节层级约束（input tex 禁止 `\\section/\\subsection`）落地；扩展格式注入黑名单（含 `\\newcommand` 等）
  - 修复自动清理二次命中问题，并避免自动清理路径直接 `print` 污染输出
  - LLMClient 支持 `temperature` dict 配置（analysis/generation/refinement），避免真实 LLM 路径温度参数类型错误
  - 运行路径解析更稳健：可从任意工作目录正确定位 `projects/<name>`

- **make_latex_model v2.7.1 → v2.7.2**：AI 驱动迭代闭环（最小可用版）与像素对比结构化产物
  - 新增 AI 优化器核心模块：`core/{ai_optimizer,diff_analyzer,decision_reasoner,parameter_executor,history_memory}.py` 与 `prompts/analysis_template.txt`
  - `enhanced_optimize.py`：新增 `--ai/--ai-mode`；像素对比改为解析 `--json-out` 输出并落盘 `diff_features.json`
  - `compare_pdf_pixels.py`：新增 `--json-out/--features-out`；0 页 PDF 显式失败；条纹特征归一化（提升根因推断稳定性）
  - 修复 LaTeX 替换的 `re.sub` 转义风险（避免 `\\newcommand`/`\\renewcommand` 被误解析），并修正 `sync_config.py` 的字号解析正则
  - 加固 `--project` 参数解析与路径边界校验（限制在仓库 `projects/` 下）
  - **SKILL.md 瘦身**：将“可执行细节流程/FAQ”迁移到 `skills/make_latex_model/docs/{WORKFLOW,FAQ}.md`，`SKILL.md` 仅保留边界/入口/验收标准
  - 新增可追溯的 auto-test-skill A/B 轮会话文档：`skills/make_latex_model/plans/` 与 `skills/make_latex_model/tests/`

- **make_latex_model v2.7.2 → v2.8.0**：脚本托管与项目级工作空间隔离重构
  - 核心模块迁移：`skills/make_latex_model/core/` → `skills/make_latex_model/scripts/core/`，并统一导入路径为 `scripts.core.*`
  - 工作空间迁移：产物统一落在 `projects/<project>/.make_latex_model/`（`baselines/iterations/reports/cache/backup`），并生成 `workspace_manager.json` 元数据
  - 向后兼容：检测旧的技能级 workspace 与 `artifacts/` 产物，自动复制到新工作空间（可通过 `workspace.auto_migrate_legacy` / `workspace.verbose_migration` 控制）
  - 迭代上限提升：`iteration.max_iterations` 15 → 30，`no_improvement_limit` 3 → 5
  - 安全加固：关键入口脚本补齐 projects/ 边界校验（防路径遍历），并更新 `analyze_pdf.py`/`run_validators.py`/`generate_baseline.py`/`optimize.py` 等入口的一致性
  - 文档同步：更新 `skills/make_latex_model/{SKILL.md,README.md,docs/WORKFLOW.md,scripts/README.md}` 的路径与迭代说明
  - auto-test-skill：新增 A/B 轮会话 `v202601271524`，并强制闭环 P0-P2

- **make_latex_model v2.8.0 → v2.9.0**：PDF 单源标题对齐 + 加粗解析统一 + 逐段像素对齐落地
  - 新增 `skills/make_latex_model/scripts/extract_headings_from_pdf.py`：从 PDF 基准提取标题文字/加粗片段/跨行换行点
  - `skills/make_latex_model/scripts/compare_headings.py`：支持 PDF 作为输入源（.docx 保留为 deprecated 兼容），并复用统一格式解析器修复加粗识别误报
  - 新增 `skills/make_latex_model/scripts/optimize_heading_linebreaks.py`：根据 PDF 标题跨行位置自动插入 `\\linebreak{}`（严格匹配后才改写）
  - 新增 `skills/make_latex_model/scripts/core/latex_format_parser.py`：统一解析 `\\textbf{}` / `{\\bfseries ...}` / 嵌套命令等常见格式，供对比与验证器复用
  - 新增逐段对齐链路：`scripts/core/paragraph_alignment.py` + `scripts/{extract_paragraphs,match_paragraphs,compare_paragraph_images}.py`；`compare_pdf_pixels.py` 增加 `--mode paragraph` 与段落级特征输出；`diff_analyzer.py` 识别 paragraph mode 特征并给出更贴近段距/缩进/行距的根因推断
  - `enhanced_optimize.py`/`run_ai_optimizer.py`：基准 PDF 选择更稳健（优先 `baseline.pdf`，兼容 `word.pdf`），并支持从配置传递像素对比 mode/dpi/tolerance/min_similarity
  - 文档与配置同步：`skills/make_latex_model/{SKILL.md,config.yaml,docs/WORKFLOW.md,scripts/README.md}`

- **make_latex_model**：增强 NSFC 系模板的基准选择与验证稳定性
  - `skills/make_latex_model/scripts/compare_headings.py`：忽略被注释的标题；同时识别 `\\NSFCSubsection{}`；支持嵌套花括号标题（用于 `\\textbf{...}` 等局部加粗）；Word 标题样式缺失时回退到“文本模式”提取；支持生成 HTML 报告；格式对比时保留空格边界（避免 `1.~` 等空白差异误报）
  - `skills/make_latex_model/scripts/{generate_baseline.py,core/validators/heading_validator.py}`：模板目录存在多份 Word 文件时，优先选择“年份最大”的模板（同年优先 `.docx`）
  - `skills/make_latex_model/scripts/validate.sh`：基于 `projects/<project>/.make_latex_model/baselines/word_analysis.json` 自动校验边距；Word 模板选择与年份排序对齐
  - `skills/make_latex_model/scripts/prepare_main.py`：新增 `--add-placeholders`（可选）用于像素对齐调试，默认保持“只注释 input 行”的语义
  - `skills/make_latex_model/scripts/compare_pdf_pixels.py`：JSON 输出字段强制转换为基础类型（提升跨平台可读性/可序列化稳定性）

- **NSFC_Local**：补充“深度学习在医疗影像分析中的应用”示例内容（CNN 架构 + 数据增强策略）
  - 更新 `projects/NSFC_Local/extraTex/1.2.内容目标问题.tex`：研究内容/目标/关键问题
  - 更新 `projects/NSFC_Local/extraTex/1.3.方案及可行性.tex`：研究方法/技术路线/关键技术/可行性分析
  - 更新 `projects/NSFC_Local/extraTex/1.4.特色与创新.tex`：特色与创新点
  - 更新 `projects/NSFC_Local/extraTex/1.5.研究计划.tex`：三年计划与预期结果

- **NSFC_Local**：对齐 2026 年“地区科学基金项目-正文”Word 模板版式与提纲
  - 更新 `projects/NSFC_Local/main.tex`：同步“报告正文（2026 版）”与三大部分提纲标题文字；微调标题区与三大部分之间的垂直间距以贴近 2026 PDF 观感
  - 更新 `projects/NSFC_Local/extraTex/@config.tex`：对齐页面边距；新增 `\raggedbottom` 避免页高拉伸；统一标题缩进；`\\NSFCSubsection` 使用 `parshape` 复刻首行缩进/续行回到左边距，并对齐段后距
  - 新增 `projects/NSFC_Local/template/2026年最新word模板-5.地区科学基金项目-正文.docx`：由 2026 `.doc` 转换，便于标题一致性自动校验

- **make_latex_model**：标题一致性校验更稳健
  - 更新 `skills/make_latex_model/scripts/core/validators/heading_validator.py`：模板目录存在多份 `.docx` 时，优先选择文件名中年份最大的那份（否则取字典序最后），避免误用旧年份模板

- **systematic-literature-review v1.0.5 → v1.0.6**：运行提速与上下文/目录膨胀治理（按最小改动落地）
  - API 缓存默认开启但使用 `mode=minimal`（新增 `config.yaml:cache.api.{enabled,mode}`），避免 `.systematic-literature-review/cache/api` 文件爆炸
  - 摘要补齐默认后移到选文后（新增 `config.yaml:search.abstract_enrichment.stage=post_selection`），降低检索阶段耗时与 cache 膨胀
  - 选文策略引入 `selection.target_refs`（默认 midpoint），避免候选库大时“天然打满 max_refs”
  - 写作阶段新增证据卡（`evidence_cards_{topic}.jsonl`）与生成脚本 `build_evidence_cards.py`，压缩证据包字段与摘要长度
  - 新增 `run_pipeline.py`（幂等 work_dir 生成，避免 `{topic}/{topic}` 嵌套目录）与 `reconcile_state_from_outputs.py`（产物反推 state 修复工具）

- **systematic-literature-review v1.0.6 → v1.0.7**：写作负面约束 + work_dir 路径隔离（防止“参见类堆砌引用”与跨 run 污染）
  - `skills/systematic-literature-review/SKILL.md`：新增“写作负面约束（禁止模式）”，显式禁止“本节补充阅读可参见：\cite{...}”等业余写法
  - `skills/systematic-literature-review/references/expert-review-writing.md`：补齐“写作负面约束”章节；将“文献利用率”从硬门槛调整为提示项（不再驱动“必须用完所有文献”）
  - `skills/systematic-literature-review/scripts/validate_no_process_leakage.py`：新增“参见类堆砌引用”模式检测（高危）
  - `skills/systematic-literature-review/scripts/path_scope.py`：新增统一的路径隔离校验模块（scope_root）
  - `skills/systematic-literature-review/scripts/pipeline_runner.py`：统一 work_dir 绝对路径；设置 `SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT`；阶段3提示增强（隔离警告）
  - 核心脚本新增 `--scope-root`（可选，默认读 env）并对 I/O 路径做准入校验：`dedupe_papers.py`、`select_references.py`、`multi_query_search.py`、`openalex_search.py`、`plan_word_budget.py`、`update_working_conditions_data_extraction.py`、`generate_validation_report.py`、`compile_latex_with_bibtex.py`、`convert_latex_to_word.py`
  - `skills/systematic-literature-review/scripts/validate_citation_distribution.py`：新增 `--min-ref-util`（默认不启用硬门槛），避免“为达利用率而强行堆砌引用”

- **systematic-literature-review v1.0.7 → v1.0.8**：质量可观测性 + 更稳健的回滚与路径解析
  - `skills/systematic-literature-review/scripts/generate_validation_report.py`：新增"摘要覆盖率（selected_papers）"统计，避免无感引用缺摘要文献
  - `skills/systematic-literature-review/scripts/pipeline_runner.py`：验证报告阶段透传 selected_papers 与摘要阈值，确保摘要覆盖率可见
  - `skills/systematic-literature-review/scripts/select_references.py`：`min_abstract_chars` 默认值与 `config.yaml` 对齐（兜底 80）；BibTeX 转义增强（补充 `^`/`~`）
  - `skills/systematic-literature-review/scripts/path_scope.py`：异常不再静默吞掉；候选路径为空时显式报错；支持 `SYSTEMATIC_LITERATURE_REVIEW_PATH_SCOPE_DEBUG=1` 输出解析结果
  - `skills/systematic-literature-review/scripts/multi_language.py`：新增 `--auto-restore`，编译失败/需要 AI 修复时自动回滚到编译前备份并保留 `.broken` 副本
  - `skills/systematic-literature-review/scripts/openalex_search.py`：ASCII fallback 触发条件更保守并增加日志，避免搜索语义被无声降级
  - `skills/systematic-literature-review/scripts/validate_counts.py`：明确数字计数口径，新增 `words_digits` 与 `words_total_including_digits`
  - 文档同步：`skills/systematic-literature-review/SKILL.md`、`skills/systematic-literature-review/references/ai_scoring_prompt.md` 明确"低分不分配子主题"，并同步多语言回滚提示

- **systematic-literature-review v1.0.8 → v1.0.9**：工作目录隔离机制增强（AI 临时脚本托管 + Pipeline 自动整理 + A 轮批判性测试修复）
  - `skills/systematic-literature-review/scripts/pipeline_runner.py`：新增 `scripts_dir` 目录创建及 `SYSTEMATIC_LITERATURE_REVIEW_SCRIPTS_DIR` 环境变量，供 AI 临时脚本存放；Pipeline 完成后自动调用 `organize_run_dir.py --apply` 整理工作目录；改进自动整理日志，区分"无需整理"与"整理失败"
  - `skills/systematic-literature-review/scripts/path_scope.py`：新增 `require_scope` 装饰器，可强制校验函数的 Path 参数都在 scope_root 内；新增 URL 排除逻辑（`http://`/`https://` 开头的参数不校验）；新增短别名支持（`SLR_SCOPE_ROOT`、`SLR_PATH_SCOPE_DEBUG`）
  - `skills/systematic-literature-review/scripts/validate_workdir_cleanliness.py`（新增）：校验工作目录根部整洁性，检测中间文件泄漏；非隐藏子目录视为 unexpected（严格隔离）
  - `skills/systematic-literature-review/scripts/organize_run_dir.py`：`FINAL_SUFFIXES` 补充 `_验证报告.md`；新增 AI 临时脚本（`temp_*.py`/`debug_*.py`/`analysis_*.py`）识别与移动到 `scripts/` 目录
  - `skills/systematic-literature-review/scripts/api_cache.py`：`DEFAULT_CACHE_DIR` 改为函数动态获取，环境变量未设置时禁用缓存（避免相对路径导致跨 run 污染）；`CacheStorage` 新增 `enabled` 标志
  - `skills/systematic-literature-review/config.yaml`：`layout` 新增 `scripts_dir_name: "scripts"`
  - `skills/systematic-literature-review/SKILL.md`：新增"文件操作规范（工作目录隔离）"章节，明确 AI 临时脚本与中间文件的存放约定；修正示例代码中 `os.environ.get()` 的类型错误

### Updated（文档更新）

- 更新 [skills/README.md](skills/README.md)：优化 systematic-literature-review 技能描述
  - 更新版本号到 v1.0.8，并同步“摘要覆盖率/多语言自动回滚/低分不分配子主题”等口径
- 更新 [README.md](README.md)：优化 systematic-literature-review 文献调研阶段描述
  - 更新技能表格版本号到 v1.0.8
- 更新 `skills/systematic-literature-review/SKILL.md` 与 `skills/systematic-literature-review/README.md`：补齐新配置与工具脚本说明
- 新增 systematic-literature-review auto-test 会话：`skills/systematic-literature-review/plans/v202601251218.md`、`skills/systematic-literature-review/plans/B轮-v202601251218.md` 及对应 `tests/` 目录
- 新增 systematic-literature-review auto-test 会话：`skills/systematic-literature-review/plans/v202601251439.md`、`skills/systematic-literature-review/plans/B轮-v202601251439.md` 及对应 `tests/` 目录
- 新增审计与优化计划：`skills/systematic-literature-review/plans/文献-优化-v202601251308.md`（针对异种器官移植-02，补全可审计中间产物与 work_dir 隔离建议）
- 更新 [README.md](README.md)：优化 Skills 快速安装说明
  - 新增 `@install` 快捷方式（推荐）：无需手动执行 git 命令，AI 自动克隆并安装
  - 保留手动安装方法作为标准流程备选方案
  - 更新安装命令为 `install-bensz-skills this skill install skills in this project to Codex and Claude Code`

---

## [v3.2.3] - 2026-01-24
  - AGENTS.md 作为通用规范的唯一真相来源
  - CLAUDE.md 采用硬链接模式：包含 AGENTS.md 完整内容 + Claude Code 特定说明
  - 添加 `<!-- HARD_LINK_START -->` / `<!-- HARD_LINK_END -->` 标记同步区域
  - 优化章节组织：项目概览 → 核心工作流 → 工程原则 → 通用规范 → LaTeX 技术规范 → 文档与版本管理
  - 使用分隔线（---）区分主要章节，提升文档"呼吸感"

- **NSFC_Young/NSFC_General README**：新增"样式微调指南"章节，包含行距/段落间距、标题间距、字体大小、标题颜色、列表格式、页面边距等常见微调方法的详细说明，并附带快速微调清单和代码示例

- **nsfc-research-content-writer v0.2.0**：补齐“研究内容→特色与创新→年度计划”的可验证闭环写作约束与参考材料
  - 更新 `skills/nsfc-research-content-writer/SKILL.md`：补齐 `output_mode` 语义、写入安全约束、`S1–S4` 回溯口径与写作小抄索引
  - 更新 `skills/nsfc-research-content-writer/README.md`、`skills/README.md`、`README.md`：补齐“先预览再写入”的推荐工作流与 Prompt 字段，版本同步为 v0.2.0
  - 更新 `skills/nsfc-research-content-writer/references/info_form.md`：补齐任务分解/创新坐标系/年度硬约束/风险备选输入项
  - 更新 `skills/nsfc-research-content-writer/references/dod_checklist.md`：DoD 可操作化（2.1↔2.2↔2.3 可回溯与覆盖检查）
  - 新增参考资料：`skills/nsfc-research-content-writer/references/subgoal_triplet_examples.md`、`skills/nsfc-research-content-writer/references/relative_coordinate_examples.md`、`skills/nsfc-research-content-writer/references/yearly_plan_template.md`、`skills/nsfc-research-content-writer/references/anti_patterns.md`、`skills/nsfc-research-content-writer/references/validation_menu.md`、`skills/nsfc-research-content-writer/references/terminology_sheet.md`
  - 新增开发者校验脚本：`skills/nsfc-research-content-writer/scripts/validate_skill.py`
  - 新增可追溯的 A/B 轮计划与测试会话目录：`skills/nsfc-research-content-writer/plans/`、`skills/nsfc-research-content-writer/tests/`

### Changed（变更）

- **systematic-literature-review v1.0.1 → v1.0.2**：表格样式规范化与导出链路加固（避免固定列宽溢出；template override 搜索目录生效；运行目录隔离更稳健）
- **systematic-literature-review v1.0.2 → v1.0.3**：检索源优化与自动降级（OpenAlex 主力 + Semantic Scholar 语义增强 + Crossref 兜底），新增速率限制/退避/健康监控保护与降级日志，单一查询检索在结果不足时自动补齐
- **systematic-literature-review v1.0.3 → v1.0.4**：摘要补充默认启用并加有限重试；对“摘要仍缺失”的条目标记低参考价值并在选文时尽量避免纳入最终参考文献
- **systematic-literature-review v1.0.4 → v1.0.5**：检索与摘要补齐的可控性/可复现性加固
  - `multi_query_search.py`：未提供查询时不再静默回退到硬编码查询，改为直接报错（避免误跑无关主题）
  - `openalex_search.py`：摘要补齐默认跟随 `config.yaml`，并支持 CLI 显式覆盖；补齐请求复用 `--cache-dir`
  - `multi_source_abstract.py`：补齐请求接入 `api_cache.py` 缓存，减少重复请求与限流风险；修复 OpenAlex `abstract_inverted_index=null` 导致的崩溃
  - `select_references.py`：摘要长度阈值默认跟随 `config.yaml:search.abstract_enrichment.min_abstract_chars`，保证“补齐判定/选文规避”口径一致
  - 文档同步：更新 `README.md`、`skills/README.md` 中的 skill 版本号展示
- **systematic-literature-review**：补充 LaTeX 表格样式最佳实践（列宽基于 `\textwidth` 按比例分配，避免固定 `p{}` 宽度溢出），并在写作前提示中加入强约束
- **systematic-literature-review**：加固导出链路与运行隔离（移除危险 `.gz` 清理项；template override 同级目录加入 TEXINPUTS/BSTINPUTS；PDF 输出跨卷移动更稳健；pipeline 子脚本统一 `cwd=work_dir` 且失败信息更可定位）

- **NSFC_General（2026）**：对齐 `projects/NSFC_General/template/2026年最新word模板-1.面上项目-正文-v2.pdf` 的页面边距（更新 `projects/NSFC_General/extraTex/@config.tex` 中 `geometry` 的右/上/下边距参数）
- **NSFC_General（2026）**：微调标题与正文提示语的版式间距（加粗 `\section` 标题、调整 `\section` 缩进到 2em，增大“提纲提示语”与首个 `\section` 之间的垂直间距，对部分 `\subsection` 标题内关键词加粗，并减小“（四）其他需要说明的情况”与首个 `\subsection` 之间的局部空白）
- **NSFC_Young（2026）**：对齐 `projects/NSFC_Young/template/2026年最新word模板-青年科学基金项目（C类）-正文-v2.pdf` 的页面边距与正文行距体系（更新 `projects/NSFC_Young/extraTex/@config.tex` 的 `geometry`、固定行距 22pt/段后 7.8pt、标题缩进与 `\frenchspacing`；同步修正 `projects/NSFC_Young/main.tex` 的提纲标题文字与断行，并按 v2 模板将“其他需要说明的情况”收敛为 `5. 其他。`）
- **NSFC_Young（2026）**：加粗 `\section` 标题，微调“提纲提示语”与首个 `\section` 的间距，减小 `\section` 与 `\subsection` 的间隙，进一步收紧段落间距（含 `\subsubsection` 后首段；避免 `\indent` 形成空段落造成额外空白），并对部分长标题用 `\linebreak{}` 精确控制断行（更贴近 Word 模板观感）
- **NSFC_Local（2026）**：对齐 `projects/NSFC_Local/template/2026年最新word模板-5.地区科学基金项目-正文.pdf` 的页面边距（更新 `projects/NSFC_Local/extraTex/@config.tex` 中 `geometry` 的右/上/下边距参数）

- **nsfc-research-content-writer v0.2.1**：补齐 auto-test 流水线脚手架与开发者自检闭环，强化 guardrails/targets/文档契约的一致性门禁
  - 新增 `skills/nsfc-research-content-writer/templates/`：A轮计划/B轮检查/TEST_PLAN/TEST_REPORT 模板（支持 A/B 轮 `--kind` 正确复跑）
  - 新增 `skills/nsfc-research-content-writer/scripts/create_test_session.py`：自建 A/B 轮会话骨架（不再依赖外部脚本）
  - 新增 `skills/nsfc-research-content-writer/scripts/check_project_outputs.py`：对 `project_root` 的只读输出自检（存在性、最小内容启发式、风险词扫描、严格门禁开关）
  - 新增 `skills/nsfc-research-content-writer/scripts/run_checks.py`：一键串联 `validate_skill.py` + 输出自检（支持 `--fail-on-risk-phrases`）
  - 更新 `skills/nsfc-research-content-writer/scripts/validate_skill.py`：增加 templates/plans/tests/scripts 门禁、guardrails↔targets 一致性校验、README/SKILL 关键入口防回退
  - 新增 `skills/nsfc-research-content-writer/references/output_skeletons.md`：三个输出文件最小结构骨架（含 `Sx/Ty/Vz` 回溯约定）
  - 新增/更新可追溯会话：`skills/nsfc-research-content-writer/plans/v202601142307.md` ~ `skills/nsfc-research-content-writer/plans/v202601142314.md`、`skills/nsfc-research-content-writer/plans/B轮-v202601142315.md` 与对应 `tests/` 目录

- **nsfc-justification-writer v0.7.7**：强化"科学问题与假说为核心"的设计理念，防止用方法学术语稀释立项依据主线
  - 更新 `references/dod_checklist.md`：新增"方法学术语使用规范（重要）"章节，明确禁止用方法术语撑段落主线，并提供检查方法
  - 更新 `references/theoretical_innovation_guidelines.md`：新增"方法学术语误用警示"章节，提供常见误用模式对比表格和检查清单
  - 更新 `prompts/writing_coach.txt`：在写作教练约束中增加"方法学术语使用规范"，引导用户聚焦科学问题
  - 新增 `references/methodology_term_examples.md`：提供详细的"方法术语撑主线"vs"科学问题驱动"四段闭环对比示例，含快速检查清单和学科适配参考
  - 更新 `SKILL.md`：在相关设计说明中新增 `methodology_term_examples.md` 引用

- **nsfc-justification-writer v0.7.6**：修复 P0 语法阻断并补齐 `style.mode` 写作导向开关（见下方 Changed/Fixed）

- 新增 `plans/v202601101300.md`：对 `skills/nsfc-justification-writer`「理论创新导向优化」做源代码审查，记录 P0 语法阻断缺陷与一致性改进建议

- 新增 `skills/nsfc-justification-writer/core/style.py`：写作导向（`style.mode`）统一入口，并提供可注入到 Prompt 的最小“写作导向”约束文本
- 新增 `tests/v202601101300/`：nsfc-justification-writer 轻量测试会话目录（含 `TEST_PLAN.md`、`TEST_REPORT.md`、测试输出与 `override.yaml`）

- **nsfc-justification-writer 理论创新导向优化**（v0.7.5）：新增 `references/theoretical_innovation_guidelines.md`，默认优先关注科学问题/假说的可证伪性、理论贡献的清晰性、验证维度的完备性（理论证明/定理/数值验证），而非工程落地细节
  - 更新 `references/dod_checklist.md`：在验收标准中新增"理论创新导向（默认）"要求
  - 更新 `references/info_form.md`：引导用户提供理论层面的信息（如"假设过强/框架不统一/因果缺失/界不紧"等理论瓶颈）
  - 更新 `templates/phrase_patterns.md`：新增理论创新导向的常用句式（如"理论空白/认知缺失/假设过强/框架不统一/因果缺失"等）
  - 更新 `prompts/writing_coach.txt`：在写作教练提示中融入理论创新导向
  - 更新 `core/writing_coach.py`：修改 `_suggest_questions()` 和 `_copyable_prompt()`，引导用户关注理论层面的问题
  - 更新 `core/review_advice.py`：修改 `_fallback_review_markdown()`，评审问题聚焦理论层面的瓶颈和验证方式
  - 更新 `SKILL.md`：在"目标输出（契约）"中新增"理论创新导向（默认）"说明，更新"推荐 `\\subsubsection` 标题与内容映射"表格

- 新增 `skills/nsfc-justification-writer/core/review_integration.py`：systematic-literature-review 集成模块，支持只读访问 systematic-literature-review 生成的文献综述目录
  - 目录检测：`detect_slr_directory(path)` 识别 systematic-literature-review 目录（支持运行中的 pipeline 和已完成的输出目录）
  - 目录分析：`analyze_review_directory(path)` 返回目录结构信息（.tex/.bib 文件列表、只读状态）
  - 引用验证：`validate_citation_consistency(tex_path, bib_path)` 检查 .tex 中的引用与 .bib 中的定义是否一致
  - 内容提取：`extract_citation_keys_from_bib()` 和 `extract_citations_from_tex()` 从文件中提取引用信息
- 新增 `skills/nsfc-justification-writer/tests/test_review_integration.py`：systematic-literature-review 集成模块的单元测试
- 新增 `skills/nsfc-justification-writer/scripts/validate_review_integration.py`：systematic-literature-review 集成功能验证脚本
- 更新 `skills/nsfc-justification-writer/config.yaml`：新增 `slr_integration` 配置节（启用/禁用集成、标记文件夹名称、只读保护、引用验证、文件模式）
- 更新 `skills/nsfc-justification-writer/SKILL.md`：新增"systematic-literature-review 集成（可选）"章节，说明识别标准、只读访问约束、使用场景和核心功能

- 更新 [README.md](README.md)：新增"技能生态系统"章节，按功能阶段分类展示多个 AI 技能（文献调研/标书准备/标书写作/模板开发）
- 更新 [README.md](README.md)：新增"推荐工作流"章节，展示完整的文献调研与标书写作工作流（含 Mermaid 流程图）
- 更新 [README.md](README.md)：技能表格新增"版本"列，显示各技能的版本号（v2.7.1、v0.7.3、v1.4.0 等）
- 更新 [skills/README.md](skills/README.md)：新增"技能依赖关系"章节，说明技能之间的协作关系和推荐使用顺序
- 更新 [skills/README.md](skills/README.md)：新增 nsfc-bib-manager 完整技能说明（功能、使用场景、Prompt 模板、技能特点）
- 新增 [CLAUDE.md](CLAUDE.md) 和 [AGENTS.md](AGENTS.md)：新增"技能版本号管理规范"章节，规定所有技能版本号统一通过 config.yaml 管理（Single Source of Truth）
- 新增 `skills/nsfc-bib-manager/config.yaml`：添加技能版本信息（v1.0.0）
- 新增 `skills/get-review-theme/config.yaml`：添加技能版本信息（v1.0.0）
- 更新 `skills/systematic-literature-review/config.yaml`：添加技能版本信息（v1.0.0）
- 更新 `skills/transfer_old_latex_to_new/config.yaml`：添加 skill_info 节，统一版本号为 v1.4.0
- **跨项目标准化**：将"技能版本号管理规范"有机融入 `/Volumes/2T01/winE/PythonCloud/Agents/pipelines/skills` 的 [AGENTS.md](/Volumes/2T01/winE/PythonCloud/Agents/pipelines/skills/AGENTS.md)，建立统一的技能版本管理标准（config.yaml 作为 SSoT，语义化版本命名，版本同步机制）

### Changed（变更）

- 更新 `skills/nsfc-justification-writer/config.yaml`：新增 `style.mode=theoretical|mixed|engineering`（默认 `theoretical`）
- 更新 `skills/nsfc-justification-writer/prompts/writing_coach.txt`、`skills/nsfc-justification-writer/prompts/review_suggestions.txt`：引入 `{style_preamble}` 注入，确保“理论创新导向/工程导向”约束在 AI 可用时也显式生效
- 更新 `skills/nsfc-justification-writer/core/writing_coach.py`、`skills/nsfc-justification-writer/core/review_advice.py`：将 `style.mode` 贯通到回退路径与 Prompt 填充，减少 AI/回退口径不一致
- 更新 `skills/nsfc-justification-writer/SKILL.md`、`skills/nsfc-justification-writer/README.md`：补充 `style.mode` 使用说明

- 更新 [README.md](README.md)：删除"快速开始指南"章节，保持文档简洁（详细使用示例请查阅各技能的 README.md）
- 更新 [README.md](README.md)：技能表格从 7 个扩展到 10 个，新增 nsfc-bib-manager、get-review-theme、guide-updater、complete_example
- 更新 [README.md](README.md)：修正技能状态：nsfc-bib-manager、get-review-theme、nsfc-justification-writer 均为 🚧 开发中
- 更新 [README.md](README.md)：更新 systematic-literature-review、nsfc-bib-manager、get-review-theme 版本号为 v1.0.0
- 更新 [skills/README.md](skills/README.md)：修正技能状态：nsfc-bib-manager、get-review-theme、nsfc-justification-writer 均为 🚧 开发中；guide-updater 为 ✅ 稳定（v1.0.0）
- 更新 [skills/README.md](skills/README.md)：技能编号从 9 个扩展到 10 个，新增 nsfc-bib-manager（编号 8），其他编号相应顺延
- 更新 [skills/README.md](skills/README.md)：新增"推荐工作流"章节，展示从文献调研到标书写作的完整流程（get-review-theme → systematic-literature-review → guide-updater → nsfc系列skills），并新增 get-review-theme 与 guide-updater 两个技能的说明，同时更新"技能类型说明"表

- 更新 `plans/v202601100803.md`：将"代码审查报告"重构为可执行的改进计划，去除时间线表述，补齐目标/范围/交付物/验收标准，并声明计划文档不记录版本历史（统一在 `CHANGELOG.md`）

- 新增 `plans/v202601100912.md`：审阅 `nsfc-justification-writer` 的安全措施与潜在缺陷，重点指出 `guardrails` 可能被 override 置空导致白名单失效，并给出按优先级排序的改进建议与验收标准

- 更新 `skills/nsfc-justification-writer/core/config_loader.py`：加固 `guardrails`（强校验 + 校验关闭时仍强制安全兜底），无 PyYAML 时跳过强校验并给出明确提示，新增 `prompts.*` 指向 skill_root 外路径的风险 warning
- 更新 `skills/nsfc-justification-writer/core/security.py`：`build_write_policy()` 不允许“空策略”，缺失/无效配置时回退到最小写入白名单与默认禁止规则
- 更新 `skills/nsfc-justification-writer/core/editor.py`、`skills/nsfc-justification-writer/core/versioning.py`、`skills/nsfc-justification-writer/core/hybrid_coordinator.py`、`skills/nsfc-justification-writer/scripts/run.py`：备份/回滚优先按目标相对路径定位（并兼容旧版按文件名回退），`apply_result.json` 记录 `target_relpath`，Crossref DOI 校验增加“将联网”的提示，`validate-config` 在无 PyYAML 时友好降级
- 新增 `tests/v202601100912/`：轻量测试计划/报告与脚本，验证 P0–P2 修复（所有中间文件限定在测试目录树内）

- 更新 [AGENTS.md](AGENTS.md) 和 [CLAUDE.md](CLAUDE.md)：在"变更记录规范"中新增"Skill 文档编写原则"子章节，明确 Skill 文档（SKILL.md）应始终展示最新状态，不包含版本标记等对 AI 执行无用的元信息；包括内容优先于版本、简洁标题、单一职责等原则及设计公式

- 更新 [AGENTS.md](AGENTS.md) 和 [CLAUDE.md](CLAUDE.md)：在"核心工作流/执行流程"中新增"计划制定原则"，要求任务按优先级从上到下罗列，不使用时间限制表述（如"第1-2周"、"第3-4周"等）；同时更新 CLAUDE.md 的"任务管理"章节同步此原则

- 更新 [README.md](README.md)：在"AI 模型配置建议"中补充 Claude Code + Claude 4.5 Opus "比较昂贵"的提示，新增 Codex CLI + GPT-5.2 Medium 的推荐组合，并在"API 获取建议"中补充 Packycode Codex 站点说明与扩写 DMXAPI 介绍
- 更新 [AGENTS.md](AGENTS.md)：修正目录结构，移除不存在的根级 `scripts/`，并说明脚本主要位于 `skills/*/scripts/`
- 更新 [CLAUDE.md](CLAUDE.md)：修正目录结构，移除不存在的根级 `scripts/`，并说明脚本主要位于 `skills/*/scripts/`
- 更新 `skills/make_latex_model/README.md`：补充“优先用 Prompt 调用 Skill”的推荐用法，并将脚本流程作为备选
- **nsfc-justification-writer v0.2.0** - 升级信息表与文档，并补齐可复现的“诊断→写入→验收”闭环
  - 更新 `skills/nsfc-justification-writer/references/info_form.md`：8 项信息表（必填/选填标识），与 `extraTex/1.1.立项依据.tex` 的 4 个 `\subsubsection` 对齐
  - 更新 `skills/nsfc-justification-writer/config.yaml` 与 `skills/nsfc-justification-writer/SKILL.md`：加入字数参数、术语 alias_groups、Tier1/Tier2（可选）诊断说明

- **nsfc-justification-writer v0.3.0** - 落地改进计划（P1–P3），主推“渐进式写作引导”
  - 更新 `skills/nsfc-justification-writer/scripts/run.py`：新增 `init/coach/review/refs` 与 `diff/rollback/list-runs` 子命令，`diagnose` 支持 `--html-report`
  - 更新 `skills/nsfc-justification-writer/core/term_consistency.py`：术语矩阵改为“按章节统计命中次数”，并识别“同章内不一致”
  - 更新 `skills/nsfc-justification-writer/core/reference_validator.py` 与 `skills/nsfc-justification-writer/core/diagnostic.py`：增加 DOI 缺失提示（可核验性增强）
  - 更新 `skills/nsfc-justification-writer/core/hybrid_coordinator.py`：`apply-section` 默认严格拒绝“缺失 bibkey 的 \\cite{...}”（防止幻觉引用）
  - 更新 `skills/nsfc-justification-writer/README.md`、`skills/nsfc-justification-writer/SKILL.md`、`skills/nsfc-justification-writer/scripts/README.md`：补齐渐进式写作闭环与新命令用法

- **nsfc-justification-writer v0.4.0** - 对齐配置/示例/体验与可扩展性
  - 更新 `skills/nsfc-justification-writer/SKILL.md`：补齐“4 段闭环”与 4 个 `\\subsubsection` 标题的映射表，并修正工作流编号
  - 更新 `skills/nsfc-justification-writer/templates/structure_template.tex`：为每个 `\\subsubsection` 增加写作要点注释
  - 更新 `skills/nsfc-justification-writer/core/example_matcher.py` 与 `skills/nsfc-justification-writer/examples/`：引入 `*.metadata.yaml` 关键词元数据，扩展多学科示例与匹配逻辑
  - 更新 `skills/nsfc-justification-writer/templates/html/report_template.html`：新增“点击行号复制/复制页面链接”的交互与更清晰的定位说明
  - 更新 `skills/nsfc-justification-writer/core/config_loader.py`、`skills/nsfc-justification-writer/config/presets/`、`skills/nsfc-justification-writer/scripts/run.py`：支持 `--preset` 学科预设与用户 `override.yaml` 配置覆盖（可用 `--no-user-override` 关闭）
  - 更新 `skills/nsfc-justification-writer/tests/`：补齐 diagnostic/writing_coach/example_matcher 单测与 integration 流程用例
  - 新增 `skills/nsfc-justification-writer/docs/`：补齐教程与架构说明

- **nsfc-justification-writer v0.5.0** - 按改良计划完成 P0–P2（稳定性/体验/可扩展性）
  - 更新 `skills/nsfc-justification-writer/core/config_loader.py` 与 `skills/nsfc-justification-writer/scripts/run.py`：新增 `validate-config` 配置校验命令，并默认做关键字段类型校验（可用 `NSFC_JUSTIFICATION_WRITER_DISABLE_CONFIG_VALIDATION=1` 关闭）
  - 更新 `skills/nsfc-justification-writer/core/ai_integration.py`、`skills/nsfc-justification-writer/core/hybrid_coordinator.py` 与 `skills/nsfc-justification-writer/scripts/run.py`：Tier2 支持分块处理与 `.cache/ai` 缓存（`--chunk-size/--max-chunks/--fresh`）
  - 更新 `skills/nsfc-justification-writer/core/term_consistency.py` 与 `skills/nsfc-justification-writer/config.yaml`：跨章节一致性升级为“研究对象/指标/术语”三维矩阵（`terminology.dimensions`）
  - 更新 `skills/nsfc-justification-writer/core/reference_validator.py`、`skills/nsfc-justification-writer/core/diagnostic.py` 与 `skills/nsfc-justification-writer/core/bib_manager_integration.py`：修复 bib DOI 解析并新增 DOI 格式异常提示，`refs` 支持可选 Crossref 联网校验（`--verify-doi crossref`）
  - 更新 `skills/nsfc-justification-writer/examples/` 与 `skills/nsfc-justification-writer/core/example_matcher.py`：新增 chemistry/biology/math 示例与领域加权提示
  - 新增 `skills/nsfc-justification-writer/docs/workflows/`：补齐典型工作流文档（已有草稿迭代、引用/DOI 核验）
  - 更新 `skills/nsfc-justification-writer/tests/`：补齐 AI 集成/配置校验/分块与缓存/术语维度等测试用例

- **nsfc-justification-writer v0.6.0** - 按 v202601091932 完成“AI 主导 + 优雅降级”的全缺陷修复
  - 新增 `skills/nsfc-justification-writer/core/io_utils.py`：流式读取与按 `\\subsubsection` 边界分块（降低大文件峰值内存）
  - 更新 `skills/nsfc-justification-writer/core/latex_parser.py`：替换正则解析为更稳健的结构解析（支持嵌套花括号/可选短标题/更可靠的注释剥离），并新增“标题候选 + AI 语义匹配”能力
  - 更新 `skills/nsfc-justification-writer/core/hybrid_coordinator.py` 与 `skills/nsfc-justification-writer/scripts/run.py`：`apply-section` 增强错误提示与修复建议，新增 `--suggest-alias`；Tier2 对超大文件优先流式分块
  - 更新 `skills/nsfc-justification-writer/core/term_consistency.py`、`skills/nsfc-justification-writer/core/writing_coach.py` 与 `skills/nsfc-justification-writer/config.yaml`：新增 `terminology.mode=auto|ai|legacy`，AI 可用时叠加语义一致性检查并自动回退到矩阵规则
  - 更新 `skills/nsfc-justification-writer/core/prompt_templates.py` 与 `skills/nsfc-justification-writer/core/config_loader.py`：Prompt 支持“路径或多行内联文本”，并支持按 `--preset` 变体覆盖（如 `prompts.tier2_diagnostic_medical`）
  - 更新 `skills/nsfc-justification-writer/core/example_matcher.py`：AI 语义示例推荐（带理由）+ 关键词 fallback
  - 更新 `skills/nsfc-justification-writer/config.yaml`、`skills/nsfc-justification-writer/core/config_loader.py` 与 `skills/nsfc-justification-writer/SKILL.md`：版本升级至 v0.6.0，并同步文档

- **nsfc-justification-writer v0.6.1** - 按 v202601092056 解决 P0–P2（安全/准确性/可维护性）
  - 更新 `skills/nsfc-justification-writer/core/config_loader.py` 与 `skills/nsfc-justification-writer/scripts/run.py`：无 PyYAML 时不再静默退化；内置安全兜底（guardrails 默认生效）并在 CLI 输出配置加载警告
  - 更新 `skills/nsfc-justification-writer/core/reference_validator.py` 与 `skills/nsfc-justification-writer/tests/test_reference_validator.py`：引用解析剔除注释与 `verbatim|lstlisting|minted` 环境，减少缺失 bibkey 误报
  - 新增 `skills/nsfc-justification-writer/core/quality_gate.py`，并更新 `skills/nsfc-justification-writer/core/hybrid_coordinator.py`、`skills/nsfc-justification-writer/scripts/run.py`：`apply-section --strict-quality` 对"本次新增正文"启用质量闸门（危险命令/绝对化表述可阻断；放宽引用约束时会提示建议开启）
  - 更新 `.gitignore` 与 `skills/nsfc-justification-writer/scripts/README.md`：明确并忽略 `runs/`、`.cache/` 等运行产物，避免污染工作区
  - 更新 `skills/nsfc-justification-writer/core/wordcount.py`、`skills/nsfc-justification-writer/core/diagnostic.py`、`skills/nsfc-justification-writer/scripts/run.py`：字数统计新增 `cjk_strip_commands` 口径（粗剔除命令/数学/类代码环境），并在输出中注明口径说明
  - 更新 `skills/nsfc-justification-writer/config.yaml`、`skills/nsfc-justification-writer/README.md` 与 `skills/nsfc-justification-writer/SKILL.md`：移除误导性的 `ai.min_success_rate_to_enable` 配置项，并明确 AI 可用性取决于 responder 注入（不可用自动回退）

- **nsfc-justification-writer v0.7.0** - 按 v202601100716 完成代码审查与清理（P0/P1 任务）
  - **配置 SSoT 重构**：确立 `config.yaml` 为单一真相来源（Single Source of Truth），精简 `core/config_loader.py` 的 `DEFAULT_CONFIG`（从约 100 行 → 10 行，仅保留安全关键项 guardrails），在两文件顶部添加 SSoT 声明注释
  - **残留代码清理**：删除未使用的 `core/intent_parser.py` 模块和 `prompts/intent_parse.txt`，移除 `core/errors.py` 中的 `NSFCJustificationWriterError` 基类（`SkillError` 直接继承 `Exception`），删除 `config.yaml` 中的 `latex_style_contract` 和 `quality_contract` 未使用配置项
  - **代码精简**：`core/config_loader.py`（-79 行，-20%）、`core/prompt_templates.py`（-19 行，-11%）、`config.yaml`（-18 行，-11%）

- **nsfc-justification-writer v0.7.1** - 按 v202601100716 完成 P2（可维护性/类型安全/文档）
  - 新增 `config.yaml` 的 `limits` 配置节：统一管理文件大小阈值、AI 输入上限、写作教练预览长度、字数目标范围
  - 新增 `skills/nsfc-justification-writer/core/config_access.py` 与 `skills/nsfc-justification-writer/core/limits.py`：消除 `config.get(... ) or {}` 访问模式，并替换硬编码阈值
  - 更新 `skills/nsfc-justification-writer/core/__init__.py`：补齐聚合导出并声明为内部入口
  - 新增设计说明：`skills/nsfc-justification-writer/references/dimension_coverage_design.md`、`skills/nsfc-justification-writer/references/boastful_expression_guidelines.md`
  - 轻量测试：新增 `tests/v202601100716/`（fixture + override + TEST_PLAN/TEST_REPORT）

- **nsfc-justification-writer v0.7.2** - 按 `plans/v202601100803.md` 完成 P0–P2（异常边界/Prompt SSoT/日志口径/配置访问统一）
  - 更新 `skills/nsfc-justification-writer/config.yaml` 与 `skills/nsfc-justification-writer/SKILL.md`：版本升级至 v0.7.2，并明确版本号呈现策略（口径集中）
  - 更新 `skills/nsfc-justification-writer/core/config_loader.py` 与 `skills/nsfc-justification-writer/README.md`：放宽 `terminology.dimensions` 为空 dict 的校验边界，并与文档口径一致
  - 更新 `skills/nsfc-justification-writer/core/prompt_templates.py` 与 `skills/nsfc-justification-writer/prompts/*.txt`：Prompt 改为文件单一来源，移除内联重复模板，并提供缺失提示兜底
  - 更新 `skills/nsfc-justification-writer/scripts/run.py` 与新增 `skills/nsfc-justification-writer/core/logging_utils.py`：统一 CLI 与核心模块的日志口径（stderr、级别随 `--verbose` 控制），减少 `print`/`logging` 混用
  - 更新 `skills/nsfc-justification-writer/core/*`：收紧多处 `except Exception`（优先使用更具体异常；必要处保留堆栈/日志），提升可诊断性
  - 更新 `skills/nsfc-justification-writer/core/*`：统一配置访问到 `core/config_access.py` 的 `get_*` 辅助方法，减少重复样式
  - 轻量测试：新增 `tests/v202601100803/`（fixture + override + TEST_PLAN/TEST_REPORT）

- **nsfc-justification-writer v0.7.3** - 落地 `plans/v202601100850.md` 的可选改进（文档透明度/AI 自检/预设示例）
  - 更新 `skills/nsfc-justification-writer/SKILL.md`：新增“AI 功能清单（是否需要 AI / Fallback 行为）”表格，并补充 `check-ai` 自检命令入口
  - 更新 `skills/nsfc-justification-writer/scripts/run.py`、`skills/nsfc-justification-writer/scripts/README.md`：新增 `check-ai` 子命令，用于诊断当前是否处于 responder 未注入的降级模式
  - 更新 `skills/nsfc-justification-writer/config/presets/medical.yaml`、`skills/nsfc-justification-writer/config/presets/engineering.yaml`：补齐更丰富的 `terminology.dimensions` 示例（降低用户配置门槛）
  - 更新 `skills/nsfc-justification-writer/docs/architecture.md`、`skills/nsfc-justification-writer/README.md`：同步预设覆盖口径说明与术语维度定制示例
  - 更新 `skills/nsfc-justification-writer/config.yaml`：版本升级至 v0.7.3

- **transfer_old_latex_to_new** - 脚本目录结构优化
  - 移动 `demo_core_features.py` → [scripts/demo.py](skills/transfer_old_latex_to_new/scripts/demo.py)：演示脚本归位到 scripts/ 目录
  - 移动 `run_tests.py` → [scripts/quicktest.py](skills/transfer_old_latex_to_new/scripts/quicktest.py)：快速测试工具重命名并归位
  - 更新两个脚本的路径引用(`Path(__file__).parent.parent`)以适配新位置
  - 新增 [scripts/README.md](skills/transfer_old_latex_to_new/scripts/README.md)：文档化所有脚本用途与使用场景
  - 技能根目录更清爽,仅保留配置文件和文档

- **transfer_old_latex_to_new** - LaTeX 中间文件隔离优化
  - 修改 [compiler.py](skills/transfer_old_latex_to_new/core/compiler.py)：使用 `-output-directory` 参数将 LaTeX 编译中间文件(.aux/.log/.bbl/.blg/.out/.toc 等)重定向到 `runs/<run_id>/logs/latex_aux/` 目录
  - 编译成功后自动复制 `main.pdf` 到项目根目录,方便用户查看
  - 项目目录保持清洁,不再产生编译"垃圾"文件
  - 更新 [SKILL.md](skills/transfer_old_latex_to_new/SKILL.md)：文档化目录结构与编译隔离机制

- **transfer_old_latex_to_new v1.3.1** - 易用性与可测试性增强
  - 新增一键迁移脚本：[scripts/migrate.sh](skills/transfer_old_latex_to_new/scripts/migrate.sh)（analyze→apply→(可选)compile）
  - CLI 增强：[scripts/run.py](skills/transfer_old_latex_to_new/scripts/run.py) 支持 `--runs-root` 隔离 runs 输出，并补充路径校验与更友好的错误提示
  - 进度反馈：[migrator.py](skills/transfer_old_latex_to_new/core/migrator.py) 集成进度条（rich 可用则使用，否则回退到文本）
  - 文档拆分：新增 [docs/](skills/transfer_old_latex_to_new/docs/) 并精简 [SKILL.md](skills/transfer_old_latex_to_new/SKILL.md)

- **transfer_old_latex_to_new v1.4.0** - P1 质量保障落地
  - 新增配置校验工具：[scripts/validate_config.py](skills/transfer_old_latex_to_new/scripts/validate_config.py)（类型/范围/编译序列等常见错误提前拦截）
  - runs 管理子命令：[scripts/run.py](skills/transfer_old_latex_to_new/scripts/run.py) 新增 `runs list/show/delete`（迁移历史可追溯，删除需 `--yes`）
  - 文档补齐：新增 [docs/faq.md](skills/transfer_old_latex_to_new/docs/faq.md) 与 [docs/case_study_2025_to_2026.md](skills/transfer_old_latex_to_new/docs/case_study_2025_to_2026.md)
  - 运行更干净：脚本默认不写 `__pycache__`（避免在项目目录产生中间文件）

## [0.7.0] - 2026-01-09

### Added（新增）
- **nsfc-justification-writer**：新增“内容维度覆盖检查”AI（价值/现状/科学问题/切入点），不依赖标题用词；新增“吹牛式表述”AI 语义识别（绝对化/填补空白/无依据夸大/自我定性），输出改写建议
- **nsfc-justification-writer**：新增字数解析器（优先解析用户意图/信息表中的目标字数/区间/±容差，兜底才用配置），coach 在 `--stage auto` 支持 AI 阶段判断

### Changed（变更）
- **nsfc-justification-writer**：默认 `strict_title_match=false`，结构检查以“至少 4 小节 + 内容维度覆盖”为主；质量配置改为高风险示例提示 + 可选 AI 语义阻断，写入质量闸门在 AI 可用时叠加语义检查
- **nsfc-justification-writer 文档**（README/SKILL）：同步新版工作流与能力亮点，明确 AI 依赖“原生智能环境”无需外部 API Key

### Added（新增）

- 新增 `make_latex_model` 入口文档：`skills/make_latex_model/README.md`

- 新增迁移验证记录：`tests/v202601081624/TEST_REPORT.md`

- 新增 NSFC 2026 新模板写作 Skill 迁移建议计划（已脱敏）：`plans/v202601081910.md`

- 新增 nsfc-justification-writer v0.6.0 代码审查与改良计划：`plans/v202601092056.md`

- **nsfc-justification-writer v0.2.0** - 硬编码确定性能力与配套脚本
  - 新增脚本入口：`skills/nsfc-justification-writer/scripts/run.py`（diagnose/wordcount/terms/apply-section）
  - 新增核心模块：`skills/nsfc-justification-writer/core/`（结构解析、引用核验、字数统计、术语矩阵、安全写入、可观测性）
  - 新增单元测试：`skills/nsfc-justification-writer/tests/`（pytest）
  - 新增示例与模板：`skills/nsfc-justification-writer/examples/`、`skills/nsfc-justification-writer/templates/`
  - 新增诊断示例：`skills/nsfc-justification-writer/references/diagnostic_examples.md`

- **nsfc-justification-writer v0.3.0** - 渐进式写作与可视化/版本能力
  - 新增渐进式写作引导：`skills/nsfc-justification-writer/core/writing_coach.py`（coach）
  - 新增交互式信息表收集：`skills/nsfc-justification-writer/core/info_form.py`（init --interactive）
  - 新增评审建议生成：`skills/nsfc-justification-writer/core/review_advice.py`（review）
  - 新增 HTML 诊断报告：`skills/nsfc-justification-writer/core/html_report.py`、`skills/nsfc-justification-writer/templates/html/report_template.html`
  - 新增版本 diff/回滚：`skills/nsfc-justification-writer/core/versioning.py`
  - 新增示例推荐：`skills/nsfc-justification-writer/core/example_matcher.py`（coach --topic / examples）
  - 新增 prompts 外部化：`skills/nsfc-justification-writer/prompts/`
  - 新增端到端测试：`skills/nsfc-justification-writer/tests/e2e/test_cli_flow.py`

- 新增 NSFC 2026 新模板写作主技能（MVP，按新板块契约落到 `extraTex/*.tex`）
  - `skills/nsfc-justification-writer/`：对应 `（一）立项依据`
  - `skills/nsfc-research-content-writer/`：对应 `（二）研究内容`（并编排创新点与年度计划）
  - `skills/nsfc-research-foundation-writer/`：对应 `（三）研究基础`（并编排工作条件与风险应对）

- 新增 `transfer_old_latex_to_new` v1.3.0 详细改进计划：`plans/v202601081102.md`
  - **核心修复**：移除所有 AI 功能占位符，实现真实的 AI 集成
  - **AI 集成层**：创建 `core/ai_integration.py`，利用 Claude Code/Codex 当前环境（无需额外配置）
  - **迁移策略**：实现一对多/多对一迁移（`core/strategies.py`）
  - **模块集成**：集成 `ContentOptimizer`、`ReferenceGuardian`、`WordCountAdapter` 到主流程
  - **CLI 扩展**：添加 `--optimize`、`--adapt-word-count`、`--ai-enabled` 选项
  - **实施计划**：4 个 Sprint，预计 6-8 小时
  - **问题诊断**：彻底代码审查发现 AI 功能虚假实现、依赖不存在模块、迁移策略不完整

- 新增 `transfer_old_latex_to_new` v1.3.0 优化计划：`plans/v202601081002.md`
  - **性能优化**：引入分层缓存机制、批量 AI 调用、并行化处理（预期性能提升 5-10 倍）
  - **质量保证**：建立测试体系（pytest，目标覆盖率 80%）
  - **用户体验**：实时进度反馈、细粒度错误恢复、简化配置（预设模板）
  - **高级功能**：智能版本检测、AI 写作风格评分、插件化架构
  - **用户痛点彻底解决**（3 个新增优化项）：
    - ✅ **优化项 12：字数自动适配** - 自动检测旧字数 → 新字数，调用 AI 或写作技能扩展/精简
    - ✅ **优化项 13：引用强制保护** - AI 调用前强制保护所有引用，输出后验证并自动修复
    - ✅ **优化项 14：AI 智能优化写作** - AI 自动识别并修复冗余、逻辑、证据、清晰度、结构问题
  - **分阶段实施计划**：5 个阶段，预计 10-13 周（新增 3 个核心优化项）

- 新增 `transfer_old_latex_to_new` 工程化落地优化计划：`plans/v202601080843.md`
- **transfer_old_latex_to_new（MVP 可执行闭环）**
  - 新增可执行脚本入口：`skills/transfer_old_latex_to_new/scripts/run.py`（`analyze/apply/compile/restore`）
  - 新增 `runs/<run_id>/` 工作空间：结构分析、迁移计划、日志、交付物与快照备份集中管理
  - 新增核心模块：结构分析、映射生成、迁移执行（原子写入+白名单保护）、编译日志摘要、交付物生成
  - 新增最小烟雾测试：`skills/transfer_old_latex_to_new/tests/test_smoke.py`

- **transfer_old_latex_to_new v1.1.0** - 🤖 AI 驱动映射引擎：让 AI 真正理解文件映射关系
  - **移除硬编码相似度公式**：不再使用固定权重（`0.7 * stem + 0.2 * title + 0.1 * content`）计算相似度
  - **AI 语义判断**：让 AI 真正理解文件内容（文件名、章节结构、内容语义、迁移合理性）后判断映射关系
  - **映射引擎重构**：
    - 新增 `_build_file_context()`: 为 AI 构建文件上下文（路径、结构、摘要、预览）
    - 新增 `_ai_judge_mapping()`: AI 判断映射关系的异步函数（占位符，待集成实际 AI 调用）
    - 新增 `compute_structure_diff_async()`: 异步版本的结构差异分析
    - 保留 `_fallback_score_pair()`: 当 AI 不可用时使用简单启发式规则
  - **配置文件优化**：
    - 移除硬编码权重配置（`title_similarity_weight`、`content_similarity_weight` 等）
    - 新增 `mapping.strategy`: `ai_driven`（AI 语义判断）/ `fallback`（简单启发式）
    - 新增 `mapping.thresholds`: AI 判断阈值（high/medium/low）
    - 新增 `mapping.fallback`: 回退策略配置（文件名匹配、包含关系、Jaccard 相似度）
  - **文档更新**：
    - SKILL.md 新增"AI 语义判断"章节，详细说明 AI 判断流程和判断维度
    - README.md 更新核心能力，突出"AI 语义映射"
  - **版本升级**：v1.0.0 → v1.1.0

- **transfer_old_latex_to_new v1.2.0** - 📦 资源文件智能处理：保证引用完整性
  - **核心问题解决**：迁移过程自动处理资源文件（图片、代码等），保证引用完整性
  - **新增资源文件扫描**：
    - 新增 `core/resource_manager.py` 模块：资源文件扫描、复制、完整性验证
    - 支持资源类型：
      - 图片：`\includegraphics{figures/fig1.pdf}`
      - 代码：`\lstinputlisting{code/algo.py}`
      - 其他文件：`\import{path}{file}`

### Fixed（修复）

- **systematic-literature-review**：修复参考文献 DOI 链接显示逻辑——当 BibTeX 同时包含 `doi` 与 `url`（如 OpenAlex）时，PDF 参考文献优先显示 `https://doi.org/{doi}`，并将 DOI resolver 升级为 HTTPS；BibTeX 保留原始 `url` 用于追溯
  - 更新 `skills/systematic-literature-review/latex-template/gbt7714-nsfc.bst`：`output.url.or.doi` 改为 DOI 优先，`cap.doi.url` 改为 `https://doi.org/`
  - 更新 `skills/systematic-literature-review/scripts/select_references.py`：生成 BibTeX 时同步转义 `%/_/#/$` 等常见 LaTeX 特殊字符，降低 BibTeX/LaTeX 编译阻断风险
  - 更新 `skills/systematic-literature-review/scripts/compile_latex_with_bibtex.py`：修复 `TEXINPUTS/BSTINPUTS` 未保留 TeX 默认搜索路径导致 `article.cls not found`；并在 env 注入时改用 `shlex.quote()`，避免路径包含空格/单引号导致 shell 命令拼接失败
  - 更新 `skills/systematic-literature-review/SKILL.md`：补充“DOI 链接显示”说明

- **systematic-literature-review**：修复 `validate_review_tex.py` 与 `validate_citation_distribution.py` 在 `--help` 下因未转义 `%` 导致 `argparse` 崩溃的问题
  - 更新 `skills/systematic-literature-review/scripts/validate_review_tex.py`：对 help 文本中的 `70%/25%/<5%` 做 `%%` 转义
  - 更新 `skills/systematic-literature-review/scripts/validate_citation_distribution.py`：对 epilog 文本中的目标百分比做 `%%` 转义（保留 `%(prog)s` 占位符）

- **make_latex_model**：修复 `skills/make_latex_model/scripts/analyze_pdf.py` 在未指定 `--project/--output` 时输出路径类型错误导致无法保存 `*_analysis.json`
- **make_latex_model**：修复 `skills/make_latex_model/scripts/prepare_main.py` 预处理时误注释 `\input{extraTex/@config.tex}` 导致“仅标题”编译失败

- 修复 `skills/nsfc-justification-writer/core/writing_coach.py`、`skills/nsfc-justification-writer/core/review_advice.py` 的字符串未转义导致的 `SyntaxError`，恢复脚本入口可运行性
- 更新 `skills/nsfc-justification-writer/core/config_loader.py`：新增 `style` 配置字段的轻量校验，避免无效取值静默生效

- **transfer_old_latex_to_new** - 修复 `compile_project()` 在 `-output-directory` 隔离中间文件时，`bibtex` 因工作目录切换导致无法定位 `.bst/.bib` 的问题
  - 在 `bibtex` 步骤注入 `BSTINPUTS/BIBINPUTS` 搜索路径（指向项目根目录），确保可读取 `bibtex-style/` 与 `references/`
  - 编译成功判定纳入 `bibtex` 返回码，避免“引用未生成但仍显示成功”

- **transfer_old_latex_to_new** - 修复 `ReferenceGuardian.restore_references()` 在 Python 3.12 下替换 `\\ref/\\cite` 等内容时触发 `re.error: bad escape` 的问题
  - **增强迁移流程**（`core/migrator.py`）：
    - 第一步：迁移 `.tex` 内容文件
    - 第二步：扫描旧项目的资源文件
    - 第三步：复制资源文件到新项目（只复制缺失的，避免覆盖）
    - 第四步：验证新项目中的资源引用完整性
  - **LaTeX 工具增强**（`core/latex_utils.py`）：
    - 新增 `extract_graphics()`: 提取图片引用
    - 新增 `extract_lstinputlisting()`: 提取代码文件引用
    - 新增 `extract_imports()`: 提取 LaTeX import 路径
    - 新增 `extract_all_resource_paths()`: 提取所有外部资源文件路径
  - **配置优化**：
    - `migration.figure_handling`: `copy`（复制，默认推荐）/ `link`（软链接）/ `skip`（跳过）
  - **结果报告增强**：
    - `ApplyResult` 新增 `resources` 字段，包含资源处理详情
    - 扫描摘要：总资源数、缺失数、涉及目录
    - 复制摘要：复制数、跳过数、失败数、创建的目录
    - 验证摘要：有效资源数、缺失资源数、损坏的引用
  - **文档更新**：
    - SKILL.md 新增"资源文件处理"章节
    - 核心模块索引新增"资源管理"模块
  - **版本升级**：v1.1.0 → v1.2.0

- **complete_example v1.1.0** - 🔒 安全增强：系统文件保护与格式注入扫描
  - **SecurityManager 模块**：统一的安全检查和访问控制
    - 系统文件黑名单保护（`main.tex`、`@config.tex` 绝对禁止修改）
    - SHA256 哈希校验（检测文件是否被外部篡改）
    - 格式注入检测（扫描并自动清理危险的格式指令）
    - 白名单模式匹配（只允许编辑符合正则表达式的文件）
    - 违规报告生成（详细的安全违规日志）
  - **FormatGuard 增强**：集成 SecurityManager 进行预检查
    - 编辑前自动进行系统文件检查和完整性校验
    - 应用前自动进行格式注入检查和清理
    - 支持自动清理模式（默认启用）
  - **配置文件更新**：新增 `security` 配置节
    - 系统文件黑名单和白名单配置
    - 格式关键词黑名单配置
    - 文件完整性校验配置
    - 内容安全扫描配置
  - **文档更新**：
    - SKILL.md 新增"分层安全保护"章节
    - 详细说明三层安全架构（系统文件/用户内容/内容扫描）
    - 配置示例和使用说明

- **complete_example v1.0.0** - AI 增强版 LaTeX 示例智能生成器
  - **核心功能**：AI 驱动的示例内容生成，支持用户自定义叙事提示
  - **用户提示机制**：允许通过 `narrative_hint` 参数指定研究主题、方法、场景，AI 根据提示编造合理的示例内容
  - **运行目录隔离**：所有运行输出（备份、日志、分析结果）放在 `skills/complete_example/runs/<run_id>/` 目录中，完全不对项目目录造成污染
  - **架构设计**：AI 负责"语义理解"，硬编码负责"结构保护"，有机协作
  - **核心模块**：
    - `SemanticAnalyzer`：AI 语义分析器（章节主题理解、资源相关性推理）
    - `AIContentGenerator`：AI 内容生成器（叙述性文本生成、自我优化）
    - `ResourceScanner`：资源扫描器（figures、code、references）
    - `FormatGuard`：格式守护器（格式保护、哈希验证、自动回滚）
    - `CompleteExampleSkill`：主控制器（完整工作流协调）
  - **工具模块**：LLM 客户端、LaTeX 解析、BibTeX 解析、文件操作

### Fixed（修复）

- 修复并落地 `transfer_old_latex_to_new`（对齐 `plans/v202601081102.md` 的核心问题）
  - 新增 `skills/transfer_old_latex_to_new/core/ai_integration.py`：统一 AI 接口，未接入真实 AI 时优雅降级
  - 修复错误导入：移除 `get_ai_config` 与 `skill_core` 依赖，避免运行时 `ModuleNotFoundError`
  - 集成可选后处理：`apply_plan()` 支持 `--optimize` 内容优化与 `--adapt-word-count` 字数适配
  - CLI 扩展：`skills/transfer_old_latex_to_new/scripts/run.py` 新增 `--no-ai/--optimize/--adapt-word-count`
  - 同步更新文档与测试：保证默认环境下功能可用且用法一致
  - **使用示例**：基本用法、高级用法（医疗影像、材料科学、临床试验、传统 ML）
  - **配置文件**：完整的 YAML 配置（LLM、参数、运行管理、资源扫描、格式保护、AI 提示词）
  - **测试框架**：单元测试、集成测试、AI 能力测试
  - **文档**：SKILL.md、README.md、设计计划 [plans/v202601071300.md](plans/v202601071300.md)

- **make_latex_model v2.7.0** - 全自动化工作流程优化
  - **PDF 基准获取增强**：
    - 步骤 2.1 改为"获取 Word PDF 基准"（原"生成 Word PDF 基准"）
    - 新增"方案 0：用户已提供 PDF"作为首选方案（最快，零操作）
    - 调整 LibreOffice 为"方案 1"，Microsoft Word COM 为"方案 2"
    - 渲染质量对比表格新增"用户已提供 PDF"条目
    - Q1 常见问题同步更新：支持用户已提供 PDF 或自动生成
  - **文档优化**：
    - 移除所有"在 Microsoft Word 中打开模板"等手动操作说明
    - Q1 重写：强调完全自动化的工作流程
    - 删除步骤 2.3"手动测量（备用方案，不推荐）"章节（AI 无法执行）
    - 删除"迁移说明"章节（工作空间管理章节）
    - 步骤 2.5 新增 `--auto-convert` 自动转换 .doc 为 .docx
    - 移除年份偏倚：将所有具体年份（2026）改为通用表述（2025/最新模板/YYYY-MM-DD）
    - 修正标题层级：移除所有子章节的冗余编号前缀（如 3.5.1→、4.1→、5.0→）
  - **核心理念**：本技能为全自动化技能，用户无需手动操作任何 GUI 工具

- **make_latex_model v2.6.0** - 文档格式优化
  - 移除 SKILL.md 中所有主要章节标题前的序号（如 `## 1)` → `##`）
  - 更新文档目录中的锚点链接以匹配新的标题格式
  - 提升文档可读性和链接稳定性

- **make_latex_model v2.5.0** - HTML 可视化报告与自动修复建议
  - **Phase 2: HTML 报告增强**：
    - 新增 `render_formatted_text_html()`：将格式片段渲染为 HTML（加粗用 `<b>` 标签）
    - 新增 `generate_html_report_with_format()`：生成包含格式对比的 HTML 报告
    - HTML 报告支持：
      - 加粗文本可视化（`<b>` 标签深蓝色显示）
      - 并排对比（Word vs LaTeX）
      - 格式差异高亮（黄色背景 + 详细位置标注）
      - 响应式设计，最大宽度 1400px
      - 四种统计卡片：完全匹配、文本差异、格式差异、仅在一方
  - **Phase 3: 自动修复建议**：
    - 新增 `generate_latex_fix_suggestions()`：生成 LaTeX 修复代码
    - `compare_headings.py` 新增 `--fix-file` 参数：输出修复建议到指定文件
    - 自动生成可直接复制的 `\section{}` 和 `\subsection{}` 代码
    - 根据 Word 格式生成正确的 `\textbf{}` 标记
  - **命令行增强**：
    - `--check-format` 模式下支持 HTML 报告（移除"后续版本增强"的临时提示）
    - 新增 `--fix-file` 参数，与 `--check-format` 配合使用
  - **文档更新**：
    - SKILL.md 步骤 2.5 新增 HTML 可视化报告使用说明（第 5 条）
    - SKILL.md 步骤 2.5 新增 LaTeX 修复建议使用说明（第 6 条）
    - description 更新：添加"HTML 可视化报告、LaTeX 自动修复建议"
  - **完整实现计划 v202601060836**：
    - ✅ Phase 1（核心功能）：100% 完成
    - ✅ Phase 2（可视化增强）：100% 完成
    - ✅ Phase 3（自动修复建议）：100% 完成

- **make_latex_model v2.4.0** - 标题格式对比功能增强
  - **格式对比核心功能**：
    - 新增 `extract_formatted_text_from_word()`：从 Word 段落提取格式化文本片段（加粗信息）
    - 新增 `extract_formatted_text_from_latex()`：从 LaTeX 代码解析 `\textbf{}` 格式
    - 新增 `compare_formatted_text()`：对比 Word 和 LaTeX 的格式一致性
  - **命令行参数扩展**：
    - `compare_headings.py` 新增 `--check-format` 参数：启用格式（加粗）对比
    - 支持向后兼容：默认行为保持不变，仅检查文本内容
  - **报告增强**：
    - 新增 `generate_text_report_with_format()`：生成包含格式差异的文本报告
    - 格式差异报告显示：Word 和 LaTeX 的加粗位置对比、具体差异位置标注
  - **文档更新**：
    - SKILL.md 步骤 2.5 新增格式对比使用说明
    - description 更新：添加"标题格式对比（加粗）"功能描述

- **make_latex_model v2.3.0** - 迭代优化闭环与工作空间重构
  - **工作空间管理（Phase 0）**：
    - 新增 `core/workspace_manager.py`：统一管理 skill 工作目录，避免污染用户项目目录
    - 工作空间结构：`workspace/{project}/baseline/`、`iterations/`、`reports/`、`cache/`、`backup/`
    - 支持旧路径自动迁移和缓存清理策略
  - **基础功能增强（Phase 1）**：
    - 新增 `scripts/prepare_main.py`：预处理 main.tex，自动注释/恢复 `\input{}` 行
    - 新增 `scripts/generate_baseline.py`：自动检测模板文件，使用 Word/LibreOffice 转换为 PDF
    - 新增 `scripts/convergence_detector.py`：综合判断迭代优化是否达到停止条件
    - 新增 `scripts/enhanced_optimize.py`：一键式迭代优化入口
  - **智能调整（Phase 2）**：
    - 新增 `scripts/intelligent_adjust.py`：分析像素差异，根据差异特征推断参数调整建议
  - **配置扩展**：
    - `config.yaml` 新增 `workspace` 配置节（工作空间路径、清理策略）
    - `config.yaml` 新增 `iteration` 配置节（最大迭代、收敛阈值、调整粒度、像素对比配置）
    - `config.yaml` 新增 `baseline` 配置节（转换器优先级、质量验证）
  - **文档更新**：
    - SKILL.md 新增「0.7) 工作空间说明」章节
    - SKILL.md 新增「3.5) 迭代优化闭环」章节

### Changed（变更）

- **项目指令文档** - 新增 LaTeX 编译4步法规范
  - **CLAUDE.md 和 AGENTS.md**：新增「LaTeX 编译规范」章节
    - 说明 PDF 渲染4步法：`xelatex → bibtex → xelatex → xelatex`
    - 每步的作用说明（生成辅助文件、处理参考文献、解析文献引用、确保交叉引用正确）
    - 使用原则：修改参考文献后必须完整执行4步，仅修改正文时可省略 bibtex 步骤
  - **有机整合**：与现有「LaTeX 标题换行控制」章节并列，形成完整的 LaTeX 操作规范

- **项目指令文档** - 指令规范精炼与一致性增强
  - **CLAUDE.md 和 AGENTS.md**：精炼「项目目标」「联网与搜索」表述，补充“不自动清理/删除 `.DS_Store`”边界，并统一核心章节一致性提示

### Changed（变更）

- **make_latex_model v2.7.1** - 修复验证器运行入口
  - 修复 `scripts/run_validators.py` 的导入路径，避免 `validators` 相对导入报错

- **make_latex_model v2.2.1** - SKILL.md 文档结构优化（方案 A）
  - **P1 文档优化**：
    - 合并重复的验证清单：4.3 节改为引用第 6 节，减少约 30 行重复内容
    - 整合 Q1、Q1.1、Q2 为一个完整的"Word 打印 PDF"问题，消除主题重复
    - 整合 AI 决策点规范（0.7 节）到第 3 节执行流程的相应步骤中，提升上下文连贯性
    - 新增文档目录结构，提升导航性
  - **优化效果**：
    - 消除约 50+ 行重复内容
    - 提升信息密度和可读性
    - 保持单文档结构，便于 AI 理解

- **make_latex_model v2.2.0** - 架构澄清：AI 与硬编码协调改进
  - **P0 架构澄清**：
    - 在 SKILL.md 中新增「0.6) 执行模式说明」章节：明确硬编码工具与 AI 规划的执行边界
    - 在 SKILL.md 中新增「0.7) AI 决策点规范」章节：定义 4 个关键决策点的输入、逻辑和输出
    - 新增 `scripts/check_state.py`：项目状态检查工具，AI 执行前必须运行的预检查脚本
    - 在「执行流程」中新增「步骤 0：预检查」，强制 AI 在优化前执行状态检查

### Added（新增）

- **make_latex_model**：新增 `check_state.py` 状态检查工具
  - 检查项目是否已初始化（@config.tex 存在）
  - 检查是否有 Word PDF 基准文件
  - 检测基准来源（Word PDF / QuickLook / 未知）
  - 检查编译状态和 PDF 分析结果
  - 生成状态报告并导出 JSON 供 AI 读取

### Changed（变更）

- 更新 `AGENTS.md` 与 `CLAUDE.md` 的目录结构示例，使 `skills/` 示例与当前仓库实际技能（`make_latex_model`）一致
- **make_latex_model**：融入 `analyze_pdf.py` 工具到工作流
- **make_latex_model v2.1.1** - 代码库优化与配置清理
  - **P0 紧急修复**：
    - 修复 SKILL.md 版本号不一致（v1.4.0 → v2.1.0）
    - 清理已追踪的系统垃圾文件（.DS_Store 和 __pycache__）
    - 优化 .gitignore 配置（新增虚拟环境、技能输出目录、macOS 补充规则）
  - **P1 核心优化**：
    - 实施配置继承方案：删除 base.yaml 中重复的 validation.tolerance 和 validation.acceptance_priority 配置
    - 统一颜色定义到单一数据源：在 config.yaml 中新增 style_reference.colors 配置，从 base.yaml 中删除重复的颜色定义
  - **P2 次要改进**：
    - 统一 config.yaml 和 SKILL.md 的技能描述文本
    - 清理 output 目录中的运行时生成文件，添加 README.md 说明文档
  - 在 `SKILL.md` 步骤 2 中新增 "2.2 自动提取样式参数" 小节
  - 在 `scripts/README.md` 中新增 `analyze_pdf.py` 工具文档（作为工具 #1）
  - 优化 `analyze_pdf.py`：添加依赖检查、文件验证、改进输出格式
  - 调整工具编号：`validate.sh` (#2)、`benchmark.sh` (#3)、`extract_headings.py` (#4)、`compare_headings.py` (#5)

### Added（新增）- Skills

- **make_latex_model v2.1.0** - 核心功能完善与工作流优化
  - **验证器插件系统（任务 1.1）**：
    - 实现 `CompilationValidator`：编译状态验证（第一优先级）
    - 实现 `StyleValidator`：样式参数验证（行距、颜色、边距、字号、标题格式）
    - 实现 `HeadingValidator`：标题文字验证（集成 compare_headings.py）
    - 实现 `VisualValidator`：视觉相似度验证（PDF 页面尺寸、每行字数统计）
    - 新增 `scripts/run_validators.py`：Python 验证器运行器
  - **PDF 像素对比工具（任务 1.2）**：
    - 新增 `scripts/compare_pdf_pixels.py`：像素级 PDF 对比工具
    - 支持批量对比多页 PDF
    - 生成 HTML 差异报告和差异热图
    - 计算差异像素比例（changed_ratio）
  - **样式配置双向同步工具（任务 1.3）**：
    - 新增 `scripts/sync_config.py`：LaTeX 配置解析与同步工具
    - 解析 `@config.tex` 中的颜色、字号、边距、行距、标题格式
    - 对比 PDF 分析结果与 LaTeX 配置
    - 支持自动修改和预览模式
  - **一键式优化流程（任务 2.1）**：
    - 新增 `scripts/optimize.py`：完整优化流程自动化
    - 8 步流程：分析 Word PDF → 提取标题 → 对比样式 → 生成建议 → 应用修改 → 编译 → 验证 → 生成报告
    - 新增 `scripts/optimize.sh`：Shell 脚本入口
  - **交互式配置向导（任务 2.2）**：
    - 新增 `scripts/setup_wizard.py`：交互式项目配置向导
    - 引导用户完成项目信息、模板选择、优化级别、Word 模板、高级选项
    - 自动生成项目结构和配置文件
  - **Windows 兼容性改进（任务 3.1）**：
    - 新增 `scripts/validate.bat`：Windows 验证脚本
    - 新增 `scripts/benchmark.bat`：Windows 性能测试脚本
    - 新增 `scripts/optimize.bat`：Windows 优化脚本
  - **字体路径自动检测（任务 3.2）**：
    - 新增 `core/font_detector.py`：跨平台字体检测模块
    - 支持 macOS/Windows/Linux 三大操作系统
    - 自动检测常见中文字体（KaiTi、SimSun、SimHei 等）
    - 自动检测常见英文字体（Times New Roman、Arial 等）

- **make_latex_model v2.0.0** - 通用化重构
  - **核心架构重构**：实现配置与代码分离，支持任意 LaTeX 模板
  - **分层配置系统**：
    - `config.yaml`：技能默认配置
    - `templates/`：模板配置目录（支持继承）
    - `.template.yaml`：项目本地配置
  - **新增核心模块**：
    - `core/config_loader.py`：配置加载器（支持三层合并和继承）
    - `core/template_base.py`：模板基类
    - `core/validator_base.py`：验证器基类
  - **模板配置**：
    - `templates/nsfc/base.yaml`：NSFC 基础模板
    - `templates/nsfc/young.yaml`：青年基金模板
    - `templates/nsfc/general.yaml`：面上项目模板
    - `templates/nsfc/local.yaml`：地区基金模板
  - **工具脚本重构**（支持命令行参数）：
    - `validate.sh --project PATH [--template NAME]`
    - `extract_headings.py --file PATH [--project PATH] [--config PATH]`
  - **向后兼容**：现有 NSFC 项目无需修改即可继续使用
  - **测试覆盖**：新增向后兼容性测试 `tests/test_backward_compat.py`

- **make_latex_model v1.4.0** - 标题文字对齐功能
  - 新增自动化工具：
    - `scripts/extract_headings.py`：从 Word/LaTeX 提取标题文字
    - `scripts/compare_headings.py`：对比标题文字差异，生成 HTML 可视化报告
  - 修订核心目标：明确"标题文字对齐"与"样式参数对齐"的双重目标
  - 修订绝对禁区：允许修改 `main.tex` 中的标题文本，禁止修改正文内容
  - 集成到 `validate.sh`：自动检查标题文字一致性
  - 解决问题：修复了对"样式对齐"的理解偏差，现在同时关注样式参数和标题文字分布

## [1.0.0] - 2026-01-05

### Added（新增）

- 初始化 AI 项目指令文件
- 生成 `CLAUDE.md`（Claude Code 项目指令）
- 生成 `AGENTS.md`（OpenAI Codex CLI 项目指令）
- 配置项目工程原则和工作流

### Changed（变更）

---

## 记录规范

每次修改 `CLAUDE.md` 或 `AGENTS.md` 时，请按以下格式追加记录：

```markdown
## [版本号] - YYYY-MM-DD

### Changed（变更）
- 修改了 XXX 章节：原因是 YYY，具体变更内容是 ZZZ

### Added（新增）
- 新增了 XXX 功能/章节：用途是 YYY

### Fixed（修复）
- 修复了 XXX 问题：表现是 YYY，修复方式是 ZZZ
```

### 版本号规则（可选）

- **主版本号**：重大架构变更
- **次版本号**：新增功能或章节
- **修订号**：修复问题或微调

### 变更类型说明

| 类型 | 说明 |
|------|------|
| Added | 新增的功能或章节 |
| Changed | 对现有功能或内容的变更 |
| Deprecated | 即将移除的功能（警告） |
| Removed | 已移除的功能 |
| Fixed | 修复的问题 |
| Security | 安全相关的修复 |

---

## 模板版本历史

### 2025-03-12：v2.5.0 重大更新

> :warning: 修复：面上、地区基金"3.正在承担的与本项目相关的科研项目"段落结尾缺少分号

![mQW1QFdXDq](https://chevereto.hwb0307.com/images/2025/03/12/mQW1QFdXDq.png)

### 2025-03-01：v2.4.6

- 优化：`\kaishu` → `\templatefont` 增强字体兼容性
- 优化：改善 `subsubsection` 序号显示
- 修复：系统 TimesNewRoman 适用于 macOS/Overleaf

### 2025-01-25：v2.4.2

- 修复：面上和地区基金 `font/` 文件夹缺失
- 修复：面上模板 `(建议 8000 字以下)` 未加粗
- 优化：增强 Overleaf/macOS 平台兼容

### 2025-01-24：2025 版发布

完整更新说明详见博客文章《[国家自然科学基金的 LaTeX 模板](https://blognas.hwb0307.com/skill/5762)》。
