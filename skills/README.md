# AI 技能使用指南

本项目内置多个 AI 技能（Skills），辅助 LaTeX 写作和模板优化。**兼容 Claude Code 和 OpenAI Codex CLI！**

> 📋 **Skills 开发规范**：本项目遵循通用的 Skills 开发规范，详见 [huangwb8/skills](https://github.com/huangwb8/skills)

## 当前技能列表

### 1. make_latex_model - 样式对齐优化

**类型**：🔧 开发

**功能**：基于最新 Word 模板，高保真优化 LaTeX 样式

**使用场景**：NSFC 发布新 Word 模板，需要 LaTeX 模板与之像素级对齐

**推荐 Prompt 模板**：

```
请使用 make_latex_model 这个 skill 对 projects/NSFC_Young 进行改造，使其与 template/2026年最新word模板-青年科学基金项目（C类）-正文.pdf 对齐
```

**技能特点**：
- 仅修改 `projects/{project}/extraTex/@config.tex`
- 修改 `main.tex` 中的标题文本（不触碰正文内容）
- 支持标题文字对齐和样式参数对齐

[详细文档 →](make_latex_model/SKILL.md)

---

### 2. complete_example - 智能示例生成

**类型**：🔧 开发

**功能**：快速生成示例内容，填充空白章节

**使用场景**：需要快速生成演示内容或测试排版效果

**推荐 Prompt 模板**：

```
请你联网调研一下某研究主题，假设你要以此为题材填写 projects/NSFC_Young，请使用 complete_example 这个 skill 辅助工作。最后的排版，PDF 要紧凑、美观，大致维持在 8 页左右。
```

[详细文档 →](complete_example/SKILL.md)

---

### 3. transfer_old_latex_to_new - 标书智能迁移

**类型**：📝 日常

**功能**：将旧标书内容迁移到新模板

**使用场景**：旧版本标书迁移到新模板（结构变化大的情况）

**推荐 Prompt 模板**：

```
请基于 transfer_old_latex_to_new 这个 skill 把 /xxx/NSFC_Young_2025 这个旧项目迁移到 /xxx/NSFC_Young_2026 这个文件夹里；新项目的模板是 projects/NSFC_Young。注意，千万不能修改或者删除 NSFC_Young_2025 里面的任何文件（完全只读）；只需要在 NSFC_Young_2026 里按要求生成内容就行。如果你工作时有测试文件/中间文件要生成，请一律放在 ./tests/v202601081624 里；测试/中间文件必须要保存在该测试目录里。
```

**技能特点**：
- 充当顶尖科学家的角色
- AI 自主规划迁移策略
- 严格遵守新模板格式

[详细文档 →](transfer_old_latex_to_new/SKILL.md)

---

## 调用方式

| 工具 | 调用方式 | 示例 |
|------|----------|------|
| **Claude Code** | 自然语言描述 | "请将 NSFC_Young 对齐到 2026 Word 样式" |
| **OpenAI Codex CLI** | `/skill-name` 参数 | `/complete_example NSFC_Young --content-density moderate` |

## 技能类型说明

| 类型 | 说明 | 面向对象 |
|------|------|----------|
| 🔧 开发 | 模板调试、样式对齐、示例生成 | 开发者 |
| 📝 日常 | 标书迁移、内容迁移 | 普通用户 |
