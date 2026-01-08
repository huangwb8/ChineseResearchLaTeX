<div align="center">

<img src="logo/logo.png" alt="项目 Logo" width="200"/>

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

AI 负责格式对齐、参考文献管理、章节重构等机械性工作，人类则专注研究设计、学术观点、创新提炼等创造性思维。为适应这一变革，本项目基于 Vibe Coding 理念重构：AI 智能分析模板结构并自动识别需要优化的样式模块，提出优化方案后由人类审核决策，AI 执行并自动编译测试，人类把控最终质量。同时，项目构建了可扩展的 Agent Skills 体系，支持灵活组合与升级，从而在"AI 辅助标书写作"这一任务里充分地压榨 AI 的智能。更重要的是，**斯坦福大学《2025年AI指数报告》显示 LLM 能力正以超越摩尔定律的速度指数级进化**，核心基准测试分数一年内飙升 67.3 个百分点，编码任务通过率从 4.4% 跃升至 71.7%——这意味着本项目的价值将随模型能力增长而持续放大，今天 AI 能帮你完成格式对齐，明天就能协助观点提炼和逻辑重构。**本项目的核心特性**：

- 🤖 **AI 驱动**：智能模板规划、自动样式对齐、代码审查测试
- 🧩 **模块化技能**：可扩展的 AI 技能体系，支持灵活组合与升级
- 👥 **人机协作**：AI 处理机械任务，人类聚焦创意与决策
- 🔬 **科研导向**：专为国自然标书等科研写作场景深度优化
- 🚀 **未来可期**：随 AI 能力指数级增长，项目价值持续放大

> 💡 **创作不易，如果这个项目对您有帮助，请给个 ⭐ Star 持续关注！**

---

## ⚠️ 免责和安全性声明

> 使用本项目前，**务必仔细阅读** [logo/SECURITY.md](logo/SECURITY.md) **完整声明文档**。请在充分了解相关风险的情况下使用本项目。

---

## 📋 模板列表

> ⚠️ **建议使用正式的 [Release 版本](https://github.com/huangwb8/ChineseResearchLaTeX/releases) 以获得最佳稳定性**

| 模板 | 状态 | Overleaf 演示 |
|------|------|---------------|
| [青年科学基金项目](projects/NSFC_Young/) | ✅ 2026 就绪 | [演示](https://www.overleaf.com/read/jchdzdmdkkpj#423009) |
| [面上项目](projects/NSFC_General/) | ✅ 2026 就绪 | [演示](https://www.overleaf.com/read/trpmsszhsyvt#c3eb06) |
| 地区科学基金项目 | ⏸️ 暂未更新，[有需要请提交 Issue](https://github.com/huangwb8/ChineseResearchLaTeX/issues) | ⏳ 待更新 |

---

## 🔗 镜像站

- **GitHub 源站**：[huangwb8/ChineseResearchLaTeX](https://github.com/huangwb8/ChineseResearchLaTeX)
- **Gitee 镜像**：[huangwb8/ChineseResearchLaTeX](https://gitee.com/huangwb8/ChineseResearchLaTeX)（方便中国大陆访问）

---

## 🚀 使用

### 环境要求

- **测试平台**：Windows / macOS / Overleaf
- **LaTeX 发行版**：TeX Live（推荐）或 MacTeX
- **编译器**：**必须使用 XeLaTeX**（Overleaf 上请在 Menu → Compiler 中选择 XeLaTeX）
- **编译顺序**：`xelatex -> bibtex -> xelatex -> xelatex`

### 推荐软件平台

- **VS Code + LaTeX Workshop**：本地开发的最佳选择，充分发挥 Vibe Coding 工具的超强能力
- **Claude Code / OpenAI Codex CLI**（VS Code 插件）：**最佳选择**，AI 辅助写作，与本项目的 AI 技能完美配合。VS Code 扩展市场搜索"Claude Code"或"OpenAI Codex"即可安装
- **Office Viewer**（VS Code 插件）：推荐安装，提供 Markdown 和 Word 文档的实时预览功能，提升文档编辑体验

> 💡 **说明**：由于在本地使用 Vibe Coding 的体验很好，因此**不推荐**在 Overleaf 等在线平台使用本模板。但本项目**会持续支持 Overleaf 平台**，用户可自由选择使用方式。

---

### AI 模型配置建议

| 工具 | 推荐模型 | 适用场景 |
|------|----------|----------|
| **Codex CLI** | GPT-5.2 High | **首选**：复杂任务、长上下文、高质量输出（速度较慢） |
| **Claude Code** | Claude 4.5 Opus | 复杂任务、高质量输出 |
| **Claude Code** | GLM-4.7 | 轻量调整、格式修复、快速迭代 |

> 💡 **API 获取建议**：如果您还没有可用的 API，推荐使用 [我的专属邀请链接](https://x.dogenet.win/i/kUOGvGyo) 获取稳定、高质量的 API 服务。如果您累计充值满4美元（约 20 元人民币）后填写邀请码，我们均可获得 20 美元 ClaudeCode 专用抵扣额度。此额度仅能通过[指定活动端点](https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg)使用，额度有效期为 60 天。

---

## 🤖 Skills

项目内置多个符合 [我预定义规范](https://github.com/huangwb8/skills) 的强大 Skills，辅助 LaTeX 写作和模板优化。**兼容 Claude Code 和 OpenAI Codex CLI！**

| 技能 | 类型 | 功能 | 状态 |
|------|------|------|------|
| [make_latex_model](skills/make_latex_model/) | 🔧 开发 | 基于 Word 模板高保真优化 LaTeX 样式 | ✅ 稳定 |
| [complete_example](skills/complete_example/) | 🔧 开发 | 智能示例生成和补全 | ✅ 稳定 |
| [transfer_old_latex_to_new](skills/transfer_old_latex_to_new/) | 📝 日常 | 将旧标书内容迁移到新模板 | ✅ 稳定 |
| [systematic-literature-review](skills/systematic-literature-review/) | 📝 日常 | 令人印象深刻的精准、全面的专家级综述 | ✅ 稳定 |
| [nsfc-justification-writer](skills/nsfc-justification-writer/) | 📝 日常 | NSFC 立项依据写作 | 🚧 开发中 |
| [nsfc-research-content-writer](skills/nsfc-research-content-writer/) | 📝 日常 | NSFC 研究内容编排写作 | 🚧 开发中 |
| [nsfc-research-foundation-writer](skills/nsfc-research-foundation-writer/) | 📝 日常 | NSFC 研究基础编排写作 | 🚧 开发中 |

> 📖 **详细使用说明和 Prompt 模板**：请查阅 [skills/README.md](skills/README.md)

---

## 💝 捐赠

开发和维护这些 LaTeX 模板需要大量时间和精力 😓,**您的捐赠将帮助我持续优化模板和 AI 技能、快速响应问题和 Bug 修复、开发新的科研写作辅助功能,以及保持项目的长期维护和更新**。如果本项目对您有帮助,欢迎捐赠支持我的开发工作! 🙏

<div align="center">

<img src="logo/pay-1024x541.jpg" alt="捐赠码" width="400"/>

</div>

---

## 👨‍💻 维护者

[@huangwb8](https://blognas.hwb0307/lyb)

---

## ©️ 许可证

本项目采用 [MIT License](license.txt)。

---

## 📚 相关资源

### 指南与教程

> 💡 **提示**：深入了解 AI 辅助编程和 Vibe Coding 理念，推荐阅读上述博客文章（如果您是初次接触，建议按顺序阅读以循序渐进地了解 Vibe Coding 生态）

- [LaTeX 写作指南](references/latex-writing-guide.md)：科研论文写作最佳实践
- [博客文章](https://blognas.hwb0307.com/skill/5762) ：国家自然科学基金 LaTeX 模板详解
- [Vibe Coding CLI 评测：Claude Code vs. OpenAI Codex vs.Gemini CLI](https://blognas.hwb0307.com/other/6923) - 全面对比三大 CLI AI 编程助手（2026-01-06）
- [AI 模型评测：性价比超绝的 GLM-4.7](https://blognas.hwb0307.com/ai/6914) - 智谱 AI 开源模型的编码能力与推理性能分析（2026-01-05）
- [Claude Code 和 Claude Skills 的工程设计](https://blognas.hwb0307.com/skill/6689) - 深入探讨 Skills 本质与系统化开发流程（2026-01-03）
- [AI 应用系列：一个简单的 Vibe Coding 通知系统](https://blognas.hwb0307.com/ai/6659) - VibeNotification 项目实战经验（2025-12-21）

### 相关仓库

- [Ruzim/NSFC-application-template-latex](https://github.com/Ruzim/NSFC-application-template-latex)
- [Readon/NSFC-application-template-latex](https://github.com/Readon/NSFC-application-template-latex)
- [MCG-NKU/NSFC-LaTex](https://github.com/MCG-NKU/NSFC-LaTex)
- [fylimas/nsfc](https://github.com/fylimas/nsfc)：活跃更新的国自然模板
- [YimianDai/iNSFC](https://github.com/YimianDai/iNSFC)：MacTeX 和 Overleaf 通用模板
