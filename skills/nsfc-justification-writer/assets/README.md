# assets/（资源目录）

本目录存放 **可复用的静态资源**，避免散落在 skill 根目录，便于维护与移植。

约定：
- `assets/prompts/`：可配置 Prompt 文件（由 `config.yaml:prompts.*` 指向）
- `assets/templates/`：模板文件（如 HTML 报告模板、结构骨架模板）
- `assets/examples/`：示例库（`*.tex` + `*.metadata.yaml`），用于 `scripts/run.py examples/coach --topic` 推荐参考骨架
- `assets/presets/`：学科预设（`--preset <name>`），用于覆盖术语维度等配置

说明：
- 历史路径 `prompts/`、`templates/`、`examples/`、`config/presets/` 已迁移到此处；代码仍保留兼容回退。
- 仓库不再保留 `config/` 目录；如你手头仍有旧的 `config/presets/<name>.yaml`，可自行在 skill 根目录创建该路径，或直接迁移到 `assets/presets/`。
