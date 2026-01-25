<div align="center">

<img src="logo/logo.png" alt="项目 Logo" width="200"/>

# 中国科研常用 LaTeX 模板集

[![Version](https://img.shields.io/github/v/tag/huangwb8/ChineseResearchLaTeX?label=version&sort=semver&color=blue)](https://github.com/huangwb8/ChineseResearchLaTeX/releases)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Mac%20%7C%20Win%20%7C%20Overleaf-lightgrey.svg)
![Built with](https://img.shields.io/badge/AI%20Powered-Vibe%20Coding-orange.svg)

</div>

---

<div align="center">

**[国自然正文模板（2026 就绪）](#模板列表) • [AI 技能](#相关资源) • [写作指南](#相关资源)**

为 Vibe Writing 做好准备！💡 创作不易，如果这个项目对您有帮助，请给个 ⭐ Star 持续关注！

</div>

---

## ✨ 概览

2024-2025 年，AI 辅助开发迎来了真正的范式转移。2023 年，[GitHub Copilot](https://github.com/features/copilot) 普及了 AI 代码补全，但 AI 仍处于"被动响应"角色。2024 年初，[Cursor](https://cursor.sh) 率先将 AI 转变为"主动协作伙伴"，引入 AI 原生开发环境。随后，[Manus](https://manus.im)、[Windsurf](https://windsurf.ai) 等产品持续推动多 Agent 协作和深度 IDE 集成。到了 2024 年末，[Claude Code](https://code.claude.com/docs/en/overview) 和 [OpenAI Codex CLI](https://developers.openai.com/codex/cli) 将这一理念带入命令行领域，实现了真正的"AI 作为第一公民"。这一演进背后的核心理念被称为 **Vibe Coding**——AI 不再是工具，而是合作伙伴。传统模式下，人类写代码、AI 补全，指令是单向的、生成是一次性的。而在 Vibe Coding 模式下，AI 主动规划并执行任务，人类负责监督和决策；双方通过双向对话持续迭代优化，AI 成为真正的"合作开发者"。

<h3>🔥 科研写作正从纯手工转向这种人机协作模式（我称之为 <strong>Vibe Writing</strong>）</h3>

AI 负责格式对齐、参考文献管理、章节重构等机械性工作，人类则专注研究设计、学术观点、创新提炼等创造性思维。为适应这一变革，本项目基于 Vibe Coding 理念重构：AI 智能分析模板结构并自动识别需要优化的样式模块，提出优化方案后由人类审核决策，AI 执行并自动编译测试，人类把控最终质量。同时，项目构建了可扩展的 Agent Skills 体系，支持灵活组合与升级，从而在"AI 辅助标书写作"这一任务里充分地压榨 AI 的智能。更重要的是，**斯坦福大学《2025年AI指数报告》显示 LLM 能力正以超越摩尔定律的速度指数级进化**，核心基准测试分数一年内飙升 67.3 个百分点，编码任务通过率从 4.4% 跃升至 71.7%——这意味着本项目的价值将随模型能力增长而持续放大，今天 AI 能帮你完成格式对齐，明天就能协助观点提炼和逻辑重构。**本项目的核心特性**：

- 🤖 **AI 驱动**：智能模板规划、自动样式对齐、代码审查测试
- 🧩 **模块化技能**：可扩展的 AI 技能体系，支持灵活组合与升级
- 👥 **人机协作**：AI 处理机械任务，人类聚焦创意与决策
- 🔬 **科研导向**：专为国自然标书等科研写作场景深度优化
- 🚀 **未来可期**：随 AI 能力指数级增长，项目价值持续放大

<div align="center">

<img src="logo/poster.jpeg" alt="项目海报" width="800"/>

</div>

---

## ⚠️ 免责和安全性声明

使用本项目前，**务必仔细阅读[完整声明文档](logo/SECURITY.md)**。请保证您在充分了解相关风险的情况下使用本项目。

---

## 👥 社区支持

博客文章：

- [国家自然科学基金的LaTeX模板](https://blognas.hwb0307.com/skill/5762)
- [国家自然科学基金的LaTeX模板 第2期](https://blognas.hwb0307.com/skill/6930)

欢迎加入项目微信群聊，与其他用户交流经验、分享心得！无论您是对以下哪个话题感兴趣，都欢迎扫码进群：

- 📚 **科研写作**：LaTeX 使用、论文写作、标书撰写
- 📝 **国自然标书**：申请经验、模板使用、格式优化
- 🤖 **AI Agents**：智能代理开发、技能体系搭建
- 🔌 **API 使用**：模型调用、API 配置、成本优化
- ✨ **Vibe Coding/Writing**：AI 辅助编程与写作，人机协作式创作

<div align="center">

<img src="logo/wechat-group-01.JPG" alt="微信群二维码" width="300"/>

</div>

> 💡 **温馨提示**：微信群主要用于经验交流和问题讨论，如需报告 Bug 或提交功能建议，请通过 [GitHub Issues](https://github.com/huangwb8/ChineseResearchLaTeX/issues) 提交，以便更好地跟踪和管理。

---

## 📋 模板列表

> ⚠️ **建议使用正式的 [Release 版本](https://github.com/huangwb8/ChineseResearchLaTeX/releases) 以获得最佳稳定性**。借助 [make_latex_model](skills/make_latex_model/) 技能，现已支持像素级 `Word/PDF 模板 → LaTeX 模板` 的快速转换，如有定制需求欢迎[提交 Issue](https://github.com/huangwb8/ChineseResearchLaTeX/issues)。模板中的示例内容、章节结构、写作逻辑仅供参考，请务必根据您的研究主题和实际情况进行调整。

| 模板 | 状态 | Overleaf 演示 | 上次修改时间 |
|------|------|---------------|----------------|
| [青年C](projects/NSFC_Young/) | ✅ 2026 就绪 | [演示](https://www.overleaf.com/read/cjhmcmjpsrpy#875405) | 2026-01-19 |
| [面上](projects/NSFC_General/) | ✅ 2026 就绪 | [演示](https://www.overleaf.com/read/cjhmcmjpsrpy#875405) | 2026-01-19 |
| 地区 | ⏸️ 暂未更新，[有需要请提交 Issue](https://github.com/huangwb8/ChineseResearchLaTeX/issues) | ⏳ 待更新 | - |

---

## 🔗 镜像站

- **GitHub 源站**：[huangwb8/ChineseResearchLaTeX](https://github.com/huangwb8/ChineseResearchLaTeX)
- **Gitee 镜像**：[huangwb8/ChineseResearchLaTeX](https://gitee.com/huangwb8/ChineseResearchLaTeX)（方便中国大陆访问）

---

## 🚀 环境

### LaTex版本

- **测试平台**：Windows / macOS / Overleaf
- **LaTeX 发行版**：TeX Live（推荐）或 MacTeX
- **编译器**：**必须使用 XeLaTeX**（Overleaf 上请在 Menu → Compiler 中选择 XeLaTeX）
- **编译顺序**：`xelatex -> bibtex -> xelatex -> xelatex`

### 工作软件

#### 必选工具

- **VS Code + LaTeX Workshop**：本地开发的最佳选择，充分发挥 Vibe Coding 工具的超强能力
- **Claude Code / OpenAI Codex CLI**（VS Code 插件）：**最佳选择**，AI 辅助写作，与本项目的 AI 技能完美配合。VS Code 扩展市场搜索"Claude Code"或"OpenAI Codex"即可安装。macOS 已成为 AI 时代开发首选操作系统，体验最佳；Windows 用户建议使用 WSL（Windows Subsystem for Linux）环境以获得更稳定的性能
  - **Claude Code**：详见[安装教程](https://claudefa.st/blog/guide/installation-guide)
  - **Codex CLI**：详见[WSL 安装指南](https://1v0.dev/posts/25-openai-codexcli-wsl/) 或 [Ubuntu/WSL 配置教程](https://cdkagaya.design.blog/2025/10/16/install-and-configure-openai-codex-cli-on-ubuntu-wsl/)

#### 可选工具

- **Office Viewer**（VS Code 插件）：提供 Markdown 和 Word 文档的实时预览功能，如需预览可安装

> 💡 **说明**：由于在本地使用 Vibe Coding 的体验很好，因此**不推荐**在 Overleaf 等在线平台使用本模板。但本项目**会持续支持 Overleaf 平台**，用户可自由选择使用方式。

### AI 模型配置建议

| 工具 | 推荐模型 | 适用场景 |
|------|----------|----------|
| **Codex CLI** | GPT-5.2 High | 执行计划、复杂任务、长上下文、高质量输出、指令遵循好、速度较慢但相对便宜 |
| **Claude Code** | Claude 4.5 Opus + thinking | 执行计划、复杂任务、高质量输出、速度较快但较昂贵、更加符合人类偏好 |
| **Codex CLI** | GPT-5.2 Medium | 轻至中量调整、格式修复；指令遵循不错、全局把控力尚可 |
| **Claude Code** | GLM-4.7 | 制定/优化计划、轻量调整、格式修复、快速迭代 |

### API 获取建议

> ⚠️ **重要说明**：以下推荐的均为第三方 API 中转服务商，非 OpenAI 或 Anthropic 官方 API。由于网络限制等原因，官方 API 在国内无法直接使用，这些中转服务提供了便捷的替代方案。同时，以下商家均支持发票报销，干科研就不用自己花钱了吧 (～￣▽￣)～ 

- **稳定高质量**：推荐使用 [我的专属邀请链接](https://x.dogenet.win/i/kUOGvGyo) 获取稳定、高质量的 API 服务。如果您累计充值满4美元（约 20 元人民币）后填写邀请码，我们均可获得 20 美元 ClaudeCode 专用抵扣额度。此额度仅能通过[指定活动端点](https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg)使用，额度有效期为 60 天。🔥 **最新动态**：Cerebras 推出新模型 `zai-glm-4.7`，现开放免费及开发者版本，将于 2026 年 1 月 20 日起替代旧版 GLM-4.7
- **性价比之选**：可考虑 [DMXAPI](https://www.dmxapi.cn/register?aff=HIeH)（LangChain 中文网提供的 API 聚合平台）。通常可做到海外模型约 **6-7 折/约 70-80% 官方价**，支持**专票/普票**与**公对公转账**等企业报销需求；平台运营相对透明（有运营日志与接口状态监控）。注意高峰期可能出现 429 限流或个别模型不稳定，建议先小额测试，并保留官方/备用方案。
- **Codex 平价拼车**：可考虑 [Packycode 的 Codex 站](https://codex.packycode.com)（日/周/月限额度）。登录/服务相对原始，偏 Team 账号拼车；实测使用 1 个多月整体较稳，个人开发基本够用。价格优势明显；发票需联系站长办理（相对麻烦），但支持对公报销是巨大优势。
- **GLM-4.7 超值拼车**：直接使用[我的邀请链接购买智谱Coding Plan](https://www.bigmodel.cn/glm-coding?ic=BNIXXULS2J)，支持企业报销。**推荐约 10 人拼一个 Coding Plan Max 车位，基本够用**，折合每人每月约 **16 元**，量大管饱，完全没有 token 焦虑。
---

## 🤖 Skills

> ⚠️ 注意：标记为 `🚧 开发中` 的 skill 暂时不建议小白用户使用，因为它们往往还没有被充分地测试，功能和安全性没有保障。

项目内置多个符合 [我预定义规范](https://github.com/huangwb8/skills) 的强大 Skills，辅助 LaTeX 写作和模板优化。**兼容 Claude Code、OpenAI Codex、Cursor、GitHub Actions、VS Code！** 通过灵活运用 skills，加上多轮对话进行优化，才能保证最佳效果。**详细使用说明和 Prompt 模板**：[skills/README.md](skills/README.md)

### ⚡ 快速安装

#### 方法一：一键快速安装

| 平台 | 命令 |
|------|------|
| **macOS / Linux / WSL** | `curl -fsSL https://raw.githubusercontent.com/huangwb8/skills/main/@install/install.sh \| bash` |
| **Windows PowerShell** | `irm https://raw.githubusercontent.com/huangwb8/skills/main/@install/install.ps1 \| iex` 

#### 方法二：本地硬编码安装

```bash
git clone https://github.com/huangwb8/skills.git && 
  git clone https://github.com/huangwb8/ChineseResearchLaTeX.git && 
  cd skills &&
  python3 install-bensz-skills/scripts/install.py --source ../ChineseResearchLaTeX/skills
```

#### 方法三：远程对话式安装

```bash
git clone https://github.com/huangwb8/skills.git && 
  cd skills &&
  python3 install-bensz-skills/scripts/install.py --remote --check
```

### 🧩 技能生态系统

本项目提供多个 AI 技能，覆盖标书写作全流程：

#### 📚 文献调研阶段
- **get-review-theme**：主题提取（从文件/图片/URL/自然语言描述提取结构化综述主题）
- **systematic-literature-review**：系统综述（AI 自定检索词，多源检索→去重→AI 逐篇阅读并评分，生成专家级综述；多源降级、摘要补齐、检索质量评估与可视化）
- **check-review-alignment**：引用核查（AI 检查综述正文引用与文献内容的语义一致性，减少幻觉引用）

#### 📋 标书准备阶段
- **guide-updater**：指南优化（基于文献综述结果优化项目指南，明确研究方向和亮点）
- **transfer_old_latex_to_new**：标书迁移（将旧标书内容迁移到新模板）

#### ✍️ 标书写作阶段
- **nsfc-justification-writer**：理论创新导向的立项依据写作（适用于各类科研基金申请书），构建"价值与必要性 → 现状与不足 → 科学问题/假说 → 切入点"四段闭环叙事，识别并改写"绝对化/填补空白"等高风险表述，防止用方法学术语稀释科学问题主线
- **nsfc-research-content-writer**：研究内容编排，同步生成"研究内容 + 特色与创新 + 三年年度计划"，确保子目标带"指标/对照/验证方案"三件套，创新点用"相对坐标系"表达
- **nsfc-research-foundation-writer**：研究基础编排，同步生成"研究基础 + 工作条件 + 风险应对措施"，用"证据链 + 条件对位 + 风险预案"证明项目可行性
- **nsfc-bib-manager**：引用管理，新增/核验论文信息（题目/作者/年份/期刊/DOI）并写入 .bib 文件，拒绝幻觉引用，只引"可核验"文献

#### 🔧 模板开发阶段（开发者专用，普通用户可忽略）
- **make_latex_model**：样式对齐（基于 Word 模板高保真优化 LaTeX 样式）
- **complete_example**：示例生成（智能示例生成和补全）

| 技能 | 版本 | 类型 | 功能 | 状态 |
|------|------|------|------|------|
| [make_latex_model](skills/make_latex_model/) | v2.7.1 | 🔧 开发 | 基于 Word 模板高保真优化 LaTeX 样式 | ✅ 稳定 |
| [complete_example](skills/complete_example/) | v1.0.0 | 🔧 开发 | 智能示例生成和补全 | ✅ 稳定 |
| [transfer_old_latex_to_new](skills/transfer_old_latex_to_new/) | v1.4.0 | 📝 日常 | 将旧标书内容迁移到新模板 | ✅ 稳定 |
| [systematic-literature-review](skills/systematic-literature-review/) | v1.0.9 | 📝 日常 | 令人印象深刻的精准、全面的专家级综述 | ✅ 稳定 |
| [check-review-alignment](skills/check-review-alignment/) | v1.0.2 | 📝 日常 | 综述引用语义一致性检查 | ✅ 稳定 |
| [nsfc-bib-manager](skills/nsfc-bib-manager/) | v1.0.0 | 📝 日常 | NSFC 标书引用与 Bib 管理 | 🚧 开发中 |
| [get-review-theme](skills/get-review-theme/) | v1.0.0 | 📝 日常 | 结构化综述主题提取 | 🚧 开发中 |
| [guide-updater](skills/guide-updater/) | v1.0.0 | 📝 日常 | 项目指南优化与写作规范沉淀 | ✅ 稳定 |
| [nsfc-justification-writer](skills/nsfc-justification-writer/) | v0.7.7 | 📝 日常 | 理论创新导向的立项依据写作 | ✅ 稳定 |
| [nsfc-research-content-writer](skills/nsfc-research-content-writer/) | v0.2.1 | 📝 日常 | NSFC 研究内容编排写作 | 🚧 开发中 |
| [nsfc-research-foundation-writer](skills/nsfc-research-foundation-writer/) | v0.1.0 | 📝 日常 | NSFC 研究基础编排写作 | 🚧 开发中 |

---

## 💝 捐赠

开发和维护这些 LaTeX 模板需要大量时间和精力 😓,**您的捐赠将帮助我持续优化模板和 AI 技能、快速响应问题和 Bug 修复、开发新的科研写作辅助功能,以及保持项目的长期维护和更新**。如果本项目对您有帮助,欢迎捐赠支持我的开发工作! 🙏

<div align="center">

<img src="logo/pay-1024x541.jpg" alt="捐赠码" width="400"/>

</div>

---

## 👨‍💻 维护者

[@huangwb8](https://blognas.hwb0307.com/lyb)

---

## ©️ 许可证

本项目采用 [MIT License](license.txt)。

---

## 🤝 商务合作

**智谱 AI** 的 **GLM-4.7** 模型凭借出色的编码能力和推理性能，为项目的 Vibe Coding 实践提供了极大助力，我们诚挚邀请智谱清言团队及各类 AI 服务商、云服务提供商、科研机构等相关方洽谈合作与赞助事宜，具体合作方式包括但不限于：

- 💰 **项目赞助**：资金、API 额度、云服务资源等
- 🎯 **技术合作**：联合开发、技术支持、模型优化等
- 📢 **品牌推广**：品牌露出、案例展示、联合活动等
- 🔬 **科研合作**：论文撰写、数据标注、模型评估等

如有合作意向，欢迎通过 [GitHub Issues](https://github.com/huangwb8/ChineseResearchLaTeX/issues) 或[维护者博客](https://blognas.hwb0307.com)联系。

---

## 📚 相关资源

### 指南与教程

> 💡 **提示**：深入了解 AI 辅助编程和 Vibe Coding 理念，推荐阅读上述博客文章（如果您是初次接触，建议按顺序阅读以循序渐进地了解 Vibe Coding 生态）

- [LaTeX 写作指南](references/latex-writing-guide.md)：科研论文写作最佳实践
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
