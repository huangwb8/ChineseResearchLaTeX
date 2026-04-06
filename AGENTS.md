# 中国科研常用 LaTeX 模板集 - 项目指令

本项目已从早期的“模板仓库”演进为一个以 NSFC 为主线的 **LaTeX 模板 + 公共包源码 + 安装/构建脚本 + AI Skills** 协作仓库。当前最成熟、最稳定的主线仍是 NSFC 系列模板；同时，仓库已经引入 `packages/bensz-fonts/` 作为跨产品线共享字体基础包，`bensz-paper` 已落地首批可验证的论文链路（`packages/bensz-paper/` + `projects/paper-sci-01/` + `projects/paper-coverletter-01/`），`bensz-thesis` 已落地首批毕业论文链路（`packages/bensz-thesis/` + `projects/thesis-smu-master/` + `projects/thesis-nju-master/` + `projects/thesis-sysu-doctor/` + `projects/thesis-ucas-doctor/`），`bensz-cv` 也已落地首个中英文学术简历链路（`packages/bensz-cv/` + `projects/cv-01/`）。

一般建议优先使用最新的 [Release](https://github.com/huangwb8/ChineseResearchLaTeX/releases)。仓库主分支可以包含重构中的源码、脚本和技能，处理任务时要以“当前真实目录结构 + 当前脚本接口 + 当前 README/CHANGELOG”作为判断依据，而不是沿用旧版记忆。

---

## 项目目标

- 维护可直接使用的 NSFC LaTeX 模板与 Release 交付物
- 维护 `packages/bensz-nsfc/` 公共包源码，避免三套 NSFC 项目重复堆叠样式逻辑
- 维护 `packages/bensz-fonts/` 共享字体基础包源码，统一托管字体文件并为其它 `bensz-*` 包提供字体引用 API
- 维护 `packages/bensz-paper/` 公共包源码与 `projects/paper-sci-01/`、`projects/paper-coverletter-01/` 示例项目，支撑 SCI 论文正文与投稿信模板的 PDF/DOCX 双输出
- 维护 `packages/bensz-thesis/` 公共包源码与 `projects/thesis-smu-master/`、`projects/thesis-nju-master/`、`projects/thesis-sysu-doctor/`、`projects/thesis-ucas-doctor/` 示例项目，支撑硕士/博士论文模板的 PDF 输出与像素级验收
- 维护 `packages/bensz-cv/` 公共包源码与 `projects/cv-01/` 示例项目，支撑中英文简历模板的 PDF 输出、像素级验收与去隐私公开演示
- 维护 `packages/bensz-nsfc/scripts/` 下的 NSFC 官方脚本入口，包括安装、构建、校验与 TDS 打包
- 维护根目录 `scripts/` 下的项目级脚本入口，例如 Release 打包与上传辅助脚本
- 维护 `skills/` 目录中的项目级 AI Skills，支撑 NSFC 写作、评审、质控、迁移、出图等工作流
- 为后续期刊论文、毕业论文模板保留包级扩展位点，但不为尚未落地的能力编造规则

## 目录结构

```text
ChineseResearchLaTeX/
├── packages/
│   ├── bensz-nsfc/          # NSFC 公共包源码（当前主线）
│   │   ├── scripts/         # NSFC 安装/构建/校验/TDS 打包脚本
│   │   └── ...
│   ├── bensz-fonts/         # 共享字体基础包源码
│   ├── bensz-paper/         # SCI 论文公共包源码
│   ├── bensz-thesis/        # 毕业论文公共包源码
│   └── bensz-cv/            # 学术简历公共包源码
├── projects/
│   ├── NSFC_General/        # 面上项目薄封装 + 示例正文
│   ├── NSFC_Local/          # 地区项目薄封装 + 示例正文
│   ├── NSFC_Young/          # 青年项目薄封装 + 示例正文
│   ├── paper-sci-01/        # SCI 论文示例项目（PDF + DOCX）
│   ├── paper-coverletter-01/ # 投稿 cover letter 示例项目（PDF + DOCX）
│   ├── thesis-smu-master/   # 南方医科大学硕士论文示例项目
│   ├── thesis-nju-master/   # 南京大学工程管理硕士论文示例项目
│   ├── thesis-sysu-doctor/  # 中山大学博士论文示例项目
│   ├── thesis-ucas-doctor/   # 中国科学院大学博士论文示例项目
│   └── cv-01/               # 中英文简历示例项目（PDF）
├── scripts/
│   ├── install.py           # 统一 LaTeX 包安装器（支持远程执行）
│   ├── sync_vscode_configs.py # 同步 projects/ 下固定的 VS Code 工作区与 LaTeX 配置
│   ├── vscode/              # VS Code / LaTeX Workshop 固定配置模板
│   ├── pack_release.py      # Release 资产打包与上传
│   └── get-github-token.sh  # GitHub 辅助脚本
├── docs/
│   └── migration-guide.md   # 旧项目迁移到公共包模式的说明
├── references/              # 项目辅助文档
├── skills/                  # 项目级 Agent Skills
├── plans/                   # 规划文档
├── tests/                   # 回归验证与发布记录
├── CLAUDE.md                # Claude Code 项目指令适配
├── AGENTS.md                # OpenAI Codex 项目指令
├── CHANGELOG.md             # 项目级变更日志
└── README.md                # 用户说明
```

### 当前分层模型

处理任务时，优先判断应该修改哪一层：

- `packages/bensz-nsfc/`：NSFC 三套模板共享的样式、资源、profile、`templates/` 模板实现与稳定脚本入口
- `packages/bensz-fonts/`：跨产品线共享字体资源与统一字体引用 API
- `packages/bensz-paper/`：SCI 论文共享样式、profile 与 PDF/DOCX 构建脚本
- `packages/bensz-thesis/`：毕业论文共享样式、profile、统一 PDF 构建与像素比对脚本
- `packages/bensz-cv/`：中英文简历共享样式、字体配置、统一 PDF 构建与像素比对脚本
- `projects/NSFC_*`：项目示例内容、项目类型差异、最薄的一层入口封装
- `projects/paper-sci-01/`：SCI 论文示例正文、`extraTex/**/*.tex` 单一真相来源、项目级 wrapper
- `projects/paper-coverletter-01/`：投稿 cover letter 示例正文、匿名化元信息与项目级 wrapper
- `projects/thesis-smu-master/` / `projects/thesis-nju-master/` / `projects/thesis-sysu-doctor/` / `projects/thesis-ucas-doctor/`：毕业论文示例正文、项目级 wrapper 与公开演示资产
- `projects/thesis-*/template.json`：毕业论文项目元数据，至少记录 `project_name`、`school`、`degree`，供 README 模板列表等脚本识别院校与学位来源；`degree` 当前统一使用英文枚举 `bachelor` / `master` / `doctor`
- `projects/cv-01/`：中英文简历示例正文、公开演示头像与项目级 wrapper
- `packages/bensz-nsfc/scripts/install.py`：安装、锁定、同步、回退、状态检查
- `packages/bensz-nsfc/scripts/nsfc_project_tool.py`：统一 PDF 构建与缓存清理
- `packages/bensz-paper/scripts/paper_project_tool.py` / `packages/bensz-paper/scripts/manuscript_tool.py`：SCI 论文 PDF + DOCX 统一构建入口
- `packages/bensz-thesis/scripts/thesis_project_tool.py`：毕业论文 PDF 构建、缓存清理与像素级 PDF 比对入口
- `packages/bensz-cv/scripts/cv_project_tool.py`：中英文简历 PDF 构建、缓存清理与像素级 PDF 比对入口
- `packages/bensz-nsfc/scripts/validate_package.py` / `packages/bensz-nsfc/scripts/build_tds_zip.py`：NSFC 公共包校验与 TDS 打包
- `scripts/install.py`：统一 LaTeX 包安装器，支持远程执行（`curl | python3 -`），可安装 `bensz-fonts`、`bensz-nsfc`、`bensz-paper`、`bensz-thesis`、`bensz-cv` 等 `packages/` 下的公共包，并支持 `--mirror gitee`
- `scripts/sync_gitee_mirror.py`：将默认分支最新 commit（以及手动指定 tag）从 GitHub 同步推送到 Gitee 镜像仓库的官方脚本
- `scripts/sync_vscode_configs.py`：同步 `projects/` 下各项目的 `*.code-workspace`、`.vscode/settings.json` 与 VS Code 构建 launcher
- `scripts/vscode/`：按 `nsfc / paper / thesis / cv` 分型托管 VS Code / LaTeX Workshop 固定模板，并提供通过 `texlua` 转调项目级 Python wrapper 的跨平台 launcher
- `scripts/pack_release.py`：项目级 Release 资产打包与上传
- `.github/workflows/sync-gitee-mirror.yml`：在默认分支有新 commit 时立即同步到 Gitee，并额外每小时巡检一次
- `skills/`：项目级 AI 技能及其文档、脚本、测试
- `docs/`：迁移说明等辅助文档

如果一个问题影响多条产品线共享的字体文件、字体路径解析或字体引用 API，优先修改 `packages/bensz-fonts/`；如果问题影响三套 NSFC 模板的共同版式、BibTeX 资源或公共宏逻辑，再优先修改 `packages/bensz-nsfc/`，不要把同一份改动复制粘贴回 `projects/NSFC_General`、`projects/NSFC_Local`、`projects/NSFC_Young`。

---

## 核心工作流

当用户提出 LaTeX 模板、NSFC 标书、公共包、安装脚本或 Skill 相关需求时，按以下流程执行：

### 任务理解

- 理解用户的真实需求和意图：是正文写作、版式修复、公共包重构、安装失败、编译报错、Skill 优化，还是 Release 打包
- 确认任务层级：公共包、项目示例、脚本、技能文档、迁移文档、发布流程，分别落在哪个目录
- 识别依赖和约束：XeLaTeX、BibTeX、`TEXMFHOME`、`.nsfc-version`、共享字体/BibTeX 资源、draw.io/Gemini 配置、技能输出目录等

### 执行流程

任务分层定位 → 最小范围修改 → 按官方入口验证 → 必要时同步文档与变更记录 → 输出交付

### 当前推荐工作流

#### NSFC 模板/版式问题

- 先判断问题属于公共包还是项目层正文
- 共享样式问题优先修 `packages/bensz-nsfc/`
- 项目示例内容、说明文字、局部项目差异再修 `projects/NSFC_*`

#### LaTeX 包安装问题

- 用户无需克隆仓库时，优先使用根级统一安装器（`scripts/install.py`）：
  - 未显式指定 `--packages` 时，默认安装 `bensz-fonts,bensz-nsfc,bensz-paper,bensz-thesis,bensz-cv`
  - `curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py | python3 - install --ref <tag>`
  - Windows PowerShell 可使用：`(Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py' -UseBasicParsing).Content | python - install --ref <tag>`；若系统已安装官方 Python Launcher，也可改用 `py -3 -`
  - 支持多包安装：`--packages bensz-fonts,bensz-nsfc,bensz-paper,bensz-thesis,bensz-cv`
  - 若目标包 `version` 与已安装版本一致，安装器默认跳过重复安装；需要覆盖时显式加 `--force`
  - 中国大陆用户如需走镜像，可显式加 `--mirror gitee`
  - 若 TeX 未加入 `PATH` 或需安装到自定义 texmf 树，可显式加 `--texmfhome <path>`
- 在仓库内开发时，bensz-nsfc 包级安装优先检查 `packages/bensz-nsfc/scripts/install.py` 与 `docs/migration-guide.md`
- 用户项目版本锁相关问题优先围绕 `.nsfc-version`、`pin/sync/check/rollback` 工作流处理

#### NSFC 编译/渲染问题

- 优先使用 `python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir <项目路径>`
- 只在排查底层编译链路时，才退回原生 `xelatex -> bibtex -> xelatex -> xelatex`

#### SCI 论文模板问题

- 公共样式、profile、DOCX 对齐逻辑优先修改 `packages/bensz-paper/`
- 论文正文优先维护 `projects/paper-sci-01/extraTex/`，投稿信正文优先维护 `projects/paper-coverletter-01/extraTex/`
- 不要再把同一份正文拆成持久化 Markdown 与 LaTeX 双份
- 优先使用 `python packages/bensz-paper/scripts/paper_project_tool.py build --project-dir <project-dir>` 验证 PDF + DOCX 双输出

#### 毕业论文模板问题

- 公共样式、profile、统一构建与比对逻辑优先修改 `packages/bensz-thesis/`
- 示例正文与公开演示资产优先维护 `projects/thesis-smu-master/`、`projects/thesis-nju-master/`、`projects/thesis-sysu-doctor/`、`projects/thesis-ucas-doctor/`
- 新增、重命名或复制 `projects/thesis-*` 项目时，必须同步维护项目根目录 `template.json`；至少包含 `project_name`、`school`、`degree`，并保证 `project_name` 与目录名一致；`degree` 当前统一使用 `bachelor` / `master` / `doctor`，供 `scripts/update_readme_template_list.py` 等脚本自动识别院校与学位信息
- 优先使用 `python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir <项目路径>` 验证 PDF 输出
- 涉及版式回归时，可使用 `python packages/bensz-thesis/scripts/thesis_project_tool.py compare --project-dir <项目路径> --baseline-pdf <原始PDF>` 做像素级验收

#### 简历模板问题

- 公共样式、字体配置、统一构建与比对逻辑优先修改 `packages/bensz-cv/`
- 示例正文与公开演示头像优先维护 `projects/cv-01/`
- 优先使用 `python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all` 验证中英双语 PDF 输出
- 若需与私有源简历验收版式回归，可使用 `python packages/bensz-cv/scripts/cv_project_tool.py compare --project-dir projects/cv-01 --variant <zh|en> --baseline-pdf <原始PDF>` 做像素级验收

#### VS Code 工作区配置

- `projects/` 下每个示例项目都必须提交一个与目录同名的 `*.code-workspace` 文件，以及 `.vscode/` 隐藏目录
- `.code-workspace` 用于 VS Code 打开项目本身；`.vscode/settings.json` 负责把 LaTeX Workshop 固定到项目级 Python wrapper，不直接裸跑 `xelatex`
- `.vscode/settings.json` 默认应通过 `texlua` 调起项目级 `scripts/latex_workshop_build.lua`，再由该 launcher 自动寻找可用 Python 解释器并转调 `scripts/*_build.py`，以兼容 macOS / Linux / Windows
- 固定模板统一托管在 `scripts/vscode/`，批量同步入口为 `python scripts/sync_vscode_configs.py`
- 调整 VS Code / LaTeX Workshop 配置时，优先修改 `scripts/vscode/` 模板，再同步到各项目；不要只改单个项目导致配置漂移

#### Skill 相关问题

- 先确认是否改动 `SKILL.md`、`config.yaml`、脚本实现、README、CHANGELOG
- 变更 Skill 后，检查根级 `README.md` 与根级 `CHANGELOG.md` 是否需要同步

### 输出规范

- LaTeX / Python / Markdown 修改应遵循当前仓库真实结构，不再假设旧版“大一统模板目录”
- NSFC 模板变更后，应优先通过官方构建链路完成验证
- SCI 模板变更后，应优先通过 `paper_project_tool.py` 完成 PDF + DOCX 联合验证
- 毕业论文模板变更后，应优先通过 `thesis_project_tool.py` 完成 PDF 构建验证；若涉及版式迁移，再执行像素级 PDF 比对
- 简历模板变更后，应优先通过 `cv_project_tool.py` 完成中英双语 PDF 构建验证；若涉及样式迁移，再执行像素级 PDF 比对
- 编译结果以“无错误”为底线；若仍有 warning，需明确说明是否为已有 warning 或新增 warning
- 新增共享逻辑时，优先沉淀到公共包或脚本，不要把重复资源重新散落回各项目目录
- 构建产物应符合当前约定：中间文件尽量隔离到 `.latex-cache/` 或各 Skill 的隐藏工作区

---

## 工程原则

本项目遵循以下工程原则：

| 原则 | 核心思想 | 在本项目中的体现 |
|------|----------|------------------|
| **KISS** | Keep It Simple, Stupid | 优先维护“公共包 + 薄项目 + 官方脚本入口”的简单结构 |
| **YAGNI** | You Aren't Gonna Need It | 不为尚未落地的论文/毕业论文能力过早设计复杂规则 |
| **DRY** | Don't Repeat Yourself | 共享样式、共享字体、共享 `bst`、共享构建逻辑集中维护 |
| **SOLID** | 面向对象设计五大原则 | 安装、构建、校验、发布、技能各司其职 |
| **关注点分离** | Separation of Concerns | `packages/`、`projects/`、`scripts/`、`skills/`、`docs/` 分层清晰 |
| **奥卡姆剃刀** | 如无必要，勿增实体 | 优先选择最短迁移路径和最少入口数量 |
| **最小惊讶原则** | Principle of Least Astonishment | 默认走 README 中公开承诺的官方入口，不发明隐藏工作流 |
| **早期返回原则** | Early Return | 及早判定任务层级与修改边界，减少误改共享逻辑或错误目录 |

**原则冲突时的决策优先级**：
1. **正确性 > 一切**
2. **简洁性 > 灵活性**
3. **清晰性 > 性能**
4. **扩展性 > 紧凑性**

---

## Skill 开发规范

本项目在 `skills/` 目录中维护多个 Agent Skill。所有新增或修改的 Skill 必须遵守以下规范，确保与上游 [huangwb8/skills](https://github.com/huangwb8/skills) 项目的标准保持一致。

### 目录结构

每个 Skill 应包含以下标准文件：

```text
skills/your-skill/
├── SKILL.md              # 必需：技能功能文档（AI 执行规范）
├── README.md             # 推荐：用户友好的使用指南
├── config.yaml           # 推荐：参数和版本管理
├── CHANGELOG.md          # 可选：技能变更记录
├── scripts/              # 可选：可执行脚本
├── tests/                # 可选：测试用例和结果
├── references/           # 可选：参考文档
├── plans/                # 可选：计划文档
└── assets/               # 可选：资源文件
```

### SKILL.md 规范

**核心原则**：`SKILL.md` 应聚焦于 **AI 执行逻辑**，而非版本历史或宣传信息。

| 要求 | 说明 | 示例 |
|------|------|------|
| **长度控制** | ≤500 行，避免冗余内容 | - |
| **描述精简** | `config.yaml` 的 `description` 字段 ≤ 1024 字符 | `支持 DOI 和 arxiv ID` |
| **移除版本标记** | 不使用 `⚠️ v2.3.0 新增` 类标记 | ❌ `⚠️ v2.3.0 新增：支持XXX`<br>✅ `支持XXX功能` |
| **简洁标题** | 标题不使用序号前缀 | ❌ `## 1) 功能概述`<br>✅ `## 功能概述` |
| **单线描述** | `description` 字段使用单行格式，融入负向约束 | `生成 NSFC 摘要（不适用：非标书场景）` |

**理由**：对 AI 而言，重要的是“功能是什么”，而非“何时加入的”。版本标记会增加认知负荷，降低信号噪声比。

### README.md 规范

`README.md` 是**面向用户的使用指南**，说明如何触发和使用技能。

**应包含内容**：

- 技能用途和适用场景
- 快速开始指南
- 参数说明
- 使用示例
- 常见问题和限制

**注意**：`README.md` 应由 `write-skill-readme` skill 生成和维护。

### config.yaml 规范

配置文件统一管理技能的元信息和版本号，遵循单一真相来源（Single Source of Truth）原则。

**必需节点结构**：

```yaml
skill_info:
  name: skill-name
  version: x.y.z
  description: "功能描述（≤1024字符，单行格式）"
  category: writing|development|normal
```

**版本号规则**（遵循语义化版本）：

| 类型 | 格式 | 示例 | 说明 |
|------|------|------|------|
| **稳定版** | v1.0.0+ | v1.0.0 | 功能完整，经过充分测试 |
| **开发中** | v0.x.x | v0.7.3 | 核心功能可用，持续优化 |
| **实验性** | v0.0.x | v0.0.1 | 功能验证阶段 |

**版本号递增规则**：

- **主版本号（Major）**：不兼容的 API 变更
- **次版本号（Minor）**：向下兼容的功能性新增
- **修订号（Patch）**：向下兼容的问题修正

### 六大质量原则

#### 1. 硬编码与 AI 功能划分

- **硬编码的确定性操作**：路径处理、文件验证、格式转换、目录初始化、结构校验
- **灵活判断**：语义理解、多轮对话、启发式决策、文风/逻辑评估

#### 2. 多轮自检与人类监督

- Skill 应支持多轮对话和渐进式优化
- 关键决策应请求用户确认，或在 README / SKILL 中明确默认策略

#### 3. 冗余残留检查

- 删除功能时，全局清理所有引用和依赖
- 避免遗留孤立脚本、过期文档、失效示例和旧命令

#### 4. 安全性审视

- **输入验证**：验证用户输入合法性
- **路径处理**：避免路径穿越和越界写入
- **敏感信息防护**：不在日志中泄露密钥、密码等

#### 5. 过度设计检查

- 不添加用户未要求的“预留功能”
- 优先选择最简单、最稳的方案

#### 6. 通用性验证

- 避免时间敏感硬编码
- 避免只适用于单机单目录的脆弱实现
- 尽量保证 macOS / Linux / Windows / WSL / Overleaf 口径一致

### 版本管理

**核心原则**：`config.yaml` 为版本号唯一真相来源。

**版本号同步顺序**：
1. 更新 `config.yaml` 中的 `skill_info.version`
2. 同步更新 `README.md`
3. 同步更新 `CHANGELOG.md`
4. 其他文档中的版本号必须与 `config.yaml` 保持一致

### 文档更新与发布

每次修改 Skill 时：

1. 更新 `CHANGELOG.md`（Skill 级别）
2. 更新 `SKILL.md`（如有功能变更）
3. 重新生成 `README.md`（使用 `write-skill-readme` skill）
4. 同步到项目级 `CHANGELOG.md`
5. 视影响范围检查根级 `README.md`、`skills/README.md` 是否需要同步

---

## 通用规范

### 默认语言

除非用户明确要求其他语言，始终使用 **简体中文** 与用户对话与撰写文档/说明。

### 联网与搜索

默认优先使用项目内文件与本地上下文；确需联网获取信息时，优先使用本地搜索工具。仅当本地工具不足以满足需求时再使用其它联网手段，并说明原因与保留关键链接。

### 真实状态优先

仓库已发生较大重构，处理任务时遵循以下优先级：

1. 当前可执行脚本的真实接口
2. 当前目录结构与源码实现
3. `README.md`、`CHANGELOG.md`、`docs/` 中的现行说明
4. 其他补充性配置文件

若旧计划文档、补充性配置或旧记忆与现状冲突，以真实目录和真实脚本行为为准，并在必要时同步修正文档。

### 文件引用规范

在项目指令文档中引用文件时：

- 使用 Markdown 链接语法，如 `[filename.md](path/filename.md)`
- 包含相关的起始行号，如 `path/filename.md#L42`
- 使每个引用有独立路径，即使是同一文件

### VS Code 工程文件

- `projects/` 下每个项目必须包含 `<项目目录名>.code-workspace`
- 同时必须包含 `.vscode/` 隐藏目录，至少提供 `.vscode/settings.json`
- 默认应让 LaTeX Workshop 通过项目级 wrapper 脚本构建，并把中间文件隔离到 `.latex-cache/`
- 固定模板统一维护在 `scripts/vscode/`；新增项目或调整模板后，使用 `python scripts/sync_vscode_configs.py` 同步
- 普通用户本地开发时，默认建议直接用项目自带的 `*.code-workspace` 打开 VS Code，而不是裸开目录

### 变更边界

- 仅修改与当前任务直接相关的文件
- 不主动添加用户未要求的功能
- 保持现有代码风格和结构
- 不自动清理/删除 `.DS_Store`
- `CLAUDE.md` 与 `AGENTS.md` 的核心章节需保持一致
- 变更 `skills/` 目录内容时，检查 `skills/README.md` 与根级 `README.md` 是否需要同步
- 变更 `packages/bensz-fonts/` 时，不要把共享字体文件重新复制回 `packages/bensz-nsfc/`、`packages/bensz-cv/` 或各 `projects/` 目录
- 变更 `packages/bensz-nsfc/` 时，不要顺手把共享字体、共享 `bst` 或公共宏重新复制回 `projects/NSFC_*`
- 变更 `packages/bensz-paper/` 时，不要重新引入持久化正文 Markdown 副本；优先保持 `projects/paper-sci-01/extraTex/**/*.tex` 与 `projects/paper-coverletter-01/extraTex/**/*.tex` 为 PDF / DOCX 的唯一真相来源
- 变更 `projects/thesis-*` 时，不要遗漏项目根目录 `template.json`；新增学校模板或重命名 thesis 项目时，必须同步更新其中的 `project_name`、`school`、`degree`，且 `degree` 保持 `bachelor` / `master` / `doctor` 这组统一枚举
- 变更 `packages/bensz-cv/` 时，不要把私有简历正文、私有头像或验收阶段的私有对比图重新留在 `projects/cv-01/`；公开示例必须保持去隐私状态
- 变更 `packages/bensz-nsfc/scripts/` 下脚本时，应同步检查 README、`docs/migration-guide.md`、`AGENTS.md`、相关项目 README 与计划文档中的命令口径
- 变更 `packages/bensz-paper/scripts/` 下脚本时，应同步检查根级 `README.md`、`AGENTS.md`、`packages/bensz-paper/README.md`、`projects/paper-sci-01/README.md` 与 `projects/paper-coverletter-01/README.md`
- 变更 `packages/bensz-cv/scripts/` 下脚本时，应同步检查根级 `README.md`、`AGENTS.md`、`packages/bensz-cv/README.md` 与 `projects/cv-01/README.md`
- 变更 `scripts/sync_vscode_configs.py` 或 `scripts/vscode/` 时，应同步检查根级 `README.md`、`projects/README.md`、`AGENTS.md` 与各项目落地的 `*.code-workspace` / `.vscode/settings.json`
- 变更根目录 `scripts/pack_release.py` 时，应同步检查 Release 流程文档与 `CHANGELOG.md`
- 变更 `.github/workflows/sync-gitee-mirror.yml` 或 `scripts/sync_gitee_mirror.py` 时，应同步检查根级 `README.md`、`AGENTS.md`、`CHANGELOG.md` 与仓库变量/密钥说明

### 系统 Skill 保护

- **严禁直接修改系统级 Skill 的工作文件/代码**（如 `~/.claude/skills/`、`~/.codex/skills/` 下的文件）
- 如有项目个性化需求，应在项目目录内添加代码或配置
- 遵循“项目级覆盖系统级”原则，通过项目内的 `skills/` 目录扩展或覆盖功能

---

## LaTeX 技术规范

### 安装与版本锁定

当前 NSFC 模板采用“公共包安装 + 项目薄封装”模式。处理 NSFC 相关任务时，优先使用以下官方入口：

```bash
python packages/bensz-nsfc/scripts/install.py install --ref v3.5.1
python packages/bensz-nsfc/scripts/install.py install --ref v3.5.1 --mirror gitee
python packages/bensz-nsfc/scripts/install.py pin --ref v3.5.1
python packages/bensz-nsfc/scripts/install.py sync
python packages/bensz-nsfc/scripts/install.py check
python packages/bensz-nsfc/scripts/install.py rollback
```

开发当前仓库时，如需直接验证本地源码：

```bash
python packages/bensz-nsfc/scripts/install.py install --source local --path packages/bensz-nsfc --ref local-dev
```

处理安装/锁定问题时，优先查看：

- `packages/bensz-nsfc/scripts/install.py`
- `docs/migration-guide.md`
- 项目目录内的 `.nsfc-version`

根目录 `scripts/` 不再承载 NSFC 直接脚本；凡是 NSFC 公共包安装、构建、校验、TDS 打包问题，都优先在 `packages/bensz-nsfc/scripts/` 下定位。

在“只打开单个 NSFC 项目目录”或“处理项目 Release 压缩包”场景下，默认不要假设项目目录内自带这些脚本。应先定位已安装的 `bensz-nsfc` 包根目录，再进入其 `scripts/` 目录找脚本：

1. 首选 `kpsewhich bensz-nsfc-common.sty`
2. 若能得到 `.sty` 路径，则将其父目录视为包根目录，并优先查找 `<包根>/scripts/`
3. 若 `kpsewhich` 不可用或未返回结果，再检查常规 `TEXMFHOME/tex/latex/bensz-nsfc/`
4. 只有在完整仓库开发模式下，才直接使用仓库内 `packages/bensz-nsfc/scripts/`

默认假设：普通项目 zip 仍按“先安装 `bensz-nsfc` 公共包，再使用项目”的模式工作，AI 应优先通过上述路径发现策略定位脚本；只有在专门面向 Overleaf 的 Release zip 场景下，才允许把公共包运行时文件与共享资源一并打入压缩包，以保证上传后可直接编译。

处理 `bensz-fonts`、`bensz-paper`、`bensz-thesis`、`bensz-cv` 安装问题时，优先使用根级统一安装器：

```bash
python3 scripts/install.py install
python3 scripts/install.py install --packages bensz-fonts,bensz-paper,bensz-thesis,bensz-cv
python3 scripts/install.py install --packages bensz-paper --mirror gitee
```

`bensz-paper`、`bensz-thesis`、`bensz-cv` 现也具备与 `bensz-nsfc` 类似的包级版本管理/激活能力；默认仍先推荐根级统一安装器，只有在明确需要切换、回退或单独排查某个公共包时，才直接调用各自的 `scripts/package/install.py`，例如：

```bash
python packages/bensz-paper/scripts/package/install.py install --ref main
python packages/bensz-paper/scripts/package/install.py rollback
python packages/bensz-thesis/scripts/package/install.py check
python packages/bensz-cv/scripts/package/install.py use --ref v4.0.0
```

这些包级安装器的缓存与状态目录统一放在 `~/.ChineseResearchLaTeX/<package>/` 下，避免在用户主目录散落多个 `.bensz-*` 顶级隐藏目录。

### 编译规范

**首选入口**：使用统一 Python 渲染器，而不是手写一串裸 `xelatex` 命令。

```bash
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_General
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_Local
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_Young
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all
```

当前官方构建链路会自动执行：

```text
xelatex → bibtex → xelatex → xelatex
```

并同时保证：

- 所有中间文件尽量隔离到项目内 `.latex-cache/`
- 根目录默认只保留最终 `main.pdf`
- 为 VS Code PDF/源码跳转保留 `.latex-cache/*.synctex.gz`

仅在排查底层编译问题时，才直接使用原生命令：

```bash
xelatex -interaction=nonstopmode main.tex
bibtex main
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex
```

### 校验规范

修改 NSFC 公共包、共享资源或安装逻辑后，优先运行：

```bash
python packages/bensz-nsfc/scripts/validate_package.py
```

如仅做结构校验、暂不编译，可使用：

```bash
python packages/bensz-nsfc/scripts/validate_package.py --skip-compile
```

如需清理项目缓存与根目录中间文件，使用：

```bash
python packages/bensz-nsfc/scripts/nsfc_project_tool.py clean --project-dir projects/NSFC_General
```

### 标题换行控制

对于需要精确控制换行长度的标题，例如 NSFC 申请书里的长括号提示语：

**推荐方案：使用 `\linebreak{}`**

```latex
\subsection{2. 工作条件（包括已具备的实验条件，尚缺少的实验条件和拟\linebreak{}解决的途径...）}
```

| 方法 | 优势 | 适用场景 |
|------|------|----------|
| `\linebreak{}` | 建议换行，保留 LaTeX 微调空间 | 标题断行控制 |
| `\\` | 强制换行，不允许调整 | 仅用于必须强制换行的场景 |

---

## 文档与版本管理

### 变更记录规范

**核心原则**：项目中的任何更新都必须在根级 [CHANGELOG.md](CHANGELOG.md) 中记录，避免在分散文档中维护重复历史。

### 记录范围

每次修改以下内容时，必须更新 `CHANGELOG.md`：

- 项目指令文件：`CLAUDE.md`、`AGENTS.md`
- 项目结构变更：新增/删除/重命名目录或关键文件
- 工作流变更：安装、构建、校验、发布、技能协作等核心流程调整
- 工程原则变更：新增、修改或删除工程原则
- 重要配置变更：影响项目行为的配置文件、脚本、公共包接口修改
- Skill 变更：任何 Skill 的版本更新

### 记录格式

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式：

```markdown
## [版本号] - YYYY-MM-DD

### Added（新增）
- 新增了 XXX 功能/章节：用途是 YYY

### Changed（变更）
- 修改了 XXX 章节：原因是 YYY，具体变更内容是 ZZZ

### Fixed（修复）
- 修复了 XXX 问题：表现是 YYY，修复方式是 ZZZ
```

### 记录时机

- **修改前**：先在 `CHANGELOG.md` 的 `[Unreleased]` 部分草拟变更内容
- **修改后**：完善变更描述，添加具体细节和影响范围
- **发布时**：将 `[Unreleased]` 内容移至具体版本号下

### Release 前检查

创建 Release 前，至少确认以下事项：

- 目标变更已完成必要编译/脚本校验
- NSFC 公共包相关改动已跑过 `python packages/bensz-nsfc/scripts/validate_package.py`
- 相关 README / docs / CHANGELOG 已同步
- 确认 `python scripts/pack_release.py --tag <tag>` 生成的普通 zip 与 Overleaf zip 命名、内容与目标场景一致
- 若本次任务包含“发布 GitHub Release / 上传 Release Assets”，默认必须继续执行 `python scripts/pack_release.py --tag <tag> --upload`；除非用户明确要求“只本地打包 / 暂不上传”，否则不得省略
- 在 `--upload` 真正执行成功前，AI 不得把任务表述为“Release 已发布完成”；只能明确写成“Release 已创建，但 Assets 尚未上传”
- 如普通项目 zip 需要独立可用，确认项目内 `code/nsfc_build.py` 已能在“完整仓库路径 / 已安装 TEXMFHOME 路径”中定位 `bensz-nsfc` 公共脚本
- 如 Overleaf zip 需要独立可用，确认压缩包已将最小必需运行时裁剪后注入 `styles/`，且只包含当前项目所需的模板实现、共享字体与共享 `bst` 资源
- 若涉及模板外观回归，优先把验证记录沉淀到 `tests/` 或相应计划目录

### Release 发布流程

> 基于 `gh` CLI 发布 Release

每次创建新 Release 时，按以下顺序执行：

1. **提交代码**：使用 `git-commit` skill 生成 commit 信息并 push
2. **创建 Tag**：创建新的版本 tag（遵循 Semver，如 `v3.5.2`）
3. **生成 Release**：使用 `git-publish-release` skill 生成 Release Notes 并发布
4. **打包并上传 Assets**：运行 `python scripts/pack_release.py --tag <tag> --upload` 完成打包与上传；默认会同时产出普通 zip（本地安装公共包场景）与 Overleaf 专用 zip（内嵌公共包运行时文件场景）。这是 Release 发布任务的默认必做步骤，不得因为前面已创建 tag 或 GitHub Release 而省略；只有用户明确要求“只打包不上传”或“本次先不上传 Assets”时，才允许跳过
5. **发布微信动态**：在当前与用户交互的界面中生成一条微信动态，内容包含项目名、版本号、核心更新亮点和 Release 地址，字数控制在 100–200 字

完成判定：

- 只有步骤 4 成功执行并确认 Assets 已上传后，才可称为“Release 发布完成”
- 若因 `gh` 权限、网络、认证或用户策略导致未执行/执行失败，必须在最终答复中明确写出阻塞原因与当前停留步骤，不能省略不报
- 最终答复需显式交代 `python scripts/pack_release.py --tag <tag> --upload` 是否已执行、是否成功，以及普通 zip / Overleaf zip 的处理结果

参考：

```bash
python scripts/pack_release.py --tag v3.5.2 --upload
```

### Skill 文档编写原则

**核心理念**：Skill 文档应始终展示最新状态，不包含版本标记等对 AI 执行无用的元信息。

| 原则 | 说明 | 示例 |
|------|------|------|
| **内容优先于版本** | 移除版本标记 | ❌ `⚠️ v2.3.0 新增：支持XXX`<br>✅ `支持XXX功能` |
| **简洁标题** | 标题不使用序号前缀 | ❌ `## 1) 功能概述`<br>✅ `## 功能概述` |
| **单一职责** | `SKILL.md` 专注功能规范，`CHANGELOG.md` 专注版本追踪 | 各司其职，避免重复 |
| **技术必要引用例外** | 保留技术性版本引用 | `v2.3.0 前的旧路径` |

**设计公式**：

```text
有效信息 = 总内容 - (版本标记 + 冗余序号 + 宣传性强调)
```

---

## 文档更新原则

当需要更新本文档时，遵循以下原则：

### 1. 理解意图

先理解用户需求背后的意图，以及它在当前“公共包 + 项目 + 脚本 + Skills”生态中的真实作用。

### 2. 定位生态位

每条规则都应找到它在整个文档结构中的“生态位”：

- 它服务哪个工作流
- 它约束哪个目录层级
- 它是否会影响 README、docs、CHANGELOG、CLAUDE.md 或某个 Skill

### 3. 协调生长

更新一个部分时，检查并同步更新相关部分：

- 更新安装/构建流程时，同步更新 README、`docs/migration-guide.md`、命令示例
- 更新共享包结构时，同步检查 `packages/bensz-nsfc/README.md` 与验证脚本口径
- 更新 Skill 规范时，同步检查 `skills/README.md` 与相关 Skill 文档
- 更新本文档时，必须同步更新 `CHANGELOG.md`
- 更新本文档后，确保 `CLAUDE.md` 的核心内容保持一致

### 4. 保持呼吸感

文档应保持结构流动，而不是变成割裂的堆砌清单；新增规则优先融入现有章节逻辑。

### 5. 定期修剪整合

当某个章节开始承载过多旧时代信息、失效命令或重复说明时，主动重写，而不是继续叠补丁。

---

**提示**：修改本文档后，请立即在 `CHANGELOG.md` 中记录变更，并确保 `CLAUDE.md` 的核心内容保持一致。这是项目管理的强制性要求，不是可选项。
