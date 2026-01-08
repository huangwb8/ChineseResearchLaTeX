<div align="center">

<img src="logo/logo.png" alt="项目 Logo" width="120"/>

# 中国科研常用 LaTeX 模板集

[![Version](https://img.shields.io/github/v/tag/huangwb8/ChineseResearchLaTeX?label=version&sort=semver&color=blue)](https://github.com/huangwb8/ChineseResearchLaTeX/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](license.txt)
[![Platform](https://img.shields.io/badge/platform-Mac%20%7C%20Win%20%7C%20Overleaf-lightgrey.svg)](#使用)
[![Built with](https://img.shields.io/badge/AI%20Powered-Vibe%20Coding-orange.svg)](#ai-驱动开发)

</div>

---

<div align="center">

**[国自然正文模板（2026 就绪）](#模板列表) • [AI 技能](#ai-技能) • [写作指南](#相关资源)**

为 Vibe Writing 做好准备！

</div>

---

## ✨ 概览

2024-2025 年，AI 辅助开发迎来了真正的范式转移。2023 年，[GitHub Copilot](https://github.com/features/copilot) 普及了 AI 代码补全，但 AI 仍处于"被动响应"角色。2024 年初，[Cursor](https://cursor.sh) 率先将 AI 转变为"主动协作伙伴"，引入 AI 原生开发环境。随后，[Manus](https://manus.im)、[Windsurf](https://windsurf.ai) 等产品持续推动多 Agent 协作和深度 IDE 集成。到了 2024 年末，[Claude Code](https://docs.anthropic.com/en/docs/build-with-claude/claude-code) 和 [OpenAI Codex CLI](https://github.com/openai/openaicode) 将这一理念带入命令行领域，实现了真正的"AI 作为第一公民"。这一演进背后的核心理念被称为 **Vibe Coding**——AI 不再是工具，而是合作伙伴。传统模式下，人类写代码、AI 补全，指令是单向的、生成是一次性的。而在 Vibe Coding 模式下，AI 主动规划并执行任务，人类负责监督和决策；双方通过双向对话持续迭代优化，AI 成为真正的"合作开发者"。

<h3>🔥 科研写作正从纯手工转向这种人机协作模式（我称之为 <strong>Vibe Writing</strong>）</h3>

AI 负责格式对齐、参考文献管理、章节重构等机械性工作，人类则专注研究设计、学术观点、创新提炼等创造性思维。为适应这一变革，本项目基于 Vibe Coding 理念重构：AI 智能分析模板结构并自动识别需要优化的样式模块，提出优化方案后由人类审核决策，AI 执行并自动编译测试，人类把控最终质量。同时，项目构建了可扩展的 Agent Skills 体系，支持灵活组合与升级，从而在"AI 辅助标书写作"这一任务里充分地压榨 AI 的智能。**本项目的核心特性**：

- 🤖 **AI 驱动**：智能模板规划、自动样式对齐、代码审查测试
- 🧩 **模块化技能**：可扩展的 AI 技能体系，支持灵活组合与升级
- 👥 **人机协作**：AI 处理机械任务，人类聚焦创意与决策
- 🔬 **科研导向**：专为国自然标书等科研写作场景深度优化

> 💡 **创作不易，如果这个项目对您有帮助，请给个 ⭐ Star 持续关注！**

---

## ⚠️ 免责和安全性声明

📄 **完整声明请查阅**：[logo/SECURITY.md](logo/SECURITY.md)

---

## 📋 模板列表

> ⚠️ **建议使用正式的 [Release 版本](https://github.com/huangwb8/ChineseResearchLaTeX/releases) 以获得最佳稳定性**

| 模板 | 状态 | Overleaf 演示 |
|------|------|---------------|
| [青年科学基金项目](projects/NSFC_Young/) | ✅ 2026 就绪 | ⏳ 待更新 |
| [面上项目](projects/NSFC_General/) | ✅ 2026 就绪 | ⏳ 待更新 |
| 地区科学基金项目 | ⏸️ 暂未更新，[有需要请提交 Issue](https://github.com/huangwb8/ChineseResearchLaTeX/issues) | ⏳ 待更新 |

---

## 🚀 使用

### 环境要求

- **测试平台**：Windows / macOS / Overleaf
- **LaTeX 发行版**：TeX Live（推荐）或 MacTeX
- **编译顺序**：`xelatex -> bibtex -> xelatex -> xelatex`

### 推荐软件平台

- **VS Code + LaTeX Workshop**：本地开发的最佳选择，充分发挥 Vibe Coding 工具的超强能力
- **Claude Code / OpenAI Codex CLI**：AI 辅助写作，与本项目的 AI 技能完美配合

#### AI 模型配置建议

| 工具 | 推荐模型 | 适用场景 |
|------|----------|----------|
| **Codex CLI** | GPT-5.2 High | **首选**：复杂任务、长上下文、高质量输出（速度较慢） |
| **Claude Code** | Claude 4.5 Opus | 复杂任务、高质量输出 |
| **Claude Code** | GLM-4.7 | 轻量调整、格式修复、快速迭代 |

> 💡 **API 获取建议**：如果您还没有可用的 API，推荐使用 [我的专属邀请链接](https://x.dogenet.win/i/kUOGvGyo) 获取稳定、高质量的 API 服务。如果您累计充值满4美元（约 20 元人民币）后填写邀请码，我们均可获得 20 美元 ClaudeCode 专用抵扣额度。此额度仅能通过[指定活动端点](https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg)使用，额度有效期为 60 天。

---

## 🤖 Skills

项目内置多个 AI 技能，辅助 LaTeX 写作和模板优化。**兼容 Claude Code 和 OpenAI Codex CLI！**

| 技能 | 类型 | 功能 | 状态 |
|------|------|------|------|
| [make_latex_model](skills/make_latex_model/) | 🔧 开发 | 基于 Word 模板高保真优化 LaTeX 样式 | ✅ 稳定 |
| [complete_example](skills/complete_example/) | 🔧 开发 | 智能示例生成和补全 | ✅ 稳定 |
| [transfer_old_latex_to_new](skills/transfer_old_latex_to_new/) | 📝 日常 | 将旧标书内容迁移到新模板 | ✅ 稳定 |

> 📖 **详细使用说明和 Prompt 模板**：请查阅 [skills/README.md](skills/README.md)

## 🔗 镜像站

- **GitHub 源站**：[huangwb8/ChineseResearchLaTeX](https://github.com/huangwb8/ChineseResearchLaTeX)
- **Gitee 镜像**：[huangwb8/ChineseResearchLaTeX](https://gitee.com/huangwb8/ChineseResearchLaTeX)（方便中国大陆访问）

---

## 📚 相关资源

### 指南与教程

- [LaTeX 写作指南](references/latex-writing-guide.md)：科研论文写作最佳实践
- [博客文章](https://blognas.hwb0307.com/skill/5762)：国家自然科学基金 LaTeX 模板详解

### 相关仓库

- [Ruzim/NSFC-application-template-latex](https://github.com/Ruzim/NSFC-application-template-latex)
- [Readon/NSFC-application-template-latex](https://github.com/Readon/NSFC-application-template-latex)
- [MCG-NKU/NSFC-LaTex](https://github.com/MCG-NKU/NSFC-LaTex)
- [fylimas/nsfc](https://github.com/fylimas/nsfc)：活跃更新的国自然模板
- [YimianDai/iNSFC](https://github.com/YimianDai/iNSFC)：MacTeX 和 Overleaf 通用模板

---

## 📝 待办事项

### 🔮 AI 辅助写作技能

> 符合 [我预定义规范](https://github.com/huangwb8/skills) 的强大 Skills，Codex/Claude Code 兼容！**未来 2-3 周陆续推出，值得期待！**

- **立项依据生成**：基于研究主题自动生成研究意义和国内外现状
- **研究内容规划**：将科学问题拆解为可验证的研究目标和内容
- **可行性分析**：自动撰写四维可行性（理论/技术/团队/条件）
- **特色与创新提炼**：帮助识别和表述项目的核心创新点

---

## 👨‍💻 维护者

[@huangwb8](https://blognas.hwb0307.com/lyb)

---

## ©️ 许可证

本项目采用 [MIT License](license.txt)。

---

## 📖 推荐阅读

> 💡 深入了解 AI 辅助编程和 Vibe Coding 理念，推荐阅读我的博客文章（如果您是初次接触，建议按顺序阅读以循序渐进地了解 Vibe Coding 生态）：

- [Vibe Coding CLI 评测：Claude Code vs. OpenAI Codex vs. Gemini CLI](https://blognas.hwb0307.com/other/6923) - 全面对比三大 CLI AI 编程助手（2026-01-06）
- [AI 模型评测：性价比超绝的 GLM-4.7](https://blognas.hwb0307.com/ai/6914) - 智谱 AI 开源模型的编码能力与推理性能分析（2026-01-05）
- [Claude Code 和 Claude Skills 的工程设计](https://blognas.hwb0307.com/skill/6689) - 深入探讨 Skills 本质与系统化开发流程（2026-01-03）
- [AI 应用系列：一个简单的 Vibe Coding 通知系统](https://blognas.hwb0307.com/ai/6659) - VibeNotification 项目实战经验（2025-12-21）
