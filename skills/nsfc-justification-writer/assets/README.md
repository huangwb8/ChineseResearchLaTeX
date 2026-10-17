# assets/（资源目录）

本目录存放 **可复用的静态资源**，避免散落在 skill 根目录，便于维护与移植。

约定：
- `assets/prompts/`：可配置 Prompt 文件（由 `config.yaml:prompts.*` 指向）
- `assets/templates/`：模板文件（如 HTML 报告模板、结构骨架模板）
- `assets/examples/`：示例库（`*.tex` + `*.metadata.yaml`），用于 `scripts/run.py examples/coach --topic` 推荐参考骨架
- `assets/presets/`：可选学科预设（`--preset <name>`），仅在确有稳定配置差异时使用

说明：
- 历史路径 `prompts/`、`templates/`、`examples/`、`config/presets/` 已迁移到此处；代码仍保留兼容回退。
- 仓库不再保留 `config/` 目录；如你手头仍有旧的 `config/presets/<name>.yaml`，可自行在 skill 根目录创建该路径，或直接迁移到 `assets/presets/`。

示例默认采用标准立项依据内容链：研究意义 → 国内外研究现状及发展动态（按主题分块）→ 小结。科学问题、科学假设、申请人前期工作和项目切入点在现状后段或小结中凝练；研究目标、技术路线、主验证场景和判定规则不作为示例的固定章节。
