# 架构说明：nsfc-justification-writer

目标：把“立项依据”的写作流程拆成两部分：
- **脚本/硬编码能力**：可复现、可验收、可回滚（诊断、定位、写入、报告）
- **AI（可选）**：只负责生成/改写文字，且始终有 fallback 方案

## 目录结构（核心）

- `scripts/run.py`：CLI 入口（diagnose/coach/apply-section/refs/terms/review/diff/rollback）
- `scripts/core/hybrid_coordinator.py`：协同编排（把各模块串成闭环）
- `scripts/core/diagnostic.py`：Tier1 诊断（结构/引用/字数/禁用表述与命令）
- `scripts/core/writing_coach.py`：渐进式引导（阶段判断 + 可复制提示词 + AI fallback）
- `scripts/core/security.py`：白名单写入策略（拒绝写入 main.tex/.cls/.sty 等）
- `scripts/core/editor.py` + `scripts/core/latex_parser.py`：按 `\\subsubsection{...}` 精确替换正文
- `scripts/core/versioning.py`：runs 备份、diff、rollback
- `scripts/core/html_report.py` + `assets/templates/html/report_template.html`：HTML 可视化报告
- `scripts/core/example_matcher.py` + `assets/examples/**`：示例推荐（支持 `*.metadata.yaml`）
- `scripts/core/config_loader.py`：配置加载（基础配置 + preset + 用户 override）

## 数据流（简化）

1. CLI 读取配置：`load_config()`  
2. Coordinator 定位目标文件：`targets.justification_tex`  
3. 读取 tex → Tier1 诊断：`run_tier1()`  
4. （可选）Tier2：`AIIntegration.process_request()`  
5. 输出：
   - 终端文本（diagnose/coach/review）
   - HTML 报告（diagnose --html-report）
6. 写入（apply-section）：
   - `security.validate_write_target()` 白名单校验
   - `latex_parser.replace_subsubsection_body()` 精确替换正文
   - `versioning/ensure_run_dir()` + backup → 可 diff/rollback

## 可扩展点

- **学科预设**：在 `assets/presets/` 增加 `<preset>.yaml`（兼容旧路径 `config/presets/`：如你有旧文件可自行创建该目录），优先覆盖 `terminology.dimensions`（推荐；三维矩阵），也兼容 `terminology.alias_groups`
- **示例库**：在 `assets/examples/<category>/` 增加 `.tex` 与 `*.metadata.yaml`（keywords/description）
- **质量规则**：在 `config.yaml` 的 `quality.forbidden_phrases/avoid_commands` 里增补规则
